"""Comandos de línea de comandos para administrar Centinela."""
import click
from flask.cli import with_appcontext

from extensions import db
from models import (
    Alumno,
    Asignacion,
    Aviso,
    Grupo,
    Horario,
    Maestro,
    Materia,
    User,
)
from services.credenciales import asignar_credencial
from services.cuentas import crear_usuario


def registrar_comandos(app):
    """Registra los comandos personalizados en la aplicación."""
    app.cli.add_command(comando_inicializar)
    app.cli.add_command(comando_datos_prueba)
    app.cli.add_command(comando_crear_credenciales)


@click.command("init-db")
@with_appcontext
def comando_inicializar():
    """Crea todas las tablas de la base de datos."""
    db.create_all()
    click.echo("Base de datos inicializada correctamente.")


def _existe(username):
    return User.query.filter_by(username=username).first() is not None


@click.command("seed")
@with_appcontext
def comando_datos_prueba():
    """Carga datos de demostración (usuarios, grupos, materias, etc.)."""
    if _existe("admin"):
        click.echo("Los datos de prueba ya estaban cargados.")
        return
    cargar_datos_demo()
    click.echo("Datos de prueba cargados:")
    click.echo("  admin / admin123 (Administrador)")
    click.echo("  director / director123 (Directivo)")
    click.echo("  prof.mate / docente123 (Docente)")
    click.echo("  tutor / tutor123 (Tutor)")
    click.echo("  alumno1 / alumno123 (Alumno)")


def cargar_datos_demo():
    """Crea los usuarios y datos de demostración (sin mensajes de consola).

    Se usa tanto desde el comando `seed` como al arrancar el ejecutable.
    """
    db.create_all()

    if _existe("admin"):
        return

    # ---- Usuarios base -------------------------------------------------
    admin = crear_usuario("admin", "Ana", "Gómez", rol="admin", password="admin123")
    crear_usuario("director", "Luis", "Ramírez", rol="directivo", password="director123")

    tutor = crear_usuario("tutor", "María", "López", rol="tutor", password="tutor123")
    tutor2 = crear_usuario("tutor2", "José", "Pérez", rol="tutor", password="tutor123")
    db.session.flush()

    # ---- Docentes ------------------------------------------------------
    prof_mate = crear_usuario("prof.mate", "Carlos", "Sánchez", rol="docente", password="docente123")
    prof_hist = crear_usuario("prof.hist", "Lucía", "Torres", rol="docente", password="docente123")
    m_mate = Maestro(usuario=prof_mate, numero_empleado="EMP-001", especialidad="Matemáticas")
    m_hist = Maestro(usuario=prof_hist, numero_empleado="EMP-002", especialidad="Historia")
    db.session.add_all([m_mate, m_hist])

    # ---- Grupos y materias --------------------------------------------
    grupo_a = Grupo(nombre="1° A", nivel="Secundaria", turno="Matutino")
    grupo_b = Grupo(nombre="2° B", nivel="Secundaria", turno="Vespertino")
    db.session.add_all([grupo_a, grupo_b])

    mate = Materia(nombre="Matemáticas", clave="MAT", color="#2563eb")
    hist = Materia(nombre="Historia", clave="HIS", color="#0ea5e9")
    cien = Materia(nombre="Ciencias", clave="CIE", color="#0891b2")
    db.session.add_all([mate, hist, cien])
    db.session.flush()

    # ---- Asignaciones y horario ---------------------------------------
    db.session.add_all([
        Asignacion(maestro=m_mate, materia=mate, grupo=grupo_a),
        Asignacion(maestro=m_hist, materia=hist, grupo=grupo_a),
        Asignacion(maestro=m_mate, materia=mate, grupo=grupo_b),
        Horario(grupo=grupo_a, materia=mate, maestro=m_mate, dia="lunes",
                hora_inicio="07:00", hora_fin="08:00"),
        Horario(grupo=grupo_a, materia=hist, maestro=m_hist, dia="lunes",
                hora_inicio="08:00", hora_fin="09:00"),
    ])

    # ---- Alumnos -------------------------------------------------------
    datos_alumnos = [
        ("alumno1", "Diego", "López", "MAT-001", grupo_a, tutor),
        ("alumno2", "Sofía", "López", "MAT-002", grupo_a, tutor),
        ("alumno3", "Pedro", "Pérez", "MAT-003", grupo_b, tutor2),
        ("alumno4", "Valeria", "Pérez", "MAT-004", grupo_b, tutor2),
    ]
    for username, nombres, apellidos, matricula, grupo, t in datos_alumnos:
        u = crear_usuario(username, nombres, apellidos, rol="alumno", password="alumno123")
        db.session.add(Alumno(usuario=u, matricula=matricula, grupo=grupo, tutor=t))
        db.session.flush()
        asignar_credencial(u, tipo="alumno")

    db.session.flush()
    asignar_credencial(prof_mate, tipo="docente")
    asignar_credencial(prof_hist, tipo="docente")

    db.session.flush()
    db.session.add(Aviso(
        titulo="Bienvenidos al ciclo escolar",
        mensaje="Les damos la bienvenida al nuevo ciclo. Revisen los horarios publicados.",
        destinatario_tipo="todos",
        importante=True,
        autor_id=admin.id,
    ))

    db.session.commit()


@click.command("crear-credenciales")
@with_appcontext
def comando_crear_credenciales():
    """Genera las credenciales QR que falten para alumnos y docentes."""
    creadas = 0
    for usuario in User.query.all():
        if usuario.rol not in ("alumno", "docente"):
            continue
        if not usuario.credencial:
            asignar_credencial(usuario, tipo=usuario.rol)
            creadas += 1
    db.session.commit()
    click.echo(f"Credenciales QR creadas: {creadas}.")
