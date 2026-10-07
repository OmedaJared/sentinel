import os
import sys

from flask import Flask, render_template
from flask_login import current_user

from config import Config
from extensions import db, login_manager, socketio


def _carpeta_recursos() -> str:
    """Carpeta que contiene `template/` y `static/`.

    Empaquetado con PyInstaller los archivos viajan en `sys._MEIPASS`; en
    desarrollo basta con la carpeta del propio archivo.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


TEMPLATE_DIR = os.path.join(_carpeta_recursos(), "template")


def create_app(config_class=Config):
    """Crea e inicializa la aplicacion Flask con todo el proyecto cableado."""
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=os.path.join(_carpeta_recursos(), "static"),
    )
    app.config.from_object(config_class)

    # PRIMERO las extensiones: Flask-SocketIO envuelve `wsgi_app`, y si se
    # aplicara ProxyFix antes, SocketIO lo taparía y quedaría sin efecto.
    _inicializar_extensiones(app)

    # En línea la app vive detrás de un proxy HTTPS (Render, Railway, Fly.io,
    # nginx…). Sin esto, Flask creería que la petición es HTTP y las cookies
    # marcadas como seguras no se enviarían (el login entraría en bucle).
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _registrar_blueprints(app)
    _registrar_contexto(app)
    _registrar_errores(app)
    _registrar_rutas_pwa(app)
    _registrar_cli(app)
    _registrar_cookies_seguras(app)
    return app


def _registrar_cookies_seguras(app):
    """Marca las cookies como `Secure` solo cuando la petición es HTTPS.

    En un servidor en línea con certificado, la petición llega por HTTPS (el
    proxy lo indica en `X-Forwarded-Proto`) y las cookies se protegen. Si el
    servicio todavía no tiene HTTPS, no se marcan: marcarlas haría que el
    navegador las descartara y nadie podría iniciar sesión.
    """
    from flask import request

    @app.before_request
    def _ajustar_cookies():
        seguro = request.is_secure or request.headers.get(
            "X-Forwarded-Proto", ""
        ) == "https"
        if seguro:
            app.config["SESSION_COOKIE_SECURE"] = True
            app.config["REMEMBER_COOKIE_SECURE"] = True
        elif not app.config.get("COOKIES_SEGURAS_FORZADAS"):
            app.config["SESSION_COOKIE_SECURE"] = False
            app.config["REMEMBER_COOKIE_SECURE"] = False


def _inicializar_extensiones(app):
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    # Importar los modelos los registra en SQLAlchemy y crea las tablas.
    import models  # noqa: F401

    with app.app_context():
        db.create_all()

    from flask_socketio import join_room

    @socketio.on("conectar")
    def _conectar(_datos=None):
        """Une al usuario autenticado a su sala personal de alertas."""
        if current_user.is_authenticated:
            join_room(f"usuario_{current_user.id}")


def _registrar_blueprints(app):
    from routes import BP_REGISTRY

    for bp in BP_REGISTRY:
        app.register_blueprint(bp)


def _registrar_contexto(app):
    """Inyecta variables y utilidades globales en las plantillas."""

    @app.context_processor
    def inyectar_globales():
        from services.dashboard import alertas_no_leidas

        no_leidas = 0
        if current_user.is_authenticated:
            no_leidas = alertas_no_leidas(current_user.id)
        return {
            "app_name": app.config.get("APP_NAME", "Centinela"),
            "app_short": app.config.get("APP_SHORT", "CENTINELA"),
            "app_tagline": app.config.get("APP_TAGLINE", ""),
            "roles": app.config.get("ROLES", {}),
            "gravedades": app.config.get("GRAVEDADES", {}),
            "tipos_factor": app.config.get("TIPOS_FACTOR", {}),
            "estados_asistencia": app.config.get("ESTADOS_ASISTENCIA", {}),
            "estados_justificante": app.config.get("ESTADOS_JUSTIFICANTE", {}),
            "dias_semana": app.config.get("DIAS_SEMANA", []),
            "periodos": app.config.get("PERIODOS", []),
            "alertas_no_leidas": no_leidas,
            "pwa_theme_color": app.config.get("PWA_THEME_COLOR", "#0a0f1c"),
        }

    @app.template_filter("fecha")
    def _filtro_fecha(valor, formato="%d/%m/%Y"):
        return valor.strftime(formato) if valor else "\u2014"

    @app.template_filter("hora")
    def _filtro_hora(valor):
        return valor.strftime("%d/%m/%Y %H:%M") if valor else "\u2014"

    @app.template_filter("moneda")
    def _filtro_moneda(valor):
        return "\u2014" if valor is None else f"{valor:.1f}"


def _registrar_errores(app):
    @app.errorhandler(403)
    def _prohibido(_error):  # noqa: ANN001
        return render_template("errores/403.html"), 403

    @app.errorhandler(404)
    def _no_encontrado(_error):  # noqa: ANN001
        return render_template("errores/404.html"), 404


def _registrar_rutas_pwa(app):
    @app.route("/offline")
    def _sin_conexion():
        """Pantalla que el service worker muestra cuando no hay internet."""
        return render_template("offline.html")

    @app.route("/salud")
    def _salud():
        """Comprobación de vida que usan los servicios de hosting."""
        from extensions import db

        try:
            db.session.execute(db.text("SELECT 1"))
            base_ok = True
        except Exception:
            base_ok = False
        codigo = 200 if base_ok else 503
        return {"estado": "ok" if base_ok else "sin base de datos", "bd": base_ok}, codigo


def _registrar_cli(app):
    from cli import registrar_comandos

    registrar_comandos(app)


app = create_app()


def _host_de_red():
    """Dirección de la máquina en la red local (para abrirla desde el móvil)."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonda:
            sonda.connect(("8.8.8.8", 80))
            return sonda.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    # HOST=0.0.0.0 permite abrir la app desde cualquier dispositivo de la misma
    # red (móvil, tablet, otra computadora), no solo desde esta computadora.
    host = os.environ.get("HOST", "127.0.0.1")
    puerto = int(os.environ.get("PORT", "5000"))
    socketio.run(
        app,
        host=host,
        port=puerto,
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        allow_unsafe_werkzeug=True,
    )