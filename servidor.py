"""Servidor de producción de Sentinel.

Usa **Waitress** (servidor WSGI multi-hilo, estable en Windows) en lugar del
servidor de desarrollo de Flask, y permite activar **HTTPS** con un certificado.

HTTPS es importante para celulares: los navegadores solo permiten usar la
cámara (necesaria para escanear los QR) en conexiones seguras o en `localhost`.

Uso:
    python servidor.py                 # red local, HTTP
    python servidor.py --https         # red local, HTTPS (cámara en el celular)
    python servidor.py --puerto 8080 --https
    python servidor.py --sin-abrir     # no intenta abrir el navegador
"""
from __future__ import annotations

import argparse
import os
import socket
import ssl
import sys
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CERT_DIR = BASE_DIR / "certificados"
CERT_PEM = CERT_DIR / "sentinel.pem"
CERT_KEY = CERT_DIR / "sentinel-key.pem"


def ip_local() -> str:
    """Dirección de esta computadora dentro de la red local."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonda:
            sonda.connect(("8.8.8.8", 80))
            return sonda.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _crear_certificado_autofirmado() -> tuple[Path, Path]:
    """Genera un certificado autofirmado para servir por HTTPS en la red local.

    Se apoya en `cryptography`, que Waitress ya trae como dependencia.
    """
    from datetime import datetime, timedelta

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    if CERT_PEM.exists() and CERT_KEY.exists():
        return CERT_PEM, CERT_KEY

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    ip = ip_local()

    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Sentinel Local")])
    ahora = datetime.utcnow()

    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(llave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - timedelta(days=1))
        .not_valid_after(ahora + timedelta(days=825))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
                    x509.IPAddress(__import__("ipaddress").ip_address(ip)),
                ]
            ),
            critical=False,
        )
        .sign(llave, hashes.SHA256())
    )

    CERT_KEY.write_bytes(
        llave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_PEM.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
    print(f"Certificado creado en {CERT_DIR.relative_to(BASE_DIR)}")
    return CERT_PEM, CERT_KEY


def _banner(esquema: str, ip: str, puerto: int, https: bool) -> None:
    base = f"{esquema}://{ip}:{puerto}"
    linea = "=" * 58
    print()
    print(linea)
    print("  SENTINEL esta en marcha")
    print(linea)
    print(f"  En esta computadora : {esquema}://127.0.0.1:{puerto}")
    print(f"  Desde celulares     : {base}")
    print()
    print("  Pasos en el celular:")
    print("   1. Conecta el celular a la MISMA red Wi-Fi.")
    print(f"   2. Abre {base} en Chrome o Safari.")
    print("   3. Menu del navegador -> 'Instalar aplicacion'")
    print("      (iPhone: Compartir -> 'Anadir a pantalla de inicio').")
    print()
    if https:
        print("  Aviso: el certificado es autofirmado. Si el navegador")
        print("  muestra una advertencia, elige 'Avanzado' -> 'Continuar'.")
        print("  Esto habilita la camara para escanear los codigos QR.")
    else:
        print("  Nota: para usar la CAMARA del celular necesitas HTTPS.")
        print("  Reinicia con:  python servidor.py --https")
    print(linea)
    print("  Para detener el servidor: Ctrl + C")
    print(linea)
    print()


def _es_servidor_en_linea() -> bool:
    """True cuando corremos en un servicio de hosting (no en la red local)."""
    return os.environ.get("ENTORNO", "").lower() in ("produccion", "production")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Servidor de producción de Sentinel.")
    parser.add_argument("--puerto", type=int, default=int(os.environ.get("PORT", 5000)))
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument(
        "--https",
        action="store_true",
        default=os.environ.get("HTTPS", "0") == "1",
        help="Sirve por HTTPS con certificado propio (uso en red local).",
    )
    parser.add_argument(
        "--sin-abrir",
        action="store_true",
        help="No abre el navegador automáticamente.",
    )
    parser.add_argument(
        "--con-datos",
        action="store_true",
        default=os.environ.get("DATOS_DEMO", "0") == "1",
        help="Carga los usuarios y grupos de demostración si la base está vacía.",
    )
    parser.add_argument(
        "--trabajadores",
        type=int,
        default=int(os.environ.get("WEB_CONCURRENCY", 2)),
        help="Procesos de Gunicorn (solo Linux/macOS).",
    )
    opciones = parser.parse_args(argv)

    from app import app

    _preparar_datos(app, cargar_demo=opciones.con_datos)

    # En un servicio de hosting la app ya se sirve por HTTPS mediante su proxy,
    # así que no generamos certificados ni mostramos el banner de red local.
    if not opciones.https and (_es_servidor_en_linea() or _puede_gunicorn()):
        return _arrancar_gunicorn(app, opciones)

    ip = ip_local()
    esquema = "https" if opciones.https else "http"
    url_local = f"{esquema}://127.0.0.1:{opciones.puerto}"

    if not opciones.sin_abrir and not _es_servidor_en_linea():
        threading.Timer(1.5, lambda: webbrowser.open(url_local)).start()

    _banner(esquema, ip, opciones.puerto, opciones.https)

    if opciones.https:
        _servir_con_https(app, opciones.host, opciones.puerto)
        return 0

    return _servir_con_waitress(app, opciones.host, opciones.puerto)


def _puede_gunicorn() -> bool:
    """Gunicorn solo existe en Linux y macOS."""
    return sys.platform != "win32"


def _arrancar_gunicorn(app, opciones) -> int:
    """Arranca la app con Gunicorn (el servidor recomendado en producción)."""
    try:
        from gunicorn.app.wsgiapp import WSGIApplication
    except ImportError:
        print("Gunicorn no está instalado; usando Waitress.")
        return _servir_con_waitress(app, opciones.host, opciones.puerto)

    # Socket.IO requiere el modo "threading" con hilos, no procesos separados.
    opciones_gunicorn = {
        "bind": f"{opciones.host}:{opciones.puerto}",
        "workers": opciones.trabajadores,
        "threads": 8,
        "worker_class": "gthread",
        "timeout": 120,
        "accesslog": "-",
        "errorlog": "-",
        "capture_output": True,
    }
    print(f"Gunicorn en marcha en {opciones_gunicorn['bind']}")

    class AplicacionGunicorn(WSGIApplication):
        def load_config(self):
            for clave, valor in opciones_gunicorn.items():
                self.cfg.set(clave, valor)

        def load(self):
            return app

    try:
        AplicacionGunicorn().run()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    return 0


def _servir_con_waitress(app, host: str, puerto: int) -> int:
    """Sirve la app con Waitress (servidor estable en Windows)."""
    from waitress import serve

    try:
        serve(app, host=host, port=puerto, threads=8, ident="Sentinel")
    except OSError as error:
        print(f"\nNo se pudo iniciar el servidor: {error}")
        print(f"Puede que el puerto {puerto} esté ocupado.")
        print("Prueba con otro:  python servidor.py --puerto 8080")
        return 1
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    return 0


def _preparar_datos(app, cargar_demo: bool = False) -> None:
    """Crea las tablas y deja la base lista para usarse.

    Si la base está vacía avisa por consola, porque sin usuarios nadie puede
    entrar. Con `cargar_demo=True` además carga los datos de demostración.
    """
    from extensions import db
    from models import User

    with app.app_context():
        db.create_all()
        if User.query.count() > 0:
            return

        if cargar_demo:
            from cli import cargar_datos_demo

            cargar_datos_demo()
            print("  Datos de demostracion cargados.")
            print("  Entra con:  admin / admin123")
            print()
        else:
            print()
            print("  Aviso: la base de datos esta vacia (no hay usuarios).")
            print("  Reinicia con --con-datos para crear los usuarios de")
            print("  demostracion, o ejecuta:  flask --app app seed")
            print()


def _servir_con_https(app, host: str, puerto: int) -> None:
    """Sirve la app por HTTPS envolviendo el socket del servidor en TLS.

    Waitress no gestiona SSL, así que se usa el servidor WSGI estándar con un
    socket cifrado. Es suficiente para una red local de escuela.
    """
    import socketserver
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    pem, key = _crear_certificado_autofirmado()
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.load_cert_chain(certfile=str(pem), keyfile=str(key))

    class ServidorTLS(socketserver.ThreadingMixIn, WSGIServer):
        daemon_threads = True

    servidor = make_server(host, puerto, app, server_class=ServidorTLS)
    servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    servidor.RequestHandlerClass = WSGIRequestHandler

    print("  HTTPS activo. La camara funcionara en el celular.\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    sys.exit(main())
