import psycopg2
import os

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS LOCAL
# ==========================================
DB_HOST = "localhost"
DB_NAME = "parqueadero_db" 
DB_USER = "postgres"       
DB_PASS = "nuenama159"  

def inicializar_base_de_datos():
    try:
        # Detecta automáticamente si está en la nube o usa tu PC
        url_nube = os.environ.get("DATABASE_URL")
        if url_nube:
            conn = psycopg2.connect(url_nube)
        else:
            conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
            
        cur = conn.cursor()

        print("Conectado. Creando las tablas...")

        # Limpiar tablas si ya existían para evitar errores
        cur.execute("DROP TABLE IF EXISTS movimientos CASCADE;")
        cur.execute("DROP TABLE IF EXISTS vehiculos CASCADE;")
        cur.execute("DROP TABLE IF EXISTS celdas CASCADE;")

        # Crear tabla: Celdas
        cur.execute("""
            CREATE TABLE celdas (
                id_celda SERIAL PRIMARY KEY,
                codigo_celda VARCHAR(10) UNIQUE NOT NULL,
                estado VARCHAR(15) DEFAULT 'libre'
            );
        """)

        # Crear tabla: Vehículos
        cur.execute("""
            CREATE TABLE vehiculos (
                matricula VARCHAR(10) PRIMARY KEY,
                marca VARCHAR(50),
                color VARCHAR(30)
            );
        """)

        # Crear tabla: Movimientos
        cur.execute("""
            CREATE TABLE movimientos (
                id_movimiento SERIAL PRIMARY KEY,
                matricula VARCHAR(10) REFERENCES vehiculos(matricula),
                id_celda INT REFERENCES celdas(id_celda),
                fecha_hora_recepcion TIMESTAMP NOT NULL,
                fecha_hora_entrega TIMESTAMP NOT NULL,
                estado_movimiento VARCHAR(20) DEFAULT 'en_parqueadero'
            );
        """)

        # Crear 20 celdas de prueba (A-01 a A-10 y B-01 a B-10)
        for i in range(1, 11):
            cur.execute("INSERT INTO celdas (codigo_celda) VALUES (%s);", (f"A-{i:02d}",))
            cur.execute("INSERT INTO celdas (codigo_celda) VALUES (%s);", (f"B-{i:02d}",))

        # Guardar todos los cambios
        conn.commit()
        print("¡Éxito! Las tablas y las celdas se crearon correctamente.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    inicializar_base_de_datos()