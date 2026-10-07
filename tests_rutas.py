"""Recorre todas las rutas principales como admin para detectar errores."""
from app import app
from models import Alumno, FactorRiesgo, Grupo, Justificante, Maestro, Materia

RUTAS_ESTATICAS = [
    "/panel",
    "/maestros/",
    "/maestros/nuevo",
    "/alumnos/",
    "/alumnos/nuevo",
    "/grupos/",
    "/grupos/nuevo",
    "/materias/",
    "/materias/nuevo",
    "/calificaciones/",
    "/calificaciones/capturar",
    "/asistencia/",
    "/asistencia/pasar-lista",
    "/factores/",
    "/factores/nuevo",
    "/justificantes/",
    "/justificantes/nuevo",
    "/avisos/",
    "/avisos/nuevo",
    "/perfil/",
    "/perfil/alertas",
    "/accesos/",
    "/accesos/registros",
]


def recorrer():
    cliente = app.test_client()
    r = cliente.post("/auth/admin", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 302, "no se pudo entrar como admin"

    fallos = []
    for url in RUTAS_ESTATICAS:
        resp = cliente.get(url)
        if resp.status_code != 200:
            fallos.append((url, resp.status_code))

    with app.app_context():
        alumno = Alumno.query.first()
        maestro = Maestro.query.first()
        grupo = Grupo.query.first()
        materia = Materia.query.first()
        factor = FactorRiesgo.query.first()
        just = Justificante.query.first()

    dinamicas = [
        f"/alumnos/{alumno.id}",
        f"/alumnos/{alumno.id}/editar",
        f"/alumnos/{alumno.id}/credencial",
        f"/maestros/{maestro.id}",
        f"/maestros/{maestro.id}/editar",
        f"/maestros/{maestro.id}/credencial",
        f"/grupos/{grupo.id}",
        f"/grupos/{grupo.id}/editar",
        f"/materias/{materia.id}/editar",
    ]
    if factor:
        dinamicas.append(f"/factores/{factor.id}")
    if just:
        dinamicas.append(f"/justificantes/{just.id}")

    for url in dinamicas:
        resp = cliente.get(url)
        if resp.status_code != 200:
            fallos.append((url, resp.status_code))

    if fallos:
        print("RUTAS CON ERROR:")
        for url, code in fallos:
            print(f"  {code}  {url}")
        raise SystemExit(1)
    print(f"Todas las {len(RUTAS_ESTATICAS) + len(dinamicas)} vistas responden 200.")


if __name__ == "__main__":
    recorrer()