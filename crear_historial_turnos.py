import sqlite3

# Conectar a la base de datos existente
conexion = sqlite3.connect("database/mediscan.db")

conexion.execute("PRAGMA foreign_keys = ON")

# Crear la tabla solamente si no existe
conexion.execute("""
    CREATE TABLE IF NOT EXISTS historial_turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        turno_id INTEGER NOT NULL,

        usuario_id INTEGER NOT NULL,

        estado_anterior TEXT,

        estado_nuevo TEXT NOT NULL,

        fecha_cambio DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (turno_id)
            REFERENCES turnos(id),

        FOREIGN KEY (usuario_id)
            REFERENCES usuarios(id)
    )
""")

conexion.commit()

# Verificar que exista
tabla = conexion.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name = 'historial_turnos'
""").fetchone()

if tabla:
    print("OK: tabla historial_turnos creada correctamente.")
else:
    print("ERROR: no se pudo verificar la tabla.")

conexion.close()