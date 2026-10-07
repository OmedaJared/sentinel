# Centinela · Control escolar con credenciales QR

Sistema de gestión escolar (estilo Prevee) con tres experiencias:
**administrador**, **docentes** y **alumnos**. Incluye credenciales QR
personalizadas para registrar entrada y salida, contraseñas generadas por el
sistema y accesos separados.

Además es una **aplicación instalable (PWA)**: se instala en la pantalla de
inicio de Android, iPhone, iPad, Windows, macOS o Linux y funciona como una app
nativa, sin tienda de aplicaciones.

Puede usarse de tres formas: **en línea** (accesible desde cualquier parte),
**en la red local** de la escuela, o como **aplicación de escritorio autónoma**.

## Ponerla en línea (accesible desde cualquier parte)

En línea la app vive en un servidor con HTTPS, así que **la cámara del celular
funciona sin configurar nada**: entra desde cualquier red, sin depender de la
Wi-Fi de la escuela.

### Requisito: la clave de sesiones

En un servidor en línea la app **exige** la variable `SECRET_KEY` (si se
generara sola, cada reinicio cerraría la sesión de todos). Crea una con:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### Opción 1 · Docker (una orden, con PostgreSQL)

```bash
cp .env.example .env      # y escribe tu SECRET_KEY dentro
docker compose up --build -d
```

Queda disponible en `http://localhost:8080`. Para verlo desde otro dispositivo:
`http://TU-IP:8080`. Los datos viven en un volumen de PostgreSQL, así que
sobreviven a reinicios.

### Opción 2 · Render (con un clic, HTTPS incluido)

1. Sube el proyecto a un repositorio de GitHub.
2. En [Render](https://render.com): **New → Blueprint** y elige el repositorio.
3. `render.yaml` crea el servicio web **y** la base de datos solos, y genera la
   `SECRET_KEY` automáticamente.

Al terminar tendrás una dirección `https://sentinel-xxxx.onrender.com` con
HTTPS, lista para usar desde cualquier celular.

### Opción 3 · Cualquier servicio (Railway, Fly.io, Heroku, un VPS…)

Incluye un `Procfile` y un `Dockerfile` estándar. Solo define estas variables:

| Variable | Para qué sirve |
| --- | --- |
| `SECRET_KEY` | **Obligatoria.** Firma las sesiones. |
| `ENTORNO` | `produccion`. Activa proxy, cookies seguras y Gunicorn. |
| `DATABASE_URL` | Base de datos (PostgreSQL en línea). Sin ella usa SQLite local. |
| `PORT` | Puerto que asigna el servicio. |
| `DATOS_DEMO` | `1` la primera vez para crear los usuarios de demostración. |
| `WEB_CONCURRENCY` | Procesos de Gunicorn. Usa `1` con Socket.IO. |
| `COOKIES_SEGURAS` | `1`/`0` para forzar las cookies seguras. Por defecto se activan solas cuando hay HTTPS. |

> **Importante:** la primera vez pon `DATOS_DEMO=1` para crear el usuario
> `admin / admin123`, entra y **cambia esa contraseña** desde *Mi perfil*.

### Qué cambia al pasar a producción

- **Cookies seguras**: se activan automáticamente cuando la petición llega por
  HTTPS. Si el servicio aún no tiene certificado, no se marcan, para que el
  login no entre en un bucle.
- **ProxyFix** activo: la app entiende que detrás del proxy la petición es
  HTTPS (si no, el login redirigiría a `https://` sin salir nunca del login).
- **Gunicorn** con hilos en Linux; **Waitress** en Windows.
- **`/salud`**: endpoint de vida que usan los servicios de hosting.
- La base de datos **no** se recrea sola: los datos persisten.

Para comprobar que todo está bien configurado antes de desplegar:

```powershell
uv run python tools/probar_produccion.py
```

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias del proyecto)

> ¿No quieres instalar nada? Salta a **[Ejecutable autónomo](#ejecutable-autónomo-sin-instalar-nada)**.

## Puesta en marcha (en tu computadora o red local)

### Opción rápida (recomendada)

Un solo comando instala dependencias y arranca la app en toda la red local:

```powershell
.\iniciar.ps1                 # Windows (PowerShell)
.\iniciar.ps1 -Https          # con HTTPS (activa la cámara del celular)
.\iniciar.ps1 -ConDatos       # carga usuarios de demostración
```

```bat
iniciar.bat                   REM Windows (doble clic)
iniciar-https.bat             REM Windows con HTTPS (cámara en el celular)
```

```bash
./iniciar.sh                  # macOS / Linux
./iniciar.sh 5000 --https     # con HTTPS
```

Al arrancar se muestra la dirección para abrir la app desde cualquier
dispositivo conectado a la **misma red Wi-Fi** (móvil, tablet u otra PC).

### Opción manual

```powershell
# 1. Instalar dependencias
uv sync

# 2. Crear la base de datos
uv run flask --app app init-db

# 3. (Opcional) Cargar datos de demostración
uv run flask --app app seed

# 4. Arrancar el servidor de producción
uv run python servidor.py
```

La aplicación queda en `http://127.0.0.1:5000`.

## Usarla desde el celular

1. Conecta el celular a la **misma red Wi-Fi** que la computadora.
2. Arranca el servidor: se imprime en pantalla la dirección `http://TU-IP:5000`.
3. Abre esa dirección en Chrome (Android) o Safari (iPhone).
4. Menú del navegador → **Instalar aplicación** (iPhone: *Compartir → Añadir a
   pantalla de inicio*).

### La cámara solo funciona con HTTPS

Los navegadores **solo permiten usar la cámara en conexiones seguras** (HTTPS) o
en `localhost`. Si abres la app en el celular por `http://` y pulsas *Activar
cámara*, el navegador la bloqueará y la app te lo avisará.

Para escanear los QR desde el celular, arranca con HTTPS:

```powershell
.\iniciar.ps1 -Https        # o:  uv run python servidor.py --https
```

La primera vez el navegador advertirá que el certificado es autofirmado:
entra en *Avanzado* → *Continuar*. La app genera el certificado sola y lo
guarda en `certificados/`.

> Si solo necesitas registrar entradas desde la computadora, HTTP es
> suficiente: en `localhost` la cámara sí funciona.

## Ejecutable autónomo (sin instalar nada)

Genera un `.exe` que incluye Python y todas las dependencias: se copia a
cualquier PC con Windows y arranca con doble clic.

```powershell
uv run python tools/compilar_exe.py
```

El resultado queda en `dist/Sentinel/Sentinel.exe`. Para compartirlo, copia la
**carpeta `Sentinel` completa** (el `.exe` necesita la carpeta `_internal` que
está a su lado).

```powershell
dist\Sentinel\Sentinel.exe --con-datos      # crea los usuarios de demostración
dist\Sentinel\Sentinel.exe --https          # HTTPS para la cámara del celular
dist\Sentinel\Sentinel.exe --puerto 8080
```

Los datos (base de datos y clave de sesiones) se guardan junto al `.exe`, así
que la instalación es portable: puedes mover la carpeta con todo incluido.

## Descargar / compartir la app

```powershell
uv run python tools/empaquetar.py   # genera dist/sentinel.zip
```

El ZIP contiene todo el proyecto listo para arrancar en otra computadora
(incluye `iniciar.ps1`, `iniciar.bat` e `iniciar.sh`). Quien lo reciba solo
debe descomprimirlo, instalar `uv` y ejecutar el script de inicio.

## Instalar como app en cada dispositivo

Abre la dirección de la app y usa el botón **Instalar app** de la barra
superior, o el menú del navegador:

| Dispositivo | Cómo instalarla |
| --- | --- |
| Android (Chrome) | Menú ⋮ → *Instalar aplicación* / *Añadir a pantalla de inicio* |
| iPhone / iPad (Safari) | Compartir → *Añadir a pantalla de inicio* |
| Windows / macOS / Linux (Chrome, Edge) | Icono de instalar en la barra de direcciones, o menú → *Instalar Sentinel* |
| Escritorio (Chrome) | Menú ⋮ → *Guardar y compartir* → *Instalar página como aplicación* |

Una vez instalada queda un icono propio, se abre a pantalla completa y muestra
una pantalla de "Sin conexión" si se pierde la red.

## Cómo funciona cada rol

### 1. Administrador

Entra por una puerta distinta al resto:

- URL: `/auth/admin`
- Credenciales de demo: `admin` / `admin123`

Desde el panel puede:

1. **Dar de alta docentes** (`Docentes → Nuevo docente`) y **alumnos**
   (`Alumnos → Nuevo alumno`) en apartados separados.
2. Al guardar, el sistema **genera automáticamente una contraseña** y una
   **credencial QR** para esa persona, y redirige a la credencial.
3. La credencial muestra el **nombre completo** y la **contraseña** que el
   administrador debe entregar al alumno o docente. Se puede imprimir.
4. Si alguien olvida su contraseña, el botón **Nueva contraseña** la regenera.
5. En **Checador** ve las entradas/salidas del día.

### 2. Docentes y alumnos

Entran por el acceso general con **su nombre completo** (tal como lo registró
el admin) y la **contraseña** que les entregó:

- URL: `/auth/login`
- Ejemplo: `Carlos Sánchez` / la contraseña generada

Cada uno ve en su panel **su propio código QR** y su historial de
entradas/salidas. También en la pestaña **Mi QR**.

### 3. Registro de entrada y salida (checador)

En **Checador** (admin/directivo/docente):

- **Cámara**: pulsa _Activar cámara_ y muestra el QR; el sistema detecta si es
  entrada o salida automáticamente (alterna según el último movimiento del día).
- **Código manual**: pega el código del QR.
- **Marcaje manual**: escribe el nombre completo de la persona.

## Estructura

```
app.py                     Fábrica de la aplicación Flask
servidor.py                Arranque: Gunicorn (Linux) / Waitress (Windows)
config.py                  Configuración, catálogos, clave y base de datos
cli.py                     Comandos: init-db, seed, crear-credenciales
extensions.py              db, login_manager, socketio

Dockerfile                 Imagen lista para la nube
docker-compose.yml         App + PostgreSQL con un solo comando
render.yaml                Despliegue con un clic en Render (HTTPS incluido)
Procfile                   Para Railway, Heroku, Fly.io…
.env.example               Plantilla de variables de entorno

iniciar.ps1 / .bat / .sh   Arranque en red local en un clic
iniciar-https.bat          Arranque con HTTPS (cámara en el celular)
models/
  user.py                  Usuario y roles
  comunidad.py             Grupo, Maestro, Alumno
  academico.py             Materia, Asignacion, Calificacion, Horario
  seguimiento.py           Asistencia, FactorRiesgo, Justificante, Aviso, Alerta
  credencial.py            Credencial (QR) y RegistroAcceso
services/
  cuentas.py               Alta de usuarios y contraseñas automáticas
  credenciales.py          QR, tokens y checador
  dashboard.py             Métricas del panel
  paneles.py               Paneles por rol
routes/
  auth.py                  Login general y login de administrador
  accesos.py               Checador QR
  alumnos.py, maestros.py  Altas y credenciales
  ...
static/
  manifest.webmanifest     Manifiesto PWA (instalación en cualquier dispositivo)
  sw.js                    Service worker (modo sin conexión)
  icons/                   Iconos 192/512 y maskable
  theme.css                Tema oscuro + estilos para celular
template/                  Plantillas Jinja2 (Bootstrap 5)
tools/
  generar_iconos.py        Regenera los iconos PNG de la app
  empaquetar.py            Genera dist/sentinel.zip descargable
  compilar_exe.py          Genera el ejecutable autónomo (PyInstaller)
  probar_servidor.py       Verifica un servidor en marcha de punta a punta
  probar_produccion.py     Comprueba la configuración antes de desplegar
  probar_en_linea.py       Prueba el modo producción con proxy HTTPS
```

## Pruebas rápidas

```powershell
uv run python tests_smoke.py   # flujos de login, QR y checador
uv run python tests_rutas.py   # todas las vistas responden 200
```

## Comandos útiles

```powershell
uv run flask --app app crear-credenciales  # genera los QR que falten
uv run python tools/generar_iconos.py      # regenera los iconos de la app
uv run python tools/empaquetar.py          # crea dist/sentinel.zip
uv run python tools/compilar_exe.py        # crea el ejecutable autónomo
uv run python tools/probar_servidor.py     # verifica un servidor en marcha
uv run python tools/probar_produccion.py   # revisa la config. de producción
```
