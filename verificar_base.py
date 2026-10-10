import sqlite3
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "database" / "mediscan.db"


def conectar():
    """Conecta con la base de datos y activa las claves foráneas."""
    conexion = sqlite3.connect(DATABASE_FILE)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def mostrar_tablas(conexion):
    print("\n" + "=" * 60)
    print("1. TABLAS DE LA BASE DE DATOS")
    print("=" * 60)

    tablas = conexion.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    for tabla in tablas:
        print(f"  ✓ {tabla[0]}")


def mostrar_areas(conexion):
    print("\n" + "=" * 60)
    print("2. ÁREAS")
    print("=" * 60)

    areas = conexion.execute("""
        SELECT id, nombre
        FROM areas
        ORDER BY id
    """).fetchall()

    for id_area, nombre in areas:
        print(f"  {id_area}. {nombre}")

    print(f"\n  Total: {len(areas)}")


def mostrar_sedes(conexion):
    print("\n" + "=" * 60)
    print("3. SEDES")
    print("=" * 60)

    sedes = conexion.execute("""
        SELECT id, nombre, direccion, telefono
        FROM sedes
        ORDER BY id
    """).fetchall()

    for id_sede, nombre, direccion, telefono in sedes:
        print(f"\n  {id_sede}. {nombre}")
        print(f"     Dirección: {direccion}")
        print(f"     Teléfono:  {telefono}")

    print(f"\n  Total: {len(sedes)}")


def mostrar_estudios(conexion):
    print("\n" + "=" * 60)
    print("4. ESTUDIOS")
    print("=" * 60)

    estudios = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            a.nombre,
            e.duracion_minutos
        FROM estudios e
        JOIN areas a ON e.area_id = a.id
        ORDER BY e.id
    """).fetchall()

    for id_estudio, nombre, area, duracion in estudios:
        print(
            f"  {id_estudio:2}. {nombre} "
            f"| Área: {area} "
            f"| Duración: {duracion} min"
        )

    print(f"\n  Total: {len(estudios)}")


def mostrar_estudios_por_sede(conexion):
    print("\n" + "=" * 60)
    print("5. ESTUDIOS DISPONIBLES POR SEDE")
    print("=" * 60)

    sedes = conexion.execute("""
        SELECT id, nombre
        FROM sedes
        ORDER BY id
    """).fetchall()

    for sede_id, sede_nombre in sedes:
        estudios = conexion.execute("""
         SELECT e.nombre
         FROM sede_estudios se
         JOIN estudios e ON se.estudio_id = e.id
         WHERE se.sede_id = ?
         AND se.activo = 1
         ORDER BY e.id
        """, (sede_id,)).fetchall()

        print(f"\n  {sede_nombre}:")
        for (nombre_estudio,) in estudios:
            print(f"     ✓ {nombre_estudio}")

        print(f"     Total: {len(estudios)}")


def mostrar_relaciones_sede_estudio(conexion):
    print("\n" + "=" * 60)
    print("RELACIONES SEDE ↔ ESTUDIO")
    print("=" * 60)

    relaciones = conexion.execute("""
        SELECT
            s.nombre,
            e.nombre,
            se.activo
        FROM sede_estudios se
        JOIN sedes s
            ON s.id = se.sede_id
        JOIN estudios e
            ON e.id = se.estudio_id
        ORDER BY e.id, s.id
    """).fetchall()

    for sede, estudio, activo in relaciones:

        estado = "ACTIVA" if activo else "INACTIVA"

        print(
            f"  {estudio:<25} "
            f"| {sede:<20} "
            f"| {estado}"
        )

    print(f"\n  Total de relaciones: {len(relaciones)}")


def mostrar_horarios(conexion):
    print("\n" + "=" * 60)
    print("6. HORARIOS")
    print("=" * 60)

    cantidad = conexion.execute("""
        SELECT COUNT(*)
        FROM horarios
    """).fetchone()[0]

    print(f"  Total de horarios registrados: {cantidad}")

    dias = {
        1: "Lunes",
        2: "Martes",
        3: "Miércoles",
        4: "Jueves",
        5: "Viernes",
        6: "Sábado",
        7: "Domingo"
    }

    horarios = conexion.execute("""
        SELECT
            s.nombre,
            e.nombre,
            h.dia_semana,
            h.hora_inicio,
            h.hora_fin
        FROM horarios h
        JOIN sedes s ON h.sede_id = s.id
        JOIN estudios e ON h.estudio_id = e.id
        ORDER BY s.id, e.id, h.dia_semana
    """).fetchall()

    sede_actual = None

    for sede, estudio, dia, inicio, fin in horarios:
        if sede != sede_actual:
            print(f"\n  {sede}:")
            sede_actual = sede

        print(
            f"     {estudio:<25} "
            f"{dias[dia]:<10} "
            f"{inicio} - {fin}"
        )



def verificar_relaciones(conexion):
    print("\n" + "=" * 60)
    print("7. VERIFICACIÓN DE RELACIONES")
    print("=" * 60)

    relaciones = conexion.execute("""
        SELECT COUNT(*)
        FROM sede_estudios
    """).fetchone()[0]

    horarios = conexion.execute("""
        SELECT COUNT(*)
        FROM horarios
    """).fetchone()[0]

    horarios_validos = conexion.execute("""
        SELECT COUNT(*)
        FROM horarios h
        JOIN sede_estudios se
            ON h.sede_id = se.sede_id
            AND h.estudio_id = se.estudio_id
    """).fetchone()[0]

    print(f"  Relaciones sede-estudio: {relaciones}")
    print(f"  Horarios registrados: {horarios}")
    print(f"  Horarios con relación válida: {horarios_validos}")

    if horarios == horarios_validos:
        print("  ✓ Todos los horarios tienen una relación válida.")
    else:
        print("  ⚠ Se encontraron horarios sin relación válida.")


def verificar_administrador(conexion):
    print("\n" + "=" * 60)
    print("8. ADMINISTRADOR DE PRUEBA")
    print("=" * 60)

    admin = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            dni,
            email,
            rol,
            activo
        FROM usuarios
        WHERE rol = 'admin'
    """).fetchall()

    if not admin:
        print("  ✗ No se encontró ningún administrador.")
        return

    for usuario in admin:
        id_usuario, nombre, apellido, dni, email, rol, activo = usuario

        print(f"  ID:       {id_usuario}")
        print(f"  Nombre:   {nombre} {apellido}")
        print(f"  DNI:      {dni}")
        print(f"  Email:    {email}")
        print(f"  Rol:      {rol}")
        print(f"  Activo:   {'Sí' if activo else 'No'}")


def verificar_integridad(conexion):
    print("\n" + "=" * 60)
    print("9. INTEGRIDAD DE SQLITE")
    print("=" * 60)

    resultado = conexion.execute("""
        PRAGMA integrity_check
    """).fetchone()[0]

    if resultado == "ok":
        print("  ✓ integrity_check: OK")
    else:
        print(f"  ✗ integrity_check: {resultado}")

    foreign_keys = conexion.execute("""
        PRAGMA foreign_keys
    """).fetchone()[0]

    if foreign_keys == 1:
        print("  ✓ Foreign Keys: ACTIVADAS")
    else:
        print("  ✗ Foreign Keys: DESACTIVADAS")


def main():
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE BASE DE DATOS MEDISCAN")
    print("=" * 60)

    if not DATABASE_FILE.exists():
        print("\n✗ ERROR: No se encontró la base de datos.")
        print(f"  Buscada en: {DATABASE_FILE}")
        return

    print(f"\nBase encontrada:")
    print(f"  {DATABASE_FILE}")

    conexion = conectar()

    try:
        mostrar_tablas(conexion)
        mostrar_areas(conexion)
        mostrar_sedes(conexion)
        mostrar_estudios(conexion)
        mostrar_estudios_por_sede(conexion)
        mostrar_relaciones_sede_estudio(conexion)
        mostrar_horarios(conexion)
        verificar_relaciones(conexion)
        verificar_administrador(conexion)
        verificar_integridad(conexion)

        print("\n" + "=" * 60)
        print("VERIFICACIÓN FINALIZADA")
        print("=" * 60)
        print("✓ La base de datos pudo abrirse y consultarse correctamente.")
        print("=" * 60)

    except sqlite3.Error as error:
        print("\n" + "=" * 60)
        print("✗ ERROR DE SQLITE")
        print("=" * 60)
        print(error)

    finally:
        conexion.close()
        





if __name__ == "__main__":
    main()