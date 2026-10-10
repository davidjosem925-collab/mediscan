
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
import sqlite3
from pathlib import Path
from werkzeug.utils import secure_filename
import unicodedata
import re
import os


# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "database" / "mediscan.db"



# ============================================================
# CONEXIÓN A LA BASE DE DATOS
# ============================================================

def obtener_conexion():
    conexion = sqlite3.connect(
        DATABASE_FILE,
        timeout=10
    )

    conexion.row_factory = sqlite3.Row

    conexion.execute(
        "PRAGMA foreign_keys = ON"
    )

    conexion.execute(
        "PRAGMA busy_timeout = 10000"
    )

    return conexion


# ============================================================
# GENERAR SLUG
# ============================================================

def generar_slug(texto):

    texto = texto.strip().lower()

    # Eliminar tildes
    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    # Reemplazar caracteres que no sean letras o números
    texto = re.sub(r"[^a-z0-9]+", "-", texto)

    # Eliminar guiones del principio y final
    texto = texto.strip("-")

    return texto

# ============================================================
# GENERAR HORARIOS
# ============================================================

def generar_horarios(hora_inicio, hora_fin, duracion_minutos):
    horarios = []

    inicio = datetime.strptime(hora_inicio, "%H:%M")
    fin = datetime.strptime(hora_fin, "%H:%M")

    actual = inicio

    while actual + timedelta(minutes=duracion_minutos) <= fin:
        horarios.append(actual.strftime("%H:%M"))
        actual += timedelta(minutes=duracion_minutos)

    return horarios


# ============================================================
# RUTA PRINCIPAL
# ============================================================

@app.route("/")
def inicio():

    conexion = obtener_conexion()

    estudios = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.descripcion,
            e.duracion_minutos,
            a.nombre AS area
        FROM estudios e
        JOIN areas a ON e.area_id = a.id
        WHERE e.activo = 1
        ORDER BY e.id
    """).fetchall()

    conexion.close()

    return render_template(
        "index.html",
        estudios=estudios
    )


# ============================================================
# RUTA DE PRUEBA DE BASE DE DATOS
# ============================================================

@app.route("/prueba-db")
def prueba_db():

    conexion = obtener_conexion()

    cantidad = conexion.execute(
        "SELECT COUNT(*) AS total FROM estudios"
    ).fetchone()["total"]

    conexion.close()

    return f"Conexión correcta. Hay {cantidad} estudios en la base de datos."


# ============================================================
# DETALLE DEL ESTUDIO
# ============================================================

@app.route("/estudios/<slug>")
def detalle_estudio(slug):

    conexion = obtener_conexion()

    estudio = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.descripcion,
            e.duracion_minutos,
            e.preparacion,
            e.requisitos,
            a.nombre AS area
        FROM estudios e
        JOIN areas a ON e.area_id = a.id
        WHERE e.slug = ? AND e.activo = 1
    """, (slug,)).fetchone()

    conexion.close()

    if estudio is None:
        return "Estudio no encontrado", 404

    return render_template(
        "estudio.html",
        estudio=estudio
    )


# ============================================================
# SELECCIONAR SEDE
# ============================================================

@app.route("/estudios/<slug>/reservar")
def reservar_turno(slug):

    if "usuario_id" not in session:
     return redirect(url_for("login"))

    if session.get("rol") != "paciente":
     return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    estudio = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.descripcion,
            e.duracion_minutos,
            a.nombre AS area
        FROM estudios e
        JOIN areas a ON e.area_id = a.id
        WHERE e.slug = ? AND e.activo = 1
    """, (slug,)).fetchone()

    if estudio is None:
        conexion.close()
        return "Estudio no encontrado", 404

    sedes = conexion.execute("""
    SELECT
        s.id,
        s.nombre,
        s.direccion,
        s.telefono

    FROM sedes s

    JOIN sede_estudios se
        ON s.id = se.sede_id

    WHERE se.estudio_id = ?
      AND se.activo = 1
      AND s.activo = 1

    ORDER BY s.id
    """, (
    estudio["id"],
    )).fetchall()
    conexion.close()

    return render_template(
        "reservar.html",
        estudio=estudio,
        sedes=sedes
    )


# ============================================================
# SELECCIONAR FECHA Y HORARIO
# ============================================================

@app.route("/estudios/<slug>/reservar/sede/<int:sede_id>")
def seleccionar_fecha(slug, sede_id):

    if "usuario_id" not in session:
     return redirect(url_for("login"))

    if session.get("rol") != "paciente":
     return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR ESTUDIO
    # --------------------------------------------------------

    estudio = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.duracion_minutos,
            a.nombre AS area
        FROM estudios e
        JOIN areas a ON e.area_id = a.id
        WHERE e.slug = ?
          AND e.activo = 1
    """, (slug,)).fetchone()

    if estudio is None:
        conexion.close()
        return "Estudio no encontrado", 404

    # --------------------------------------------------------
    # BUSCAR SEDE
    # --------------------------------------------------------

    sede = conexion.execute("""
        SELECT
            s.id,
            s.nombre,
            s.direccion,
            s.telefono
        FROM sedes s
        JOIN sede_estudios se
            ON s.id = se.sede_id
        WHERE s.id = ?
          AND se.estudio_id = ?
           AND se.activo = 1
          AND s.activo = 1
    """, (
        sede_id,
        estudio["id"]
    )).fetchone()

    if sede is None:
        conexion.close()
        return "La sede no está disponible para este estudio", 404

    # --------------------------------------------------------
    # OBTENER DÍAS DISPONIBLES
    # --------------------------------------------------------

    dias_disponibles = conexion.execute("""
        SELECT DISTINCT dia_semana
        FROM horarios
        WHERE sede_id = ?
          AND estudio_id = ?
          AND activo = 1
        ORDER BY dia_semana
    """, (
        sede_id,
        estudio["id"]
    )).fetchall()

    dias = [
        fila["dia_semana"]
        for fila in dias_disponibles
    ]

    # --------------------------------------------------------
    # FECHA ACTUAL
    # --------------------------------------------------------

    hoy_fecha = date.today()

    # Se envía al HTML para impedir seleccionar días anteriores.
    hoy = hoy_fecha.isoformat()

    fecha_seleccionada = request.args.get("fecha")

    mensaje = None
    horarios_disponibles = []

    # ========================================================
    # SI EL USUARIO SELECCIONÓ UNA FECHA
    # ========================================================

    if fecha_seleccionada:

        try:

            fecha = datetime.strptime(
                fecha_seleccionada,
                "%Y-%m-%d"
            ).date()

            # ------------------------------------------------
            # IMPEDIR FECHAS ANTERIORES
            # ------------------------------------------------

            if fecha < hoy_fecha:

                mensaje = (
                    "No podés seleccionar una fecha "
                    "anterior a hoy."
                )

            else:

                # --------------------------------------------
                # COMPROBAR DÍA DE LA SEMANA
                # --------------------------------------------

                dia_semana = fecha.weekday() + 1

                if dia_semana not in dias:

                    mensaje = (
                        "El estudio no está disponible "
                        "en esa sede durante ese día."
                    )

                else:

                    # ----------------------------------------
                    # OBTENER HORARIO DE ATENCIÓN
                    # ----------------------------------------

                    horario = conexion.execute("""
                        SELECT
                            hora_inicio,
                            hora_fin
                        FROM horarios
                        WHERE sede_id = ?
                          AND estudio_id = ?
                          AND dia_semana = ?
                          AND activo = 1
                    """, (
                        sede_id,
                        estudio["id"],
                        dia_semana
                    )).fetchone()

                    if horario is None:

                        mensaje = (
                            "No hay horarios configurados "
                            "para ese día."
                        )

                    else:

                        # ------------------------------------
                        # GENERAR HORARIOS DEL ESTUDIO
                        # ------------------------------------

                        horarios_generados = generar_horarios(
                            horario["hora_inicio"],
                            horario["hora_fin"],
                            estudio["duracion_minutos"]
                        )

                        # ------------------------------------
                        # OBTENER TURNOS YA OCUPADOS
                        # ------------------------------------

                        turnos_ocupados = conexion.execute("""
                            SELECT hora
                            FROM turnos
                            WHERE estudio_id = ?
                              AND sede_id = ?
                              AND fecha = ?
                              AND estado != 'cancelado'
                        """, (
                            estudio["id"],
                            sede_id,
                            fecha_seleccionada
                        )).fetchall()

                        horas_ocupadas = {
                            turno["hora"]
                            for turno in turnos_ocupados
                        }

                        # ------------------------------------
                        # FILTRAR HORARIOS
                        # ------------------------------------

                        horarios_disponibles = []

                        ahora = datetime.now()

                        for hora in horarios_generados:

                            # Si ya está ocupado, no mostrarlo.
                            if hora in horas_ocupadas:
                                continue

                            # Si la fecha seleccionada es hoy,
                            # comprobar que el horario todavía
                            # no haya pasado.
                            if fecha == hoy_fecha:

                                fecha_hora_turno = datetime.combine(
                                    fecha,
                                    datetime.strptime(
                                        hora,
                                        "%H:%M"
                                    ).time()
                                )

                                if fecha_hora_turno <= ahora:
                                    continue

                            # Si pasó todas las validaciones,
                            # el horario está disponible.
                            horarios_disponibles.append(hora)

                        # ------------------------------------
                        # SI HOY YA NO QUEDAN HORARIOS
                        # ------------------------------------

                        if (
                            fecha == hoy_fecha
                            and not horarios_disponibles
                        ):
                            mensaje = (
                                "Ya no quedan horarios "
                                "disponibles para hoy."
                            )

        except ValueError:

            mensaje = (
                "La fecha seleccionada no es válida."
            )

    # --------------------------------------------------------
    # CERRAR CONEXIÓN
    # --------------------------------------------------------

    conexion.close()

    # --------------------------------------------------------
    # MOSTRAR PÁGINA
    # --------------------------------------------------------

    return render_template(
        "fecha.html",
        estudio=estudio,
        sede=sede,
        dias_disponibles=dias,
        hoy=hoy,
        fecha_seleccionada=fecha_seleccionada,
        mensaje=mensaje,
        horarios_disponibles=horarios_disponibles
    )

# ============================================================
# DATOS DEL PACIENTE Y CREACIÓN DEL TURNO
# ============================================================

@app.route(
    "/estudios/<slug>/reservar/sede/<int:sede_id>/datos",
    methods=["GET", "POST"]
)
def datos_paciente(slug, sede_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "paciente":
        return redirect(url_for("inicio"))

    usuario_id = session["usuario_id"]

    fecha = request.args.get("fecha")
    hora = request.args.get("hora")

    if not fecha or not hora:
        return "Faltan la fecha o la hora del turno.", 400

    try:
      fecha_hora_turno = datetime.strptime(
        f"{fecha} {hora}",
        "%Y-%m-%d %H:%M"
    )
    except ValueError:
        return "Fecha u hora inválida.", 400

    if fecha_hora_turno <= datetime.now():
        return (
        "No se puede reservar un horario que ya pasó. "
        "Por favor, seleccioná otro horario."
    ), 400

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # OBTENER PACIENTE LOGUEADO
    # --------------------------------------------------------

    paciente = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            dni,
            email,
            telefono,
            obra_social,
            numero_afiliado
        FROM usuarios
        WHERE id = ?
          AND rol = 'paciente'
          AND activo = 1
    """, (
        usuario_id,
    )).fetchone()

    if paciente is None:
        conexion.close()
        session.clear()
        return redirect(url_for("login"))

    # --------------------------------------------------------
    # BUSCAR ESTUDIO
    # --------------------------------------------------------

    estudio = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.duracion_minutos,
            a.nombre AS area
        FROM estudios e
        JOIN areas a
            ON e.area_id = a.id
        WHERE e.slug = ?
          AND e.activo = 1
    """, (
        slug,
    )).fetchone()

    if estudio is None:
        conexion.close()
        return "Estudio no encontrado", 404

    # --------------------------------------------------------
    # BUSCAR SEDE
    # --------------------------------------------------------

    # --------------------------------------------------------
# BUSCAR SEDE
# --------------------------------------------------------

    sede = conexion.execute("""
    SELECT
        s.id,
        s.nombre,
        s.direccion,
        s.telefono

    FROM sedes s

    JOIN sede_estudios se
        ON s.id = se.sede_id

    WHERE s.id = ?
      AND se.estudio_id = ?
      AND se.activo = 1
      AND s.activo = 1
    """, (
    sede_id,
    estudio["id"]
    )).fetchone()

    if sede is None:
     conexion.close()
     return "La sede no está disponible para este estudio", 404

    # ========================================================
    # POST - CREAR TURNO
    # ========================================================

    if request.method == "POST":

        # ----------------------------------------------------
        # VOLVER A COMPROBAR EL HORARIO
        # ----------------------------------------------------

        turno_existente = conexion.execute("""
            SELECT id
            FROM turnos
            WHERE estudio_id = ?
              AND sede_id = ?
              AND fecha = ?
              AND hora = ?
              AND estado != 'cancelado'
        """, (
            estudio["id"],
            sede_id,
            fecha,
            hora
        )).fetchone()

        if turno_existente:
            conexion.close()

            return (
                "Este horario acaba de ser reservado por otra persona. "
                "Por favor, seleccioná otro horario."
            ), 409

        # Ya no pedimos observaciones al paciente.
        observaciones = ""

        # ----------------------------------------------------
        # CREAR TURNO PARA EL PACIENTE LOGUEADO
        # ----------------------------------------------------

        try:

            cursor_turno = conexion.execute("""
                INSERT INTO turnos (
                    codigo,
                    usuario_id,
                    estudio_id,
                    sede_id,
                    fecha,
                    hora,
                    estado,
                    observaciones
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "TEMP",
                usuario_id,
                estudio["id"],
                sede_id,
                fecha,
                hora,
                "pendiente",
                observaciones
            ))

            turno_id = cursor_turno.lastrowid

            # ------------------------------------------------
            # GENERAR CÓDIGO MED
            # ------------------------------------------------

            ultimo_codigo = conexion.execute("""
                SELECT codigo
                FROM turnos
                WHERE codigo LIKE 'MED-%'
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            if ultimo_codigo:
                numero = int(
                    ultimo_codigo["codigo"].replace("MED-", "")
                ) + 1
            else:
                numero = 1

            codigo = f"MED-{numero:06d}"

            conexion.execute("""
                UPDATE turnos
                SET codigo = ?
                WHERE id = ?
            """, (
                codigo,
                turno_id
            ))

            conexion.commit()

        except sqlite3.IntegrityError:

            conexion.rollback()
            conexion.close()

            return (
                "No se pudo reservar ese horario porque "
                "ya fue ocupado. Por favor, seleccioná otro."
            ), 409

        # ====================================================
        # VOLVER A BUSCAR EL TURNO DESDE SQLITE
        # ====================================================

        turno = conexion.execute("""
            SELECT
                t.id,
                t.codigo,
                t.fecha,
                t.hora,
                t.estado,
                t.observaciones,

                u.id AS usuario_id,
                u.nombre AS usuario_nombre,
                u.apellido AS usuario_apellido,
                u.dni AS usuario_dni,
                u.email AS usuario_email,
                u.telefono AS usuario_telefono,
                u.obra_social AS usuario_obra_social,

                e.id AS estudio_id,
                e.nombre AS estudio_nombre,
                e.slug AS estudio_slug,
                e.duracion_minutos AS estudio_duracion,

                s.id AS sede_id,
                s.nombre AS sede_nombre,
                s.direccion AS sede_direccion,
                s.telefono AS sede_telefono

            FROM turnos t

            JOIN usuarios u
                ON t.usuario_id = u.id

            JOIN estudios e
                ON t.estudio_id = e.id

            JOIN sedes s
                ON t.sede_id = s.id

            WHERE t.id = ?
        """, (
            turno_id,
        )).fetchone()

        if turno is None:
            conexion.close()

            return (
                "El turno fue creado pero no pudo recuperarse "
                "desde la base de datos."
            ), 500

        conexion.close()

        

        # ----------------------------------------------------
        # MOSTRAR CONFIRMACIÓN
        # ----------------------------------------------------

        return render_template(
            "confirmacion.html",
            turno=turno,
            usuario={
                "nombre": turno["usuario_nombre"],
                "apellido": turno["usuario_apellido"]
            },
            estudio={
                "nombre": turno["estudio_nombre"],
                "duracion_minutos": turno["estudio_duracion"]
            },
            sede={
                "nombre": turno["sede_nombre"],
                "direccion": turno["sede_direccion"]
            }
        )

    # ========================================================
    # GET - MOSTRAR CONFIRMACIÓN PREVIA
    # ========================================================

    conexion.close()

    return render_template(
        "datos_paciente.html",
        estudio=estudio,
        sede=sede,
        paciente=paciente,
        fecha=fecha,
        hora=hora
    )






@app.route("/turnos/<int:turno_id>/cancelar", methods=["POST"])
def cancelar_turno(turno_id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "paciente":
        return redirect(url_for("inicio"))

    usuario_id = session["usuario_id"]

    conexion = obtener_conexion()

    turno = conexion.execute("""
        SELECT
            id,
            usuario_id,
            estado
        FROM turnos
        WHERE id = ?
          AND usuario_id = ?
    """, (
        turno_id,
        usuario_id
    )).fetchone()

    if turno is None:
        conexion.close()
        return "Turno no encontrado.", 404

    if turno["estado"] != "pendiente":
        conexion.close()
        return "Este turno ya no puede cancelarse.", 400

    conexion.execute("""
        UPDATE turnos
        SET estado = 'cancelado'
        WHERE id = ?
          AND usuario_id = ?
    """, (
        turno_id,
        usuario_id
    ))

    conexion.commit()
    conexion.close()

    return redirect(
        url_for(
            "mi_cuenta",
            cancelado=1
        )
    )


@app.route("/mi-cuenta")
def mi_cuenta():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "paciente":
        return redirect(url_for("inicio"))

    usuario_id = session["usuario_id"]

    conexion = obtener_conexion()

    paciente = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            dni,
            email,
            telefono,
            obra_social,
            numero_afiliado
        FROM usuarios
        WHERE id = ?
          AND rol = 'paciente'
          AND activo = 1
    """, (usuario_id,)).fetchone()

    if paciente is None:
        conexion.close()
        session.clear()
        return redirect(url_for("login"))

    turnos = conexion.execute("""
        SELECT
            t.id,
            t.codigo,
            t.fecha,
            t.hora,
            t.estado,
            t.observaciones,

            e.nombre AS estudio,
            e.duracion_minutos,

            s.nombre AS sede,
            s.direccion,
            s.telefono

        FROM turnos t

        JOIN estudios e
            ON t.estudio_id = e.id

        JOIN sedes s
            ON t.sede_id = s.id

        WHERE t.usuario_id = ?
          AND t.estado = 'pendiente'
          AND date(t.fecha) >= date('now', 'localtime')

        ORDER BY
            t.fecha ASC,
            t.hora ASC
    """, (usuario_id,)).fetchall()

    conexion.close()

    mensaje = None

  

    if request.args.get("cancelado") == "1":
     mensaje = "El turno fue cancelado correctamente."

    elif request.args.get("actualizado") == "1":
     mensaje = "Tus datos personales fueron actualizados correctamente."

    return render_template(
        "mi_cuenta.html",
        paciente=paciente,
        turnos=turnos,
        mensaje=mensaje
    )

# ============================================================
# PACIENTE - EDITAR MI CUENTA
# ============================================================

@app.route(
    "/mi-cuenta/editar",
    methods=["GET", "POST"]
)
def editar_mi_cuenta():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "paciente":
        return redirect(url_for("inicio"))

    usuario_id = session["usuario_id"]

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR PACIENTE
    # --------------------------------------------------------

    paciente = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            dni,
            email,
            telefono,
            obra_social,
            numero_afiliado
        FROM usuarios
        WHERE id = ?
          AND rol = 'paciente'
          AND activo = 1
    """, (
        usuario_id,
    )).fetchone()

    if paciente is None:
        conexion.close()
        session.clear()
        return redirect(url_for("login"))

    error = None

    # --------------------------------------------------------
    # ACTUALIZAR DATOS
    # --------------------------------------------------------

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        dni = request.form.get("dni", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefono = request.form.get("telefono", "").strip()
        obra_social = request.form.get("obra_social", "").strip()
        numero_afiliado = request.form.get(
            "numero_afiliado",
            ""
        ).strip()

        # ----------------------------------------------------
        # VALIDACIONES
        # ----------------------------------------------------

        if not nombre:
            error = "El nombre es obligatorio."

        elif not apellido:
            error = "El apellido es obligatorio."

        elif not dni:
            error = "El DNI es obligatorio."

        elif not email:
            error = "El email es obligatorio."

        elif not telefono:
            error = "El teléfono es obligatorio."

        elif not obra_social:
            error = "La obra social es obligatoria."

        else:

            # ------------------------------------------------
            # COMPROBAR DNI DUPLICADO
            # ------------------------------------------------

            usuario_dni = conexion.execute("""
                SELECT id
                FROM usuarios
                WHERE dni = ?
                  AND id != ?
            """, (
                dni,
                usuario_id
            )).fetchone()

            if usuario_dni:
                error = "Ya existe una cuenta registrada con ese DNI."

            else:

                # --------------------------------------------
                # COMPROBAR EMAIL DUPLICADO
                # --------------------------------------------

                usuario_email = conexion.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE lower(email) = lower(?)
                      AND id != ?
                """, (
                    email,
                    usuario_id
                )).fetchone()

                if usuario_email:
                    error = "Ya existe una cuenta registrada con ese email."

                else:

                    # ----------------------------------------
                    # ACTUALIZAR
                    # ----------------------------------------

                    conexion.execute("""
                        UPDATE usuarios
                        SET
                            nombre = ?,
                            apellido = ?,
                            dni = ?,
                            email = ?,
                            telefono = ?,
                            obra_social = ?,
                            numero_afiliado = ?
                        WHERE id = ?
                    """, (
                        nombre,
                        apellido,
                        dni,
                        email,
                        telefono,
                        obra_social,
                        numero_afiliado or None,
                        usuario_id
                    ))

                    conexion.commit()
                    conexion.close()

                    return redirect(
                        url_for(
                            "mi_cuenta",
                            actualizado="1"
                        )
                    )

    conexion.close()

    return render_template(
        "editar_mi_cuenta.html",
        paciente=paciente,
        error=error
    )


@app.route("/registro", methods=["GET", "POST"])
def registro():

    error = None

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        dni = request.form.get("dni", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefono = request.form.get("telefono", "").strip()

        password = request.form.get("password", "")
        confirmar_password = request.form.get(
            "confirmar_password", ""
        )

        # -----------------------------
        # VALIDACIONES
        # -----------------------------

        if (
            not nombre
            or not apellido
            or not dni
            or not email
            or not telefono
            or not password
            or not confirmar_password
        ):
            error = "Completá todos los campos."

        elif not dni.isdigit():
            error = "El DNI debe contener solamente números."

        elif len(password) < 8:
            error = "La contraseña debe tener al menos 8 caracteres."

        elif password != confirmar_password:
            error = "Las contraseñas no coinciden."

        else:

            conexion = obtener_conexion()

            usuario_existente = conexion.execute("""
                SELECT *
                FROM usuarios
                WHERE dni = ?
            """, (dni,)).fetchone()

            # ---------------------------------
            # EL DNI YA EXISTE
            # ---------------------------------

            if usuario_existente:

                # Ya tiene contraseña:
                # la cuenta ya fue registrada.
                if usuario_existente["password"]:

                    error = (
                        "Ya existe una cuenta registrada "
                        "con este DNI."
                    )

                # Existe porque reservó anteriormente,
                # pero todavía no activó su cuenta.
                else:

                    password_hash = generate_password_hash(
                        password
                    )

                    conexion.execute("""
                        UPDATE usuarios
                        SET
                            nombre = ?,
                            apellido = ?,
                            email = ?,
                            telefono = ?,
                            password = ?
                        WHERE id = ?
                    """, (
                        nombre,
                        apellido,
                        email,
                        telefono,
                        password_hash,
                        usuario_existente["id"]
                    ))

                    conexion.commit()

                    usuario_id = usuario_existente["id"]

                    conexion.close()

                    session.clear()

                    session["usuario_id"] = usuario_id
                    session["usuario_nombre"] = nombre
                    session["rol"] = "paciente"

                    return redirect(
                    url_for("inicio")
                )

            # ---------------------------------
            # USUARIO COMPLETAMENTE NUEVO
            # ---------------------------------

            else:

                password_hash = generate_password_hash(
                    password
                )

                cursor = conexion.execute("""
                    INSERT INTO usuarios (
                        nombre,
                        apellido,
                        dni,
                        email,
                        telefono,
                        password,
                        obra_social,
                        numero_afiliado,
                        rol,
                        activo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nombre,
                    apellido,
                    dni,
                    email,
                    telefono,
                    password_hash,
                    "Particular",
                    None,
                    "paciente",
                    1
                ))

                conexion.commit()

                usuario_id = cursor.lastrowid

                conexion.close()

                session.clear()

                session["usuario_id"] = usuario_id
                session["usuario_nombre"] = nombre
                session["rol"] = "paciente"

                return redirect(
                url_for("inicio")
            )

            conexion.close()

    return render_template(
        "registro.html",
        error=error
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    # Si ya inició sesión, vuelve al inicio
    if "usuario_id" in session:
        return redirect(url_for("inicio"))

    if request.method == "POST":

        dni = request.form.get("dni", "").strip()
        password = request.form.get("password", "")

        if not dni or not password:
            error = "Ingresá tu DNI y contraseña."

        else:
            conexion = obtener_conexion()

            usuario = conexion.execute("""
                SELECT *
                FROM usuarios
                WHERE dni = ?
            """, (dni,)).fetchone()

            conexion.close()

            if not usuario:
                error = "DNI o contraseña incorrectos."

            elif not usuario["activo"]:
                error = "Esta cuenta se encuentra desactivada."

            elif usuario["rol"] not in ("paciente", "admin"):
             error = "DNI o contraseña incorrectos."

            elif not usuario["password"]:
                error = (
                    "Esta cuenta todavía no tiene una "
                    "contraseña configurada."
                )

            elif not check_password_hash(
                usuario["password"],
                password
            ):
                error = "DNI o contraseña incorrectos."

            else:
                session.clear()

                

                session["usuario_id"] = usuario["id"]
                session["usuario_nombre"] = usuario["nombre"]
                session["rol"] = usuario["rol"]

                return redirect(url_for("inicio"))

    return render_template(
        "login.html",
        error=error
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("inicio"))


# ============================================================
# PANEL DE ADMINISTRACIÓN
# ============================================================

@app.route("/admin")
def admin_dashboard():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    # Solo los administradores pueden ingresar
    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # TOTAL DE TURNOS PENDIENTES
    # --------------------------------------------------------

    total_pendientes = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM turnos
        WHERE estado = 'pendiente'
    """).fetchone()["total"]

    # --------------------------------------------------------
    # TURNOS DE HOY
    # --------------------------------------------------------

    hoy = date.today().isoformat()

    turnos_hoy = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM turnos
        WHERE fecha = ?
          AND estado != 'cancelado'
    """, (hoy,)).fetchone()["total"]

    # --------------------------------------------------------
    # PACIENTES REGISTRADOS
    # --------------------------------------------------------

    total_pacientes = conexion.execute("""
        SELECT COUNT(*) AS total
        FROM usuarios
        WHERE rol = 'paciente'
          AND activo = 1
    """).fetchone()["total"]

    # --------------------------------------------------------
    # PRÓXIMOS TURNOS
    # --------------------------------------------------------

    proximos_turnos = conexion.execute("""
        SELECT
            t.id,
            t.codigo,
            t.fecha,
            t.hora,
            t.estado,

            u.nombre,
            u.apellido,
            u.dni,

            e.nombre AS estudio,

            s.nombre AS sede

        FROM turnos t

        JOIN usuarios u
            ON t.usuario_id = u.id

        JOIN estudios e
            ON t.estudio_id = e.id

        JOIN sedes s
            ON t.sede_id = s.id

        WHERE t.estado = 'pendiente'
          AND (
                t.fecha > ?
                OR (
                    t.fecha = ?
                    AND t.hora >= ?
                )
              )

        ORDER BY
            t.fecha ASC,
            t.hora ASC

        LIMIT 10
    """, (
        hoy,
        hoy,
        datetime.now().strftime("%H:%M")
    )).fetchall()

    total_estudios = conexion.execute("""
    SELECT COUNT(*)
    FROM estudios
    """).fetchone()[0]

    conexion.close()

    return render_template(
    "admin_dashboard.html",
    turnos_hoy=turnos_hoy,
    total_pendientes=total_pendientes,
    total_pacientes=total_pacientes,
    total_estudios=total_estudios,
    proximos_turnos=proximos_turnos
)



# ============================================================
# ADMINISTRACIÓN - TODOS LOS TURNOS
# ============================================================

@app.route("/admin/turnos")
def admin_turnos():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # RECIBIR FILTROS DESDE LA URL
    # --------------------------------------------------------

    fecha = request.args.get("fecha", "").strip()
    sede_id = request.args.get("sede_id", "").strip()
    estudio_id = request.args.get("estudio_id", "").strip()
    estado = request.args.get("estado", "").strip()

    # --------------------------------------------------------
    # CONSULTA BASE
    # --------------------------------------------------------

    consulta = """
        SELECT
            t.id,
            t.codigo,
            t.fecha,
            t.hora,
            t.estado,
            t.observaciones,
            t.fecha_creacion,

            u.id AS paciente_id,
            u.nombre AS paciente_nombre,
            u.apellido AS paciente_apellido,
            u.dni AS paciente_dni,

            e.id AS estudio_id,
            e.nombre AS estudio,

            s.id AS sede_id,
            s.nombre AS sede,
            s.direccion AS sede_direccion

        FROM turnos t

        JOIN usuarios u
            ON t.usuario_id = u.id

        JOIN estudios e
            ON t.estudio_id = e.id

        JOIN sedes s
            ON t.sede_id = s.id

        WHERE 1 = 1
    """

    parametros = []

    # --------------------------------------------------------
    # APLICAR FILTROS
    # --------------------------------------------------------

    if fecha:
        consulta += """
            AND t.fecha = ?
        """
        parametros.append(fecha)

    if sede_id:
        consulta += """
            AND t.sede_id = ?
        """
        parametros.append(sede_id)

    if estudio_id:
        consulta += """
            AND t.estudio_id = ?
        """
        parametros.append(estudio_id)

    if estado:
        consulta += """
            AND t.estado = ?
        """
        parametros.append(estado)

    consulta += """
        ORDER BY
            t.fecha DESC,
            t.hora DESC
    """

    # --------------------------------------------------------
    # EJECUTAR CONSULTA
    # --------------------------------------------------------

    turnos = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    # --------------------------------------------------------
    # DATOS PARA LOS SELECT DEL FORMULARIO
    # --------------------------------------------------------

    sedes = conexion.execute("""
        SELECT
            id,
            nombre
        FROM sedes
        WHERE activo = 1
        ORDER BY nombre
    """).fetchall()

    estudios = conexion.execute("""
        SELECT
            id,
            nombre
        FROM estudios
        WHERE activo = 1
        ORDER BY nombre
    """).fetchall()

    conexion.close()

    return render_template(
        "admin_turnos.html",
        turnos=turnos,
        sedes=sedes,
        estudios=estudios,
        filtro_fecha=fecha,
        filtro_sede=sede_id,
        filtro_estudio=estudio_id,
        filtro_estado=estado
    )

# ============================================================
# ADMINISTRACIÓN - DETALLE DE TURNO
# ============================================================

@app.route("/admin/turnos/<int:turno_id>")
def admin_detalle_turno(turno_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # OBTENER TURNO
    # --------------------------------------------------------

    turno = conexion.execute("""
        SELECT
            t.id,
            t.codigo,
            t.fecha,
            t.hora,
            t.estado,
            t.observaciones,
            t.fecha_creacion,

            u.id AS paciente_id,
            u.nombre AS paciente_nombre,
            u.apellido AS paciente_apellido,
            u.dni AS paciente_dni,
            u.email AS paciente_email,
            u.telefono AS paciente_telefono,
            u.obra_social AS paciente_obra_social,
            u.numero_afiliado AS paciente_numero_afiliado,

            e.id AS estudio_id,
            e.nombre AS estudio,
            e.duracion_minutos,

            a.nombre AS area,

            s.id AS sede_id,
            s.nombre AS sede,
            s.direccion AS sede_direccion,
            s.telefono AS sede_telefono

        FROM turnos t

        JOIN usuarios u
            ON t.usuario_id = u.id

        JOIN estudios e
            ON t.estudio_id = e.id

        JOIN areas a
            ON e.area_id = a.id

        JOIN sedes s
            ON t.sede_id = s.id

        WHERE t.id = ?
    """, (
        turno_id,
    )).fetchone()


    # --------------------------------------------------------
    # VERIFICAR QUE EL TURNO EXISTA
    # --------------------------------------------------------

    if turno is None:
        conexion.close()
        return "Turno no encontrado", 404


    # --------------------------------------------------------
    # OBTENER HISTORIAL DEL TURNO
    # --------------------------------------------------------

    historial = conexion.execute("""
        SELECT
            h.id,
            h.estado_anterior,
            h.estado_nuevo,

            datetime(
                h.fecha_cambio,
                '-3 hours'
            ) AS fecha_cambio_local,

            u.id AS usuario_id,
            u.nombre AS usuario_nombre,
            u.apellido AS usuario_apellido,
            u.rol AS usuario_rol

        FROM historial_turnos h

        JOIN usuarios u
            ON h.usuario_id = u.id

        WHERE h.turno_id = ?

        ORDER BY
            h.fecha_cambio DESC,
            h.id DESC
    """, (
        turno_id,
    )).fetchall()


    conexion.close()


    # --------------------------------------------------------
    # MENSAJE
    # --------------------------------------------------------

    mensaje = request.args.get("mensaje")


    # --------------------------------------------------------
    # MOSTRAR DETALLE
    # --------------------------------------------------------

    return render_template(
        "admin_detalle_turno.html",
        turno=turno,
        historial=historial,
        mensaje=mensaje
    )

# ============================================================
# ADMINISTRACIÓN - CAMBIAR ESTADO DE TURNO
# ============================================================

# ============================================================
# ADMINISTRACIÓN - CAMBIAR ESTADO DE TURNO
# ============================================================

@app.route(
    "/admin/turnos/<int:turno_id>/estado",
    methods=["POST"]
)
def admin_cambiar_estado_turno(turno_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    nuevo_estado = request.form.get(
        "estado",
        ""
    ).strip().lower()

    conexion = obtener_conexion()

    try:

        # ----------------------------------------------------
        # BUSCAR TURNO
        # ----------------------------------------------------

        turno = conexion.execute("""
            SELECT
                id,
                codigo,
                estado
            FROM turnos
            WHERE id = ?
        """, (
            turno_id,
        )).fetchone()

        if turno is None:
            return "Turno no encontrado", 404

        estado_actual = turno["estado"]

        # ----------------------------------------------------
        # TRANSICIONES PERMITIDAS
        # ----------------------------------------------------

        transiciones = {
    "pendiente": [
        "confirmado",
        "cancelado"
    ],

    "confirmado": [
        "realizado",
        "no_asistio",
        "cancelado"
    ],

    "realizado": [],

    "no_asistio": [],

    "cancelado": []
}

        # ----------------------------------------------------
        # VALIDAR ESTADO ACTUAL
        # ----------------------------------------------------

        if estado_actual not in transiciones:

            return (
                "El turno tiene un estado no válido.",
                400
            )

        # ----------------------------------------------------
        # VALIDAR NUEVO ESTADO
        # ----------------------------------------------------

        if nuevo_estado not in transiciones[estado_actual]:

            return (
                f"No se puede cambiar un turno de "
                f"'{estado_actual}' a '{nuevo_estado}'."
            ), 400

        # ----------------------------------------------------
        # ACTUALIZAR TURNO
        # ----------------------------------------------------

        conexion.execute("""
            UPDATE turnos
            SET estado = ?
            WHERE id = ?
        """, (
            nuevo_estado,
            turno_id
        ))

        # ----------------------------------------------------
        # REGISTRAR EN HISTORIAL
        # ----------------------------------------------------

        conexion.execute("""
            INSERT INTO historial_turnos (
                turno_id,
                usuario_id,
                estado_anterior,
                estado_nuevo
            )
            VALUES (?, ?, ?, ?)
        """, (
            turno_id,
            session["usuario_id"],
            estado_actual,
            nuevo_estado
        ))

        # ----------------------------------------------------
        # CONFIRMAR LAS DOS OPERACIONES
        # ----------------------------------------------------

        conexion.commit()

    except sqlite3.Error:

        # Si falla UPDATE o INSERT,
        # deshacer toda la operación.

        conexion.rollback()

        raise

    finally:

        # Se ejecuta SIEMPRE.
        conexion.close()

    # --------------------------------------------------------
    # VOLVER AL DETALLE
    # --------------------------------------------------------

    return redirect(
        url_for(
            "admin_detalle_turno",
            turno_id=turno_id,
            mensaje="Estado actualizado correctamente."
        )
    )


# ============================================================
# ADMINISTRACIÓN - PACIENTES
# ============================================================

@app.route("/admin/pacientes")
def admin_pacientes():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    # --------------------------------------------------------
    # BUSCADOR
    # --------------------------------------------------------

    busqueda = request.args.get(
        "buscar",
        ""
    ).strip()

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # CONSULTAR PACIENTES
    # --------------------------------------------------------

    if busqueda:

        patron = f"%{busqueda}%"

        pacientes = conexion.execute("""
            SELECT
                id,
                nombre,
                apellido,
                dni,
                email,
                telefono,
                obra_social,
                numero_afiliado,
                activo
            FROM usuarios
            WHERE rol = 'paciente'
              AND (
                    nombre LIKE ?
                    OR apellido LIKE ?
                    OR dni LIKE ?
                    OR email LIKE ?
              )
            ORDER BY apellido, nombre
        """, (
            patron,
            patron,
            patron,
            patron
        )).fetchall()

    else:

        pacientes = conexion.execute("""
            SELECT
                id,
                nombre,
                apellido,
                dni,
                email,
                telefono,
                obra_social,
                numero_afiliado,
                activo
            FROM usuarios
            WHERE rol = 'paciente'
            ORDER BY apellido, nombre
        """).fetchall()

    conexion.close()

    # --------------------------------------------------------
    # MOSTRAR PÁGINA
    # --------------------------------------------------------

    return render_template(
        "admin_pacientes.html",
        pacientes=pacientes,
        busqueda=busqueda
    )




# ============================================================
# ADMINISTRACIÓN - DETALLE DE PACIENTE
# ============================================================

@app.route("/admin/pacientes/<int:paciente_id>")
def admin_detalle_paciente(paciente_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # OBTENER PACIENTE
    # --------------------------------------------------------

    paciente = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            dni,
            email,
            telefono,
            obra_social,
            numero_afiliado,
            activo
        FROM usuarios
        WHERE id = ?
          AND rol = 'paciente'
    """, (
        paciente_id,
    )).fetchone()

    if paciente is None:
        conexion.close()
        return "Paciente no encontrado", 404

    # --------------------------------------------------------
    # OBTENER TURNOS DEL PACIENTE
    # --------------------------------------------------------

    turnos = conexion.execute("""
        SELECT
            t.id,
            t.codigo,
            t.fecha,
            t.hora,
            t.estado,

            e.nombre AS estudio,
            e.duracion_minutos,

            s.nombre AS sede,
            s.direccion AS sede_direccion

        FROM turnos t

        JOIN estudios e
            ON t.estudio_id = e.id

        JOIN sedes s
            ON t.sede_id = s.id

        WHERE t.usuario_id = ?

        ORDER BY
            t.fecha DESC,
            t.hora DESC
    """, (
        paciente_id,
    )).fetchall()

    conexion.close()

    mensaje = request.args.get("mensaje")

    

    return render_template(
    "admin_detalle_paciente.html",
    paciente=paciente,
    turnos=turnos,
    mensaje=mensaje
)
# ============================================================
# ADMINISTRACIÓN - EDITAR PACIENTE
# ============================================================

@app.route(
    "/admin/pacientes/<int:paciente_id>/editar",
    methods=["GET", "POST"]
)
def admin_editar_paciente(paciente_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR PACIENTE
    # --------------------------------------------------------

    paciente = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            dni,
            email,
            telefono,
            obra_social,
            numero_afiliado,
            activo
        FROM usuarios
        WHERE id = ?
          AND rol = 'paciente'
    """, (
        paciente_id,
    )).fetchone()

    if paciente is None:
        conexion.close()
        return "Paciente no encontrado", 404

    error = None

    # --------------------------------------------------------
    # GUARDAR CAMBIOS
    # --------------------------------------------------------

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        dni = request.form.get("dni", "").strip()
        email = request.form.get("email", "").strip()
        telefono = request.form.get("telefono", "").strip()
        obra_social = request.form.get("obra_social", "").strip()
        numero_afiliado = request.form.get(
            "numero_afiliado",
            ""
        ).strip()

        if not nombre or not apellido or not dni or not email or not telefono:

            error = (
                "Nombre, apellido, DNI, email y teléfono "
                "son obligatorios."
            )

        else:

            # ------------------------------------------------
            # VERIFICAR DNI DUPLICADO
            # ------------------------------------------------

            dni_existente = conexion.execute("""
                SELECT id
                FROM usuarios
                WHERE dni = ?
                  AND id != ?
            """, (
                dni,
                paciente_id
            )).fetchone()

            if dni_existente:

                error = (
                    "Ya existe otro usuario registrado "
                    "con ese DNI."
                )

            else:

                # --------------------------------------------
                # VERIFICAR EMAIL DUPLICADO
                # --------------------------------------------

                email_existente = conexion.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE LOWER(email) = LOWER(?)
                      AND id != ?
                """, (
                    email,
                    paciente_id
                )).fetchone()

                if email_existente:

                    error = (
                        "Ya existe otro usuario registrado "
                        "con ese email."
                    )

                else:

                    conexion.execute("""
                        UPDATE usuarios
                        SET
                            nombre = ?,
                            apellido = ?,
                            dni = ?,
                            email = ?,
                            telefono = ?,
                            obra_social = ?,
                            numero_afiliado = ?
                        WHERE id = ?
                          AND rol = 'paciente'
                    """, (
                        nombre,
                        apellido,
                        dni,
                        email,
                        telefono,
                        obra_social or None,
                        numero_afiliado or None,
                        paciente_id
                    ))

                    conexion.commit()
                    conexion.close()

                    return redirect(
                        url_for(
                            "admin_detalle_paciente",
                            paciente_id=paciente_id,
                            mensaje="Datos del paciente actualizados correctamente."
                        )
                    )

    conexion.close()

    return render_template(
        "admin_editar_paciente.html",
        paciente=paciente,
        error=error
    )


# ============================================================
# ADMINISTRACIÓN - CAMBIAR ESTADO DEL PACIENTE
# ============================================================

@app.route(
    "/admin/pacientes/<int:paciente_id>/estado",
    methods=["POST"]
)
def admin_cambiar_estado_paciente(paciente_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    paciente = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            activo
        FROM usuarios
        WHERE id = ?
          AND rol = 'paciente'
    """, (
        paciente_id,
    )).fetchone()

    if paciente is None:
        conexion.close()
        return "Paciente no encontrado", 404

    # Si está activo -> desactivar
    # Si está inactivo -> activar

    nuevo_estado = 0 if paciente["activo"] else 1

    conexion.execute("""
        UPDATE usuarios
        SET activo = ?
        WHERE id = ?
          AND rol = 'paciente'
    """, (
        nuevo_estado,
        paciente_id
    ))

    conexion.commit()
    conexion.close()

    if nuevo_estado:
        mensaje = "Paciente activado correctamente."
    else:
        mensaje = "Paciente desactivado correctamente."

    return redirect(
        url_for(
            "admin_detalle_paciente",
            paciente_id=paciente_id,
            mensaje=mensaje
        )
    )


# ============================================================
# ADMINISTRACIÓN - ESTUDIOS
# ============================================================

@app.route("/admin/estudios")
def admin_estudios():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # OBTENER ESTUDIOS
    # --------------------------------------------------------

    estudios = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.descripcion,
            e.duracion_minutos,
            e.activo,

            a.nombre AS area,

            COUNT(DISTINCT se.sede_id) AS cantidad_sedes

        FROM estudios e

        JOIN areas a
            ON e.area_id = a.id

        LEFT JOIN sede_estudios se
        ON e.id = se.estudio_id
        AND se.activo = 1

        GROUP BY
            e.id,
            e.nombre,
            e.slug,
            e.descripcion,
            e.duracion_minutos,
            e.activo,
            a.nombre

        ORDER BY
            a.nombre,
            e.nombre
    """).fetchall()

    conexion.close()

    return render_template(
        "admin_estudios.html",
        estudios=estudios
    )

# ============================================================
# ADMINISTRACIÓN - DETALLE DE ESTUDIO
# ============================================================

@app.route("/admin/estudios/<int:estudio_id>")
def admin_detalle_estudio(estudio_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    estudio = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.descripcion,
            e.preparacion,
            e.requisitos,
            e.duracion_minutos,
            e.activo,

            a.id AS area_id,
            a.nombre AS area

        FROM estudios e

        JOIN areas a
            ON e.area_id = a.id

        WHERE e.id = ?
    """, (
        estudio_id,
    )).fetchone()

    if estudio is None:
        conexion.close()
        return "Estudio no encontrado", 404

    # --------------------------------------------------------
    # SEDES DEL ESTUDIO
    # --------------------------------------------------------

    sedes = conexion.execute("""
    SELECT
        s.id,
        s.nombre,
        s.direccion,
        s.telefono

    FROM sedes s

    JOIN sede_estudios se
        ON s.id = se.sede_id

    WHERE se.estudio_id = ?
      AND se.activo = 1
      AND s.activo = 1

    ORDER BY s.nombre
    """, (
    estudio_id,
    )).fetchall()

    conexion.close()

    mensaje = request.args.get("mensaje")

    return render_template(
    "admin_detalle_estudio.html",
    estudio=estudio,
    sedes=sedes,
    mensaje=mensaje
)


# ============================================================
# ADMINISTRACIÓN - EDITAR ESTUDIO
# ============================================================

@app.route(
    "/admin/estudios/<int:estudio_id>/editar",
    methods=["GET", "POST"]
)
def admin_editar_estudio(estudio_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR ESTUDIO
    # --------------------------------------------------------

    estudio = conexion.execute("""
        SELECT
            id,
            nombre,
            slug,
            descripcion,
            preparacion,
            requisitos,
            duracion_minutos,
            area_id,
            activo
        FROM estudios
        WHERE id = ?
    """, (
        estudio_id,
    )).fetchone()

    if estudio is None:
        conexion.close()
        return "Estudio no encontrado", 404

    # --------------------------------------------------------
    # OBTENER ÁREAS
    # --------------------------------------------------------

    areas = conexion.execute("""
        SELECT
            id,
            nombre
        FROM areas
        ORDER BY nombre
    """).fetchall()

    # --------------------------------------------------------
    # OBTENER TODAS LAS SEDES
    # --------------------------------------------------------

    sedes = conexion.execute("""
        SELECT
            id,
            nombre,
            direccion
        FROM sedes
        ORDER BY nombre
    """).fetchall()

    # --------------------------------------------------------
    # OBTENER SEDES DONDE ESTÁ DISPONIBLE EL ESTUDIO
    # --------------------------------------------------------

    sedes_activas = conexion.execute("""
    SELECT sede_id
    FROM sede_estudios
    WHERE estudio_id = ?
      AND activo = 1
    """, (
    estudio_id,
    )).fetchall()

    sedes_activas_ids = [
        fila["sede_id"]
        for fila in sedes_activas
    ]

    error = None

    # --------------------------------------------------------
    # PROCESAR FORMULARIO DE EDICIÓN
    # --------------------------------------------------------

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        area_id = request.form.get("area_id", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        preparacion = request.form.get("preparacion", "").strip()
        requisitos = request.form.get("requisitos", "").strip()
        duracion = request.form.get(
            "duracion_minutos",
            ""
        ).strip()

        # ----------------------------------------------------
        # VALIDACIONES
        # ----------------------------------------------------

        if not nombre:

            error = "Ingresá el nombre del estudio."

        elif not area_id:

            error = "Seleccioná un área."

        elif not duracion:

            error = "Ingresá la duración del estudio."

        else:

            try:

                area_id = int(area_id)
                duracion = int(duracion)

                if duracion <= 0:
                    error = (
                        "La duración debe ser mayor "
                        "a 0 minutos."
                    )

            except ValueError:

                error = (
                    "El área o la duración no son válidos."
                )

        # ----------------------------------------------------
        # VERIFICAR ÁREA
        # ----------------------------------------------------

        if error is None:

            area = conexion.execute("""
                SELECT id
                FROM areas
                WHERE id = ?
            """, (
                area_id,
            )).fetchone()

            if area is None:
                error = (
                    "El área seleccionada no existe."
                )

        # ----------------------------------------------------
        # VERIFICAR NOMBRE DUPLICADO
        # ----------------------------------------------------

        if error is None:

            estudio_existente = conexion.execute("""
                SELECT id
                FROM estudios
                WHERE LOWER(nombre) = LOWER(?)
                  AND id != ?
            """, (
                nombre,
                estudio_id
            )).fetchone()

            if estudio_existente:

                error = (
                    "Ya existe otro estudio "
                    "con ese nombre."
                )

        # ----------------------------------------------------
        # ACTUALIZAR ESTUDIO
        # ----------------------------------------------------

        if error is None:

            conexion.execute("""
                UPDATE estudios
                SET
                    nombre = ?,
                    area_id = ?,
                    descripcion = ?,
                    preparacion = ?,
                    requisitos = ?,
                    duracion_minutos = ?
                WHERE id = ?
            """, (
                nombre,
                area_id,
                descripcion,
                preparacion,
                requisitos,
                duracion,
                estudio_id
            ))

            conexion.commit()
            conexion.close()

            return redirect(
                url_for(
                    "admin_detalle_estudio",
                    estudio_id=estudio_id,
                    mensaje=(
                        "Estudio actualizado "
                        "correctamente."
                    )
                )
            )

    # --------------------------------------------------------
    # MOSTRAR FORMULARIO
    # --------------------------------------------------------

    conexion.close()

    return render_template(
        "admin_editar_estudio.html",
        estudio=estudio,
        areas=areas,
        sedes=sedes,
        sedes_activas_ids=sedes_activas_ids,
        error=error
    )


# ============================================================
# ADMINISTRACIÓN - ACTUALIZAR SEDES DE UN ESTUDIO
# ============================================================

# ============================================================
# ADMINISTRACIÓN - ACTUALIZAR SEDES DE UN ESTUDIO
# ============================================================

@app.route(
    "/admin/estudios/<int:estudio_id>/sedes",
    methods=["POST"]
)
def admin_actualizar_sedes_estudio(estudio_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))


    # --------------------------------------------------------
    # OBTENER SEDES SELECCIONADAS
    # --------------------------------------------------------

    sedes_seleccionadas = request.form.getlist("sedes")

    # Convertimos los IDs recibidos a enteros
    sedes_seleccionadas = {
        int(sede_id)
        for sede_id in sedes_seleccionadas
        if sede_id.isdigit()
    }


    conexion = obtener_conexion()

    try:

        # ----------------------------------------------------
        # VERIFICAR QUE EL ESTUDIO EXISTA
        # ----------------------------------------------------

        estudio = conexion.execute("""
            SELECT id, nombre
            FROM estudios
            WHERE id = ?
        """, (
            estudio_id,
        )).fetchone()

        if estudio is None:
            return "Estudio no encontrado", 404


        # ----------------------------------------------------
        # OBTENER TODAS LAS SEDES
        # ----------------------------------------------------

        sedes = conexion.execute("""
            SELECT id
            FROM sedes
            ORDER BY id
        """).fetchall()


        # ----------------------------------------------------
        # ACTUALIZAR DISPONIBILIDAD
        # ----------------------------------------------------

        for sede in sedes:

            sede_id = sede["id"]

            activo = (
                1
                if sede_id in sedes_seleccionadas
                else 0
            )


            # ------------------------------------------------
            # VER SI YA EXISTE LA RELACIÓN
            # ------------------------------------------------

            relacion = conexion.execute("""
                SELECT sede_id
                FROM sede_estudios
                WHERE sede_id = ?
                  AND estudio_id = ?
            """, (
                sede_id,
                estudio_id
            )).fetchone()


            if relacion:

                # --------------------------------------------
                # YA EXISTE:
                # solamente cambiamos activo
                # --------------------------------------------

                conexion.execute("""
                    UPDATE sede_estudios
                    SET activo = ?
                    WHERE sede_id = ?
                      AND estudio_id = ?
                """, (
                    activo,
                    sede_id,
                    estudio_id
                ))

            elif activo == 1:

                # --------------------------------------------
                # NO EXISTE Y FUE SELECCIONADA:
                # creamos la relación
                # --------------------------------------------

                conexion.execute("""
                    INSERT INTO sede_estudios (
                        sede_id,
                        estudio_id,
                        activo
                    )
                    VALUES (?, ?, 1)
                """, (
                    sede_id,
                    estudio_id
                ))


        # ----------------------------------------------------
        # GUARDAR
        # ----------------------------------------------------

        conexion.commit()


    except Exception:

        conexion.rollback()
        raise


    finally:

        conexion.close()


    return redirect(
        url_for(
            "admin_editar_estudio",
            estudio_id=estudio_id,
            mensaje="Sedes actualizadas correctamente."
        )
    )

# ============================================================
# ADMINISTRACIÓN - NUEVO ESTUDIO
# ============================================================

@app.route(
    "/admin/estudios/nuevo",
    methods=["GET", "POST"]
)
def admin_nuevo_estudio():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))


    conexion = obtener_conexion()

    try:

        # ----------------------------------------------------
        # OBTENER ÁREAS
        # ----------------------------------------------------

        areas = conexion.execute("""
            SELECT
                id,
                nombre
            FROM areas
            ORDER BY nombre
        """).fetchall()


        # ----------------------------------------------------
        # OBTENER SEDES
        # ----------------------------------------------------

        sedes = conexion.execute("""
            SELECT
                id,
                nombre,
                direccion
            FROM sedes
            ORDER BY nombre
        """).fetchall()


        error = None


        # ----------------------------------------------------
        # PROCESAR FORMULARIO
        # ----------------------------------------------------

        if request.method == "POST":

            nombre = request.form.get(
                "nombre",
                ""
            ).strip()

            area_id = request.form.get(
                "area_id",
                ""
            ).strip()

            duracion = request.form.get(
                "duracion_minutos",
                ""
            ).strip()

            descripcion = request.form.get(
                "descripcion",
                ""
            ).strip()

            preparacion = request.form.get(
                "preparacion",
                ""
            ).strip()

            requisitos = request.form.get(
                "requisitos",
                ""
            ).strip()

            sedes_seleccionadas = request.form.getlist(
                "sedes"
            )


            # ------------------------------------------------
            # VALIDACIONES BÁSICAS
            # ------------------------------------------------

            if not nombre:

                error = "Ingresá el nombre del estudio."

            elif not area_id:

                error = "Seleccioná un área."

            elif not duracion:

                error = "Ingresá la duración del estudio."

            elif not sedes_seleccionadas:

                error = (
                    "Seleccioná al menos una sede "
                    "para el estudio."
                )


            # ------------------------------------------------
            # CONVERTIR DATOS
            # ------------------------------------------------

            if error is None:

                try:

                    area_id = int(area_id)
                    duracion = int(duracion)

                    sedes_ids = {
                        int(sede_id)
                        for sede_id in sedes_seleccionadas
                    }

                    if duracion <= 0:

                        error = (
                            "La duración debe ser mayor "
                            "a 0 minutos."
                        )

                except ValueError:

                    error = (
                        "El área, la duración o las sedes "
                        "seleccionadas no son válidas."
                    )


            # ------------------------------------------------
            # VERIFICAR ÁREA
            # ------------------------------------------------

            if error is None:

                area = conexion.execute("""
                    SELECT id
                    FROM areas
                    WHERE id = ?
                """, (
                    area_id,
                )).fetchone()

                if area is None:

                    error = (
                        "El área seleccionada no existe."
                    )


            # ------------------------------------------------
            # VERIFICAR SEDES
            # ------------------------------------------------

            if error is None:

                sedes_existentes = conexion.execute("""
                    SELECT id
                    FROM sedes
                """).fetchall()

                sedes_existentes_ids = {
                    fila["id"]
                    for fila in sedes_existentes
                }

                if not sedes_ids.issubset(
                    sedes_existentes_ids
                ):

                    error = (
                        "Una de las sedes seleccionadas "
                        "no existe."
                    )


            # ------------------------------------------------
            # GENERAR SLUG
            # ------------------------------------------------

            if error is None:

                slug = generar_slug(nombre)

                if not slug:

                    error = (
                        "No se pudo generar un identificador "
                        "válido para el estudio."
                    )


            # ------------------------------------------------
            # VERIFICAR NOMBRE DUPLICADO
            # ------------------------------------------------

            if error is None:

                estudio_existente = conexion.execute("""
                    SELECT id
                    FROM estudios
                    WHERE LOWER(nombre) = LOWER(?)
                """, (
                    nombre,
                )).fetchone()

                if estudio_existente:

                    error = (
                        "Ya existe un estudio con ese nombre."
                    )


            # ------------------------------------------------
            # VERIFICAR SLUG DUPLICADO
            # ------------------------------------------------

            if error is None:

                slug_existente = conexion.execute("""
                    SELECT id
                    FROM estudios
                    WHERE slug = ?
                """, (
                    slug,
                )).fetchone()

                if slug_existente:

                    error = (
                        "Ya existe un estudio con un "
                        "identificador similar."
                    )


            # ------------------------------------------------
            # CREAR ESTUDIO
            # ------------------------------------------------

            if error is None:

                cursor = conexion.execute("""
                    INSERT INTO estudios (
                        nombre,
                        slug,
                        descripcion,
                        preparacion,
                        requisitos,
                        duracion_minutos,
                        area_id,
                        activo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    nombre,
                    slug,
                    descripcion,
                    preparacion,
                    requisitos,
                    duracion,
                    area_id
                ))


                nuevo_estudio_id = cursor.lastrowid


                # --------------------------------------------
                # ASIGNAR SEDES
                # --------------------------------------------

                for sede_id in sedes_ids:

                    conexion.execute("""
                        INSERT INTO sede_estudios (
                            sede_id,
                            estudio_id
                        )
                        VALUES (?, ?)
                    """, (
                        sede_id,
                        nuevo_estudio_id
                    ))


                # --------------------------------------------
                # GUARDAR TODO
                # --------------------------------------------

                conexion.commit()


                return redirect(
                    url_for(
                        "admin_detalle_estudio",
                        estudio_id=nuevo_estudio_id,
                        mensaje=(
                            "Estudio creado correctamente."
                        )
                    )
                )


        # ----------------------------------------------------
        # MOSTRAR FORMULARIO
        # ----------------------------------------------------

        return render_template(
            "admin_nuevo_estudio.html",
            areas=areas,
            sedes=sedes,
            error=error
        )


    except Exception:

        conexion.rollback()
        raise


    finally:

        conexion.close()


# ============================================================
# ADMINISTRACIÓN - HORARIOS DE UN ESTUDIO
# ============================================================

@app.route(
    "/admin/estudios/<int:estudio_id>/horarios",
    methods=["GET", "POST"]
)
def admin_horarios_estudio(estudio_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))


    conexion = obtener_conexion()

    try:

        # ----------------------------------------------------
        # BUSCAR ESTUDIO
        # ----------------------------------------------------

        estudio = conexion.execute("""
            SELECT
                id,
                nombre,
                duracion_minutos,
                activo
            FROM estudios
            WHERE id = ?
        """, (
            estudio_id,
        )).fetchone()

        if estudio is None:
            return "Estudio no encontrado", 404


        # ----------------------------------------------------
        # OBTENER SEDES ACTIVAS DEL ESTUDIO
        # ----------------------------------------------------

        sedes = conexion.execute("""
            SELECT
                s.id,
                s.nombre,
                s.direccion
            FROM sedes s

            JOIN sede_estudios se
                ON se.sede_id = s.id

            WHERE se.estudio_id = ?

            ORDER BY s.nombre
        """, (
            estudio_id,
        )).fetchall()


        # ----------------------------------------------------
        # DÍAS DE LA SEMANA
        # ----------------------------------------------------

        dias = [
            (1, "Lunes"),
            (2, "Martes"),
            (3, "Miércoles"),
            (4, "Jueves"),
            (5, "Viernes"),
            (6, "Sábado"),
            (7, "Domingo")
        ]


        error = None


        # ----------------------------------------------------
        # PROCESAR FORMULARIO
        # ----------------------------------------------------

        
        if request.method == "POST":

            nuevos_horarios = []

            # Recorrer las sedes y los días configurados
            for sede in sedes:

                sede_id = sede["id"]

                for dia_numero, dia_nombre in dias:

                    campo_activo = f"activo_{sede_id}_{dia_numero}"
                    campo_inicio = f"inicio_{sede_id}_{dia_numero}"
                    campo_fin = f"fin_{sede_id}_{dia_numero}"

                    if campo_activo not in request.form:
                        continue

                    hora_inicio = request.form.get(
                        campo_inicio, ""
                    ).strip()

                    hora_fin = request.form.get(
                        campo_fin, ""
                    ).strip()

                    if not hora_inicio or not hora_fin:
                        error = (
                            f"Completá el horario de "
                            f"{dia_nombre} para {sede['nombre']}."
                        )
                        break

                    try:
                        inicio = datetime.strptime(
                            hora_inicio, "%H:%M"
                        )
                        fin = datetime.strptime(
                            hora_fin, "%H:%M"
                        )
                    except ValueError:
                        error = (
                            f"El horario de {dia_nombre} para "
                            f"{sede['nombre']} no es válido."
                        )
                        break

                    if inicio >= fin:
                        error = (
                            f"El horario de inicio debe ser "
                            f"anterior al de cierre en "
                            f"{dia_nombre} - {sede['nombre']}."
                        )
                        break

                    nuevos_horarios.append((
                        sede_id,
                        estudio_id,
                        dia_numero,
                        hora_inicio,
                        hora_fin,
                        1
                    ))

                if error:
                    break

            # Guardar una sola vez, después de validar todo
            if error is None:

                conexion.execute("""
                    DELETE FROM horarios
                    WHERE estudio_id = ?
                """, (estudio_id,))

                conexion.executemany("""
                    INSERT INTO horarios (
                        sede_id,
                        estudio_id,
                        dia_semana,
                        hora_inicio,
                        hora_fin,
                        activo
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, nuevos_horarios)

                conexion.commit()

                return redirect(
                    url_for(
                        "admin_horarios_estudio",
                        estudio_id=estudio_id,
                        mensaje="Horarios actualizados correctamente."
                    )
                )



        # ----------------------------------------------------
        # OBTENER HORARIOS ACTUALES
        # ----------------------------------------------------

        horarios_db = conexion.execute("""
            SELECT
                sede_id,
                dia_semana,
                hora_inicio,
                hora_fin,
                activo
            FROM horarios
            WHERE estudio_id = ?
            ORDER BY sede_id, dia_semana
        """, (
            estudio_id,
        )).fetchall()


        # ----------------------------------------------------
        # CONVERTIR HORARIOS EN DICCIONARIO
        # ----------------------------------------------------

        horarios = {}

        for horario in horarios_db:

            clave = (
                horario["sede_id"],
                horario["dia_semana"]
            )

            horarios[clave] = {
                "hora_inicio": horario["hora_inicio"],
                "hora_fin": horario["hora_fin"],
                "activo": horario["activo"]
            }


        mensaje = request.args.get("mensaje")


        # ----------------------------------------------------
        # MOSTRAR PÁGINA
        # ----------------------------------------------------

        return render_template(
            "admin_horarios_estudio.html",
            estudio=estudio,
            sedes=sedes,
            dias=dias,
            horarios=horarios,
            error=error,
            mensaje=mensaje
        )


    except Exception:

        conexion.rollback()
        raise


    finally:

        conexion.close()

# ============================================================
# ADMINISTRACIÓN - ACTIVAR / DESACTIVAR ESTUDIO
# ============================================================

@app.route(
    "/admin/estudios/<int:estudio_id>/estado",
    methods=["POST"]
)
def admin_cambiar_estado_estudio(estudio_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR ESTUDIO
    # --------------------------------------------------------

    estudio = conexion.execute("""
        SELECT
            id,
            nombre,
            activo
        FROM estudios
        WHERE id = ?
    """, (
        estudio_id,
    )).fetchone()

    if estudio is None:
        conexion.close()
        return "Estudio no encontrado", 404

    # --------------------------------------------------------
    # CAMBIAR ESTADO
    # --------------------------------------------------------

    nuevo_estado = 0 if estudio["activo"] else 1

    conexion.execute("""
        UPDATE estudios
        SET activo = ?
        WHERE id = ?
    """, (
        nuevo_estado,
        estudio_id
    ))

    conexion.commit()
    conexion.close()

    # --------------------------------------------------------
    # MENSAJE
    # --------------------------------------------------------

    if nuevo_estado == 1:
        mensaje = "Estudio activado correctamente."
    else:
        mensaje = "Estudio desactivado correctamente."

    return redirect(
        url_for(
            "admin_detalle_estudio",
            estudio_id=estudio_id,
            mensaje=mensaje
        )
    )

# ============================================================
# ADMINISTRACIÓN - LISTADO DE SEDES
# ============================================================

@app.route("/admin/sedes")
def admin_sedes():

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # OBTENER SEDES
    # --------------------------------------------------------

    sedes = conexion.execute("""
        SELECT
            s.id,
            s.nombre,
            s.direccion,
            s.telefono,
            s.activo,

            COUNT(
                DISTINCT CASE
                    WHEN se.activo = 1 THEN se.estudio_id
                END
            ) AS cantidad_estudios

        FROM sedes s

        LEFT JOIN sede_estudios se
            ON se.sede_id = s.id

        GROUP BY
            s.id,
            s.nombre,
            s.direccion,
            s.telefono,
            s.activo

        ORDER BY
            s.nombre
    """).fetchall()

    conexion.close()

    return render_template(
        "admin_sedes.html",
        sedes=sedes
    )


# ============================================================
# ADMINISTRACIÓN - DETALLE DE SEDE
# ============================================================

@app.route("/admin/sedes/<int:sede_id>")
def admin_detalle_sede(sede_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR SEDE
    # --------------------------------------------------------

    sede = conexion.execute("""
        SELECT
            id,
            nombre,
            direccion,
            telefono,
            activo
        FROM sedes
        WHERE id = ?
    """, (
        sede_id,
    )).fetchone()

    if sede is None:
        conexion.close()
        return "Sede no encontrada", 404

    # --------------------------------------------------------
    # ESTUDIOS ASOCIADOS A LA SEDE
    # --------------------------------------------------------

    estudios = conexion.execute("""
        SELECT
            e.id,
            e.nombre,
            e.slug,
            e.duracion_minutos,
            e.activo AS estudio_activo,
            se.activo AS disponible_sede,
            a.nombre AS area
        FROM sede_estudios se

        JOIN estudios e
            ON e.id = se.estudio_id

        JOIN areas a
            ON a.id = e.area_id

        WHERE se.sede_id = ?

        ORDER BY
            a.nombre,
            e.nombre
    """, (
        sede_id,
    )).fetchall()

    conexion.close()

    return render_template(
        "admin_detalle_sede.html",
        sede=sede,
        estudios=estudios
    )

# ============================================================
# ADMINISTRACIÓN - ACTIVAR / DESACTIVAR SEDE
# ============================================================

@app.route(
    "/admin/sedes/<int:sede_id>/estado",
    methods=["POST"]
)
def admin_cambiar_estado_sede(sede_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR SEDE
    # --------------------------------------------------------

    sede = conexion.execute("""
        SELECT
            id,
            nombre,
            activo
        FROM sedes
        WHERE id = ?
    """, (
        sede_id,
    )).fetchone()

    if sede is None:
        conexion.close()
        return "Sede no encontrada", 404

    # --------------------------------------------------------
    # CAMBIAR ESTADO
    # --------------------------------------------------------

    nuevo_estado = 0 if sede["activo"] else 1

    conexion.execute("""
        UPDATE sedes
        SET activo = ?
        WHERE id = ?
    """, (
        nuevo_estado,
        sede_id
    ))

    conexion.commit()
    conexion.close()

    # --------------------------------------------------------
    # MENSAJE
    # --------------------------------------------------------

    if nuevo_estado == 1:
        mensaje = "Sede activada correctamente."
    else:
        mensaje = "Sede desactivada correctamente."

    return redirect(
        url_for(
            "admin_detalle_sede",
            sede_id=sede_id,
            mensaje=mensaje
        )
    )


# ============================================================
# ADMINISTRACIÓN - EDITAR SEDE
# ============================================================

@app.route(
    "/admin/sedes/<int:sede_id>/editar",
    methods=["GET", "POST"]
)
def admin_editar_sede(sede_id):

    # --------------------------------------------------------
    # VERIFICAR SESIÓN Y ROL
    # --------------------------------------------------------

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return redirect(url_for("inicio"))

    conexion = obtener_conexion()

    # --------------------------------------------------------
    # BUSCAR SEDE
    # --------------------------------------------------------

    sede = conexion.execute("""
        SELECT
            id,
            nombre,
            direccion,
            telefono,
            activo
        FROM sedes
        WHERE id = ?
    """, (
        sede_id,
    )).fetchone()

    if sede is None:
        conexion.close()
        return "Sede no encontrada", 404

    error = None

    # --------------------------------------------------------
    # ACTUALIZAR SEDE
    # --------------------------------------------------------

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        direccion = request.form.get("direccion", "").strip()
        telefono = request.form.get("telefono", "").strip()

        if not nombre:
            error = "El nombre de la sede es obligatorio."

        elif not direccion:
            error = "La dirección es obligatoria."

        elif not telefono:
            error = "El teléfono es obligatorio."

        else:

            conexion.execute("""
                UPDATE sedes
                SET
                    nombre = ?,
                    direccion = ?,
                    telefono = ?
                WHERE id = ?
            """, (
                nombre,
                direccion,
                telefono,
                sede_id
            ))

            conexion.commit()
            conexion.close()

            return redirect(
                url_for(
                    "admin_detalle_sede",
                    sede_id=sede_id,
                    mensaje="Datos de la sede actualizados correctamente."
                )
            )

    conexion.close()

    return render_template(
        "admin_editar_sede.html",
        sede=sede,
        error=error
    )



# ============================================================
# INICIO DE FLASK
# ============================================================

if __name__ == "__main__":
    app.run(debug=False)
