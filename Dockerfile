# Imagen de Sentinel lista para desplegar en cualquier servicio en la nube.
FROM python:3.12-slim

# uv es el gestor de dependencias del proyecto.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    ENTORNO=produccion \
    PORT=8080

WORKDIR /app

# 1) Solo las dependencias (aprovecha la caché de capas de Docker).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 2) El código de la aplicación.
COPY . .

# Usuario sin privilegios: un servicio en internet nunca debe correr como root.
RUN useradd --create-home --uid 10001 sentinel \
    && mkdir -p /app/datos \
    && chown -R sentinel:sentinel /app
USER sentinel

# Volumen recomendado: aquí viven la base SQLite y la clave (si no usas PostgreSQL).
VOLUME ["/app/datos"]

EXPOSE 8080

# La app vive en /app/datos cuando se usa SQLite dentro del contenedor.
ENV DATABASE_URL=sqlite:////app/datos/centinela.db

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8080')}/salud\", timeout=4)"

CMD ["uv", "run", "--no-dev", "python", "servidor.py"]
