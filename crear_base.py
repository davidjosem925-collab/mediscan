import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_FILE = DATABASE_DIR / "mediscan.db"


# ============================================================
# DATOS INICIALES
# ============================================================

AREAS = [
    ("Diagnóstico por imágenes",),
    ("Cardiología",),
    ("Laboratorio",),
]

SEDES = [
    (
        "Sede San Justo",
        "Av. Juan Manuel de Rosas 2450, San Justo, Buenos Aires",
        "011-4444-1001",
    ),
    (
        "Sede Morón",
        "Av. Rivadavia 17850, Morón, Buenos Aires",
        "011-4444-1002",
    ),
    (
        "Sede Laferrere",
        "Av. Luro 6200, Gregorio de Laferrere, Buenos Aires",
        "011-4444-1003",
    ),
]


ESTUDIOS = [
    (
        1,
        "Resonancia magnética",
        "resonancia-magnetica",
        "Estudio de diagnóstico por imágenes que utiliza un campo magnético y ondas de radio para obtener imágenes detalladas de distintas partes del cuerpo.",
        60,
        "La preparación depende del tipo de estudio. Retirar objetos metálicos e informar al personal sobre implantes, prótesis o dispositivos médicos.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Informar antecedentes relevantes y dispositivos implantados.",
    ),
    (
        1,
        "Tomografía computada",
        "tomografia-computada",
        "Estudio que utiliza rayos X y procesamiento computarizado para obtener imágenes detalladas del cuerpo.",
        30,
        "La preparación depende del estudio solicitado. Algunos estudios pueden requerir ayuno o preparación especial.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Informar antecedentes, alergias y medicación.",
    ),
    (
        1,
        "Radiología digital",
        "radiologia-digital",
        "Estudio que utiliza rayos X para obtener imágenes de diferentes regiones del cuerpo.",
        20,
        "Generalmente no requiere preparación especial.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Informar si existe posibilidad de embarazo.",
    ),
    (
        1,
        "Ecografía",
        "ecografia",
        "Estudio que utiliza ondas de ultrasonido para obtener imágenes de órganos y tejidos internos.",
        30,
        "La preparación depende de la región que se estudie. Algunas ecografías pueden requerir ayuno o vejiga llena.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Seguir las indicaciones específicas del estudio.",
    ),
    (
        1,
        "Mamografía",
        "mamografia",
        "Estudio de diagnóstico por imágenes de las mamas que utiliza rayos X de baja dosis.",
        30,
        "Evitar desodorantes, talcos o productos similares en mamas y axilas el día del estudio, salvo indicación diferente.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Informar antecedentes relevantes y posibilidad de embarazo.",
    ),
    (
        1,
        "Densitometría ósea",
        "densitometria-osea",
        "Estudio que permite evaluar la densidad mineral de los huesos y valorar la salud ósea.",
        30,
        "Generalmente requiere poca preparación. El centro puede indicar evitar suplementos de calcio antes del estudio.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura.",
    ),
    (
        2,
        "Electrocardiograma",
        "electrocardiograma",
        "Registro de la actividad eléctrica del corazón mediante electrodos colocados sobre la piel.",
        15,
        "Generalmente no requiere ayuno. Se recomienda evitar ejercicio intenso inmediatamente antes del estudio.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura.",
    ),
    (
        2,
        "Ecocardiograma",
        "ecocardiograma",
        "Estudio que utiliza ultrasonido para obtener imágenes del corazón y evaluar su estructura y funcionamiento.",
        30,
        "Generalmente no requiere ayuno. Se recomienda asistir con ropa cómoda.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura.",
    ),
    (
        2,
        "Ergometría",
        "ergometria",
        "Prueba que registra la respuesta cardiovascular mientras la persona realiza ejercicio físico controlado.",
        45,
        "Utilizar ropa y calzado cómodos. Evitar comidas abundantes y ejercicio intenso antes del estudio. Seguir las indicaciones del centro.",
        "Orden médica, DNI y credencial de cobertura. Informar medicación y antecedentes relevantes.",
    ),
    (
        2,
        "Holter",
        "holter",
        "Monitoreo que registra la actividad eléctrica del corazón durante un período prolongado, habitualmente 24 horas.",
        30,
        "Asistir con ropa cómoda y con la piel limpia, sin cremas o aceites en la zona donde se colocarán los electrodos.",
        "Orden médica, DNI y credencial de cobertura. Informar medicación y antecedentes relevantes.",
    ),
    (
        3,
        "Análisis de sangre",
        "analisis-de-sangre",
        "Extracción de una muestra de sangre para realizar diferentes determinaciones de laboratorio.",
        15,
        "La preparación depende del análisis solicitado. Algunos estudios pueden requerir ayuno y otros no.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Cumplir las indicaciones específicas del análisis.",
    ),
    (
        3,
        "Análisis de orina",
        "analisis-de-orina",
        "Análisis de una muestra de orina para evaluar diferentes parámetros.",
        15,
        "La preparación depende del tipo de análisis solicitado y de las instrucciones del laboratorio.",
        "Orden médica cuando corresponda, DNI y credencial de cobertura. Utilizar un recipiente adecuado y seguir las instrucciones de recolección.",
    ),
]


# Estudios disponibles en cada sede.
#
# ID de sede:
# 1 = San Justo
# 2 = Morón
# 3 = Laferrere
#
# ID de estudio:
# 1 = Resonancia
# 2 = Tomografía
# 3 = Radiología
# 4 = Ecografía
# 5 = Mamografía
# 6 = Densitometría
# 7 = ECG
# 8 = Ecocardiograma
# 9 = Ergometría
# 10 = Holter
# 11 = Sangre
# 12 = Orina

SEDE_ESTUDIOS = [
    # San Justo
    (1, 1),
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (1, 7),
    (1, 8),
    (1, 9),
    (1, 10),
    (1, 11),
    (1, 12),

    # Morón
    (2, 1),
    (2, 2),
    (2, 3),
    (2, 4),
    (2, 5),
    (2, 7),
    (2, 8),
    (2, 9),
    (2, 10),
    (2, 11),
    (2, 12),

    # Laferrere
    (3, 2),
    (3, 3),
    (3, 4),
    (3, 5),
    (3, 7),
    (3, 8),
    (3, 10),
    (3, 11),
    (3, 12),
]


# ============================================================
# HORARIOS
# ============================================================

# Formato:
# (sede_id, estudio_id, dia_semana, hora_inicio, hora_fin)
#
# 1 = Lunes
# 2 = Martes
# 3 = Miércoles
# 4 = Jueves
# 5 = Viernes
# 6 = Sábado
#
# Los horarios se generan automáticamente para cada estudio
# según el horario definido para su sede.

HORARIOS = []


# Horarios generales de cada sede.
HORARIOS_SEDES = {
    1: {
        "lunes_viernes": ("08:00", "20:00"),
        "sabado": ("08:00", "13:00"),
    },
    2: {
        "lunes_viernes": ("08:00", "19:00"),
        "sabado": ("08:00", "13:00"),
    },
    3: {
        "lunes_viernes": ("08:00", "18:00"),
        "sabado": ("08:00", "13:00"),
    },
}


# Horarios particulares de determinados estudios.
HORARIOS_ESPECIALES = {
    # (sede_id, estudio_id): (inicio, fin)

    # San Justo
    (1, 5): ("08:00", "18:00"),   # Mamografía
    (1, 6): ("08:00", "18:00"),   # Densitometría
    (1, 8): ("08:00", "18:00"),   # Ecocardiograma
    (1, 9): ("08:00", "18:00"),   # Ergometría
    (1, 10): ("08:00", "18:00"),  # Holter
    (1, 11): ("07:00", "12:00"),  # Sangre
    (1, 12): ("07:00", "12:00"),  # Orina

    # Morón
    (2, 5): ("08:00", "17:00"),
    (2, 8): ("08:00", "17:00"),
    (2, 9): ("08:00", "17:00"),
    (2, 10): ("08:00", "17:00"),
    (2, 11): ("07:00", "12:00"),
    (2, 12): ("07:00", "12:00"),

    # Laferrere
    (3, 5): ("08:00", "17:00"),
    (3, 8): ("08:00", "17:00"),
    (3, 10): ("08:00", "17:00"),
    (3, 11): ("07:00", "12:00"),
    (3, 12): ("07:00", "12:00"),
}


def generar_horarios():
    """
    Genera los registros de horarios a partir de las sedes
    y los estudios disponibles en cada sede.
    """

    horarios = []

    for sede_id, estudio_id in SEDE_ESTUDIOS:

        # Verificar si el estudio tiene un horario especial.
        horario_especial = HORARIOS_ESPECIALES.get(
            (sede_id, estudio_id)
        )

        if horario_especial:
            inicio, fin = horario_especial
        else:
            inicio, fin = HORARIOS_SEDES[sede_id]["lunes_viernes"]

        # Lunes a viernes
        for dia in range(1, 6):
            horarios.append(
                (
                    sede_id,
                    estudio_id,
                    dia,
                    inicio,
                    fin,
                    1,
                )
            )

        # Sábado
        if horario_especial:
            # Los horarios especiales también se aplican
            # al sábado, pero no después de las 13:00.
            inicio_sabado = inicio
            fin_sabado = min(fin, "13:00")
        else:
            inicio_sabado, fin_sabado = HORARIOS_SEDES[sede_id]["sabado"]

        horarios.append(
            (
                sede_id,
                estudio_id,
                6,
                inicio_sabado,
                fin_sabado,
                1,
            )
        )

    return horarios


# ============================================================
# CREACIÓN DE BASE DE DATOS
# ============================================================

def crear_base_datos():

    DATABASE_DIR.mkdir(exist_ok=True)

    if DATABASE_FILE.exists():
     raise FileExistsError(
        "La base de datos ya existe. "
        "No se sobrescribirá para proteger los datos."
    )

    conexion = sqlite3.connect(DATABASE_FILE)

    # Activamos las foreign keys de SQLite.
    conexion.execute("PRAGMA foreign_keys = ON")

    cursor = conexion.cursor()

    # ========================================================
    # TABLA AREAS
    # ========================================================

    cursor.execute("""
        CREATE TABLE areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    # ========================================================
    # TABLA USUARIOS
    # ========================================================

    cursor.execute("""
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            dni TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            telefono TEXT NOT NULL,
            password TEXT NOT NULL,
            obra_social TEXT NOT NULL DEFAULT 'Particular',
            numero_afiliado TEXT,
            rol TEXT NOT NULL DEFAULT 'paciente'
                CHECK (rol IN ('paciente', 'admin')),
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),
            fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ========================================================
    # TABLA ESTUDIOS
    # ========================================================

    cursor.execute("""
        CREATE TABLE estudios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,
            nombre TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            descripcion TEXT NOT NULL,
            duracion_minutos INTEGER NOT NULL
                CHECK (duracion_minutos > 0),
            preparacion TEXT NOT NULL,
            requisitos TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),

            FOREIGN KEY (area_id)
                REFERENCES areas(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        )
    """)

    # ========================================================
    # TABLA SEDES
    # ========================================================

    cursor.execute("""
        CREATE TABLE sedes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            direccion TEXT NOT NULL,
            telefono TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1))
        )
    """)

    # ========================================================
    # TABLA SEDE_ESTUDIOS
    # ========================================================

    # ========================================================
# TABLA SEDE_ESTUDIOS
# ========================================================

    cursor.execute("""
    CREATE TABLE sede_estudios (
        sede_id INTEGER NOT NULL,
        estudio_id INTEGER NOT NULL,

        activo INTEGER NOT NULL DEFAULT 1
            CHECK (activo IN (0, 1)),

        PRIMARY KEY (sede_id, estudio_id),

        FOREIGN KEY (sede_id)
            REFERENCES sedes(id)
            ON UPDATE CASCADE
            ON DELETE CASCADE,

        FOREIGN KEY (estudio_id)
            REFERENCES estudios(id)
            ON UPDATE CASCADE
            ON DELETE CASCADE
    )
    """)

    # ========================================================
    # TABLA HORARIOS
    # ========================================================

    cursor.execute("""
        CREATE TABLE horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sede_id INTEGER NOT NULL,
            estudio_id INTEGER NOT NULL,
            dia_semana INTEGER NOT NULL
                CHECK (dia_semana BETWEEN 1 AND 6),
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            activo INTEGER NOT NULL DEFAULT 1
                CHECK (activo IN (0, 1)),

            FOREIGN KEY (sede_id, estudio_id)
                REFERENCES sede_estudios(sede_id, estudio_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,

            UNIQUE (
                sede_id,
                estudio_id,
                dia_semana
            )
        )
    """)

    # ========================================================
    # TABLA TURNOS
    # ========================================================

    cursor.execute("""
        CREATE TABLE turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,

            usuario_id INTEGER NOT NULL,
            estudio_id INTEGER NOT NULL,
            sede_id INTEGER NOT NULL,

            fecha DATE NOT NULL,
            hora TEXT NOT NULL,

            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (
                    estado IN (
                        'pendiente',
                        'confirmado',
                        'cancelado',
                        'realizado',
                        'no_asistio'
                    )
                ),

            observaciones TEXT,

            fecha_creacion DATETIME NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (usuario_id)
                REFERENCES usuarios(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (estudio_id)
                REFERENCES estudios(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (sede_id)
                REFERENCES sedes(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            FOREIGN KEY (sede_id, estudio_id)
                REFERENCES sede_estudios(sede_id, estudio_id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT,

            UNIQUE (
                estudio_id,
                sede_id,
                fecha,
                hora
            )
        )
    """)

    # ========================================================
    # ÍNDICES
    # ========================================================

    cursor.execute("""
        CREATE INDEX idx_turnos_fecha
        ON turnos(fecha)
    """)

    cursor.execute("""
        CREATE INDEX idx_turnos_usuario
        ON turnos(usuario_id)
    """)

    cursor.execute("""
        CREATE INDEX idx_turnos_sede
        ON turnos(sede_id)
    """)

    cursor.execute("""
        CREATE INDEX idx_turnos_estudio
        ON turnos(estudio_id)
    """)

    # ========================================================
    # INSERTAR AREAS
    # ========================================================

    cursor.executemany("""
        INSERT INTO areas (nombre)
        VALUES (?)
    """, AREAS)

    # ========================================================
    # INSERTAR SEDES
    # ========================================================

    cursor.executemany("""
        INSERT INTO sedes (
            nombre,
            direccion,
            telefono
        )
        VALUES (?, ?, ?)
    """, SEDES)

    # ========================================================
    # INSERTAR ESTUDIOS
    # ========================================================

    cursor.executemany("""
        INSERT INTO estudios (
            area_id,
            nombre,
            slug,
            descripcion,
            duracion_minutos,
            preparacion,
            requisitos
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ESTUDIOS)

    # ========================================================
    # INSERTAR RELACIÓN SEDE ↔ ESTUDIO
    # ========================================================

    cursor.executemany("""
        INSERT INTO sede_estudios (
            sede_id,
            estudio_id
        )
        VALUES (?, ?)
    """, SEDE_ESTUDIOS)

    # ========================================================
    # INSERTAR HORARIOS
    # ========================================================

    horarios = generar_horarios()

    cursor.executemany("""
        INSERT INTO horarios (
            sede_id,
            estudio_id,
            dia_semana,
            hora_inicio,
            hora_fin,
            activo
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, horarios)

    # ========================================================
    # USUARIO ADMINISTRADOR DE PRUEBA
    # ========================================================

    password_admin = os.environ.get("ADMIN_PASSWORD")

    if not password_admin:
        raise ValueError(
         "Debés configurar la variable de entorno ADMIN_PASSWORD "
         "antes de crear la base de datos."
        )

    password_hash = generate_password_hash(password_admin)

    cursor.execute("""
        INSERT INTO usuarios (
            nombre,
            apellido,
            dni,
            email,
            telefono,
            password,
            rol
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "Administrador",
        "Mediscan",
        "00000000",
        "admin@mediscan.test",
        "011-4444-1000",
        password_hash,
        "admin",
    ))

    # ========================================================
    # GUARDAR CAMBIOS
    # ========================================================

    conexion.commit()
    conexion.close()

    print()
    print("=" * 60)
    print("BASE DE DATOS MEDISCAN CREADA CORRECTAMENTE")
    print("=" * 60)
    print()
    print(f"Archivo: {DATABASE_FILE}")
    print()
    print("Tablas creadas:")
    print("  - usuarios")
    print("  - areas")
    print("  - estudios")
    print("  - sedes")
    print("  - sede_estudios")
    print("  - horarios")
    print("  - turnos")
    print()
    print(f"Áreas: {len(AREAS)}")
    print(f"Sedes: {len(SEDES)}")
    print(f"Estudios: {len(ESTUDIOS)}")
    print(f"Relaciones sede-estudio: {len(SEDE_ESTUDIOS)}")
    print(f"Horarios creados: {len(horarios)}")
    print()
    print("Administrador inicial creado correctamente.")
    print("Email: admin@mediscan.test")
    print("Contraseña: configurada mediante ADMIN_PASSWORD")
    print()
    print("IMPORTANTE: estas credenciales son solamente para desarrollo.")
    print("=" * 60)


if __name__ == "__main__":
    crear_base_datos()