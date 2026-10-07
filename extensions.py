"""Instancias compartidas de extensiones Flask."""
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(async_mode="threading", cors_allowed_origins="*")

login_manager.login_view = "auth.login"
login_manager.login_message = "Inicia sesión para continuar."
login_manager.login_message_category = "warning"
# Respeta el proxy HTTPS: sin esto, en un servidor en línea Flask genera
# redirecciones https:// cuando el cliente sigue en http:// y el login
# entra en un bucle. El ProxyFix de la app se encarga de marcar la
# petición como segura.
login_manager.session_protection = "basic"
