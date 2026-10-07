"""Prueba funcional rápida del sistema (login, QR, checador)."""
from app import app
from models import RegistroAcceso, User
from services.credenciales import alternar_marcaje, buscar_por_token, qr_data_uri


def _cliente():
    return app.test_client()


def probar_login_nombre_completo():
    c = _cliente()
    r = c.post(
        "/auth/login",
        data={"nombre": "Carlos Sánchez", "password": "docente123"},
        follow_redirects=False,
    )
    assert r.status_code == 302, f"login docente falló: {r.status_code}"
    assert "/panel" in r.headers["Location"], r.headers["Location"]
    print("  [OK] Login docente por nombre completo")


def probar_login_admin_separado():
    c = _cliente()
    # Un docente NO debe entrar por la puerta de admin.
    r = c.post(
        "/auth/admin",
        data={"username": "prof.mate", "password": "docente123"},
    )
    assert b"incorrectos" in r.data, "docente entró por el acceso admin"
    # El admin sí entra por su puerta.
    r2 = c.post(
        "/auth/admin",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert r2.status_code == 302, "admin no pudo entrar"
    print("  [OK] Acceso admin separado funciona")


def probar_admin_no_entra_por_general():
    c = _cliente()
    r = c.post(
        "/auth/login",
        data={"nombre": "Ana Gómez", "password": "admin123"},
        follow_redirects=False,
    )
    assert r.status_code == 302 and "/auth/admin" in r.headers["Location"], r.headers
    print("  [OK] El admin es redirigido a su acceso propio")


def probar_credenciales_y_qr():
    with app.app_context():
        alumno = User.query.filter_by(username="alumno1").first()
        assert alumno.credencial, "el alumno no tiene credencial"
        uri = qr_data_uri(alumno.credencial.token)
        assert uri.startswith("data:image/png;base64,"), "el QR no se generó"
        assert len(uri) > 500, "el QR parece vacío"
        # Todas las personas (alumnos y docentes) deben tener credencial.
        faltan = [
            u.username
            for u in User.query.all()
            if u.rol in ("alumno", "docente") and not u.credencial
        ]
        assert not faltan, f"sin credencial: {faltan}"
    print("  [OK] Credenciales QR generadas para alumnos y docentes")


def probar_checador_entrada_salida():
    with app.app_context():
        antes = RegistroAcceso.query.count()
        alumno = User.query.filter_by(username="alumno1").first()
        cred = buscar_por_token(alumno.credencial.token)
        assert cred, "no se encontró la credencial por token"
        r1 = alternar_marcaje(cred)
        r2 = alternar_marcaje(cred)
        assert r1.tipo == "entrada", r1.tipo
        assert r2.tipo == "salida", r2.tipo
        assert RegistroAcceso.query.count() == antes + 2
    print("  [OK] Escaneo alterna entrada y salida")


def probar_vistas_admin():
    c = _cliente()
    c.post("/auth/admin", data={"username": "admin", "password": "admin123"})
    with app.app_context():
        alumno = User.query.filter_by(username="alumno1").first()
        maestro = User.query.filter_by(username="prof.mate").first()
        aid = alumno.alumno.id
        mid = maestro.maestro.id
    for url in [
        "/panel",
        "/accesos/",
        "/accesos/registros",
        f"/alumnos/{aid}/credencial",
        f"/maestros/{mid}/credencial",
        "/alumnos/",
        "/maestros/",
    ]:
        r = c.get(url)
        assert r.status_code == 200, f"{url} -> {r.status_code}"
    print("  [OK] Vistas de admin responden 200")


def probar_vistas_alumno_docente():
    # Alumno
    c = _cliente()
    c.post("/auth/login", data={"nombre": "Diego López", "password": "alumno123"})
    for url in ["/panel", "/perfil/credencial"]:
        r = c.get(url)
        assert r.status_code == 200, f"alumno {url} -> {r.status_code}"
    # Docente
    c2 = _cliente()
    c2.post("/auth/login", data={"nombre": "Carlos Sánchez", "password": "docente123"})
    for url in ["/panel", "/perfil/credencial", "/accesos/"]:
        r = c2.get(url)
        assert r.status_code == 200, f"docente {url} -> {r.status_code}"
    print("  [OK] Paneles y credencial de alumno/docente responden 200")


def probar_nombres_duplicados_bloqueados():
    """No debe poder crearse dos cuentas con el mismo nombre completo."""
    from services.cuentas import crear_cuenta_con_password

    with app.app_context():
        try:
            crear_cuenta_con_password("Diego", "López", rol="alumno")
        except ValueError:
            pass
        else:
            raise AssertionError("se permitió un nombre completo duplicado")
    # Y por HTTP, el formulario debe rechazarlo con un aviso.
    c = _cliente()
    c.post("/auth/admin", data={"username": "admin", "password": "admin123"})
    r = c.post(
        "/alumnos/nuevo",
        data={
            "nombres": "Carlos",
            "apellidos": "Sánchez",
            "matricula": "DUP-001",
        },
        follow_redirects=True,
    )
    assert b"Ya existe una cuenta" in r.data, "el aviso de duplicado no apareció"
    print("  [OK] Los nombres completos duplicados se rechazan")


def probar_editar_no_borra_username():
    """Editar sin tocar el usuario no debe dejar el username vacío."""
    c = _cliente()
    c.post("/auth/admin", data={"username": "admin", "password": "admin123"})
    with app.app_context():
        alumno = User.query.filter_by(username="alumno1").first()
        aid = alumno.alumno.id
        username_antes = alumno.username
        matricula = alumno.alumno.matricula
    c.post(
        f"/alumnos/{aid}/editar",
        data={"nombres": "Diego", "apellidos": "López", "matricula": matricula},
    )
    with app.app_context():
        usuario = User.query.filter_by(username=username_antes).first()
        assert usuario is not None, "el username se perdió al editar"
    print("  [OK] Editar no borra el usuario interno")


if __name__ == "__main__":
    print("Ejecutando pruebas funcionales...")
    probar_login_nombre_completo()
    probar_login_admin_separado()
    probar_admin_no_entra_por_general()
    probar_credenciales_y_qr()
    probar_checador_entrada_salida()
    probar_vistas_admin()
    probar_vistas_alumno_docente()
    probar_nombres_duplicados_bloqueados()
    probar_editar_no_borra_username()
    print("\nTodas las pruebas pasaron correctamente.")