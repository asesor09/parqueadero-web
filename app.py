from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import psycopg2.extras
from datetime import date
import os

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS FLEXIBLE
# ==========================================
def get_db_connection():
    # 1. Prioridad: DATABASE_URL (si está configurada en Render)
    url_nube = os.environ.get("DATABASE_URL")
    if url_nube:
        return psycopg2.connect(url_nube)
    
    # 2. Segunda opción: Variables individuales de Render (DB_HOST, DB_NAME, etc.)
    host_nube = os.environ.get("DB_HOST")
    if host_nube:
        return psycopg2.connect(
            host=host_nube,
            database=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASS")
        )
    
    # 3. Tercera opción: Desarrollo local en tu PC
    return psycopg2.connect(
        host="localhost",
        database="parqueadero_db",
        user="postgres",
        password="nuenama159"
    )

# ==========================================
# RUTA 1: MAPA VISUAL DEL PARQUEADERO
# ==========================================
@app.route('/')
def mapa_parqueadero():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = """
        SELECT c.id_celda, c.codigo_celda, c.estado, m.matricula 
        FROM celdas c
        LEFT JOIN movimientos m ON c.id_celda = m.id_celda AND m.estado_movimiento = 'en_parqueadero'
        ORDER BY c.codigo_celda ASC;
    """
    cur.execute(query)
    celdas = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('mapa.html', celdas=celdas)

# ==========================================
# RUTA 2: REGISTRO E INGRESO DE VEHÍCULO
# ==========================================
@app.route('/registro', methods=['GET', 'POST'])
def registrar_vehiculo():
    conn = get_db_connection()
    
    if request.method == 'POST':
        matricula = request.form['matricula'].upper()
        marca = request.form.get('marca', '')
        color = request.form.get('color', '')
        id_celda = request.form['id_celda']
        fecha_recepcion = request.form['fecha_recepcion']
        fecha_entrega = request.form['fecha_entrega']
        
        cur = conn.cursor()
        try:
            # Upsert del vehículo
            cur.execute("""
                INSERT INTO vehiculos (matricula, marca, color) VALUES (%s, %s, %s)
                ON CONFLICT (matricula) DO UPDATE SET marca = EXCLUDED.marca, color = EXCLUDED.color;
            """, (matricula, marca, color))
            
            # Registrar movimiento
            cur.execute("""
                INSERT INTO movimientos (matricula, id_celda, fecha_hora_recepcion, fecha_hora_entrega)
                VALUES (%s, %s, %s, %s);
            """, (matricula, id_celda, fecha_recepcion, fecha_entrega))
            
            # Ocupar celda
            cur.execute("UPDATE celdas SET estado = 'ocupada' WHERE id_celda = %s;", (id_celda,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('mapa_parqueadero'))
    
    # GET: Cargar celdas libres
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id_celda, codigo_celda FROM celdas WHERE estado = 'libre' ORDER BY codigo_celda ASC;")
    celdas_libres = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('registro.html', celdas_libres=celdas_libres)

# ==========================================
# RUTA 3: PANEL DE ENTREGAS PENDIENTES
# ==========================================
@app.route('/entregas-pendientes')
def listado_entregas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = """
        SELECT m.id_movimiento, m.matricula, v.marca, c.codigo_celda, m.fecha_hora_entrega
        FROM movimientos m
        JOIN vehiculos v ON m.matricula = v.matricula
        JOIN celdas c ON m.id_celda = c.id_celda
        WHERE DATE(m.fecha_hora_entrega) = CURRENT_DATE
        AND m.estado_movimiento = 'en_parqueadero'
        ORDER BY m.fecha_hora_entrega ASC;
    """
    cur.execute(query)
    entregas = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('entregas.html', entregas=entregas)

# ==========================================
# RUTA 4: ACCIÓN - MARCAR COMO ENTREGADO
# ==========================================
@app.route('/marcar-entregado/<int:id_movimiento>', methods=['POST'])
def marcar_entregado(id_movimiento):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id_celda FROM movimientos WHERE id_movimiento = %s;", (id_movimiento,))
        resultado = cur.fetchone()
        
        if resultado:
            id_celda = resultado[0]
            cur.execute("UPDATE celdas SET estado = 'libre' WHERE id_celda = %s;", (id_celda,))
            cur.execute("UPDATE movimientos SET estado_movimiento = 'devuelto' WHERE id_movimiento = %s;", (id_movimiento,))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error al entregar: {e}")
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('listado_entregas'))

# ==========================================
# RUTA 5: API DE ALERTAS (PARA EL CELULAR)
# ==========================================
@app.route('/api/alertas')
def api_alertas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = """
        SELECT m.matricula, c.codigo_celda, m.fecha_hora_entrega
        FROM movimientos m
        JOIN celdas c ON m.id_celda = c.id_celda
        WHERE DATE(m.fecha_hora_entrega) = CURRENT_DATE
        AND m.estado_movimiento = 'en_parqueadero';
    """
    cur.execute(query)
    pendientes = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify({
        "hay_entregas": len(pendientes) > 0,
        "cantidad": len(pendientes),
        "vehiculos": pendientes
    })

# ==========================================
# RUTA SECRETA PARA INSTALAR LA BASE DE DATOS
# ==========================================
@app.route('/instalar')
def instalar_base_datos():
    try:
        from init_db import inicializar_base_de_datos
        inicializar_base_de_datos()
        return "<h1>¡Éxito! Base de datos instalada.</h1><br><a href='/'>Ir al mapa del parqueadero</a>"
    except Exception as e:
        return f"<h1>Error al instalar:</h1><p>{e}</p>"

# ==========================================
# INICIALIZACIÓN AUTOMÁTICA AL ARRANCAR
# ==========================================
with app.app_context():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Crear tablas solo si no existen (seguro para producción)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS celdas (
                id_celda SERIAL PRIMARY KEY,
                codigo_celda VARCHAR(10) UNIQUE NOT NULL,
                estado VARCHAR(15) DEFAULT 'libre'
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vehiculos (
                matricula VARCHAR(10) PRIMARY KEY,
                marca VARCHAR(50),
                color VARCHAR(30)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id_movimiento SERIAL PRIMARY KEY,
                matricula VARCHAR(10) REFERENCES vehiculos(matricula),
                id_celda INT REFERENCES celdas(id_celda),
                fecha_hora_recepcion TIMESTAMP NOT NULL,
                fecha_hora_entrega TIMESTAMP NOT NULL,
                estado_movimiento VARCHAR(20) DEFAULT 'en_parqueadero'
            );
        """)
        
        # Verificar si la tabla celdas está vacía para insertar las celdas iniciales
        cur.execute("SELECT COUNT(*) FROM celdas;")
        if cur.fetchone()[0] == 0:
            for i in range(1, 11):
                cur.execute("INSERT INTO celdas (codigo_celda) VALUES (%s) ON CONFLICT DO NOTHING;", (f"A-{i:02d}",))
                cur.execute("INSERT INTO celdas (codigo_celda) VALUES (%s) ON CONFLICT DO NOTHING;", (f"B-{i:02d}",))
        
        conn.commit()
        cur.close()
        conn.close()
        print("Base de datos verificada e inicializada correctamente.")
    except Exception as e:
        print(f"Nota en la inicialización automática: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
