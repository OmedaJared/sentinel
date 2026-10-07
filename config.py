"""Configuración central de Centinela.

Funciona igual en local y en línea: las diferencias se controlan con variables
de entorno (ver `.env.example`).
"""
import os
import secrets
import sys
from pathlib import Path


def en_produccion() -> bool:
    """True cuando la app corre en un servidor en línea."""
    return os.environ.get("ENTORNO", "desarrollo").lower() in ("produccion", "production")


def carpeta_datos() -> Path:
    """Carpeta donde viven los datos (base de datos y clave secreta).

    Dentro de un ejecutable (PyInstaller) `__file__` apunta a la carpeta
    temporal de extracción, que se borra al cerrar. En ese caso usamos la
    carpeta donde está el .exe, para que los datos persistan junto a él.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = carpeta_datos()
CLAVE_ARCHIVO = BASE_DIR / "clave_secreta.key"


def _clave_secreta() -> str:
    """Clave de firma de sesiones.

    En local se genera una sola vez y se guarda junto a los datos, para que las
    sesiones sigan siendo válidas al reiniciar. En línea **debe** venir de la
    variable de entorno SECRET_KEY: si se generara sola, cada reinicio del
    servidor cerraría la sesión de todos los usuarios.
    """
    de_entorno = os.environ.get("SECRET_KEY")
    if de_entorno:
        return de_entorno
    if en_produccion():
        raise RuntimeError(
            "Falta la variable de entorno SECRET_KEY. Es obligatoria en producción "
            "para que las sesiones sobrevivan a los reinicios. "
            "Genera una con:  python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if CLAVE_ARCHIVO.exists():
        guardada = CLAVE_ARCHIVO.read_text(encoding="utf-8").strip()
        if guardada:
            return guardada
    nueva = secrets.token_hex(32)
    try:
        CLAVE_ARCHIVO.write_text(nueva, encoding="utf-8")
    except OSError:
        # Sin permiso de escritura seguimos funcionando en memoria.
        pass
    return nueva


def _url_base_datos() -> str:
    """Dirección de la base de datos.

    En línea suele venir en DATABASE_URL. Los servicios gestionados entregan el
    prefijo `postgres://`, que SQLAlchemy ya no acepta: lo normalizamos.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    return f"sqlite:///{BASE_DIR / 'centinela.db'}"


def _cookie_segura() -> bool:
    """Indica si las cookies deben marcarse como `Secure`.

    Se activa en producción siempre que la conexión sea realmente HTTPS. Si el
    servicio aún no tiene certificado (o se accede por HTTP), marcarlas como
    seguras haría que el navegador las descartara y el login no funcionaría.

    Se puede forzar con la variable COOKIES_SEGURAS=1|0.
    """
    forzado = os.environ.get("COOKIES_SEGURAS")
    if forzado is not None:
        return forzado == "1"
    return en_produccion()


class Config:
    """Configuración de la aplicación."""

    APP_NAME = "Sentinel"
    APP_TAGLINE = "Prevención y Control Escolar"
    APP_SHORT = "SENTINEL"

    SECRET_KEY = _clave_secreta()

    SQLALCHEMY_DATABASE_URI = _url_base_datos()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,  # evita conexiones caídas en servicios gestionados
    }

    # Sesiones
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 días
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 14  # 14 días

    # Detrás de un proxy (Render, Railway, Fly.io, nginx) hay que respetar las
    # cabeceras X-Forwarded-* para saber que la petición original era HTTPS.
    PREFERRED_URL_SCHEME = "https" if en_produccion() else "http"

    # PWA
    PWA_THEME_COLOR = "#0a0f1c"
    PWA_BACKGROUND_COLOR = "#05070d"

    # Catálogos del sistema
    ROLES = {
        "admin": "Administrador",
        "directivo": "Directivo",
        "docente": "Docente",
        "tutor": "Padre / Tutor",
        "alumno": "Alumno",
    }

    GRAVEDADES = {
        "baja": "Baja",
        "media": "Media",
        "alta": "Alta",
        "critica": "Crítica",
    }

    TIPOS_FACTOR = {
        "inasistencia": "Inasistencia recurrente",
        "conducta": "Conducta disruptiva",
        "academico": "Rezago académico",
        "emocional": "Riesgo emocional",
        "familiar": "Situación familiar",
        "salud": "Situación de salud",
        "disciplina": "Falta disciplinaria",
        "otro": "Otro",
    }

    ESTADOS_ASISTENCIA = {
        "presente": "Presente",
        "ausente": "Ausente",
        "retardo": "Retardo",
        "justificado": "Justificado",
    }

    ESTADOS_JUSTIFICANTE = {
        "pendiente": "Pendiente",
        "aprobado": "Aprobado",
        "rechazado": "Rechazado",
    }

    DIAS_SEMANA = [
        ("lunes", "Lunes"),
        ("martes", "Martes"),
        ("miercoles", "Miércoles"),
        ("jueves", "Jueves"),
        ("viernes", "Viernes"),
    ]

    PERIODOS = [
        ("1", "Primer periodo"),
        ("2", "Segundo periodo"),
        ("3", "Tercer periodo"),
    ]
