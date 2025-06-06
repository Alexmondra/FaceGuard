import mysql.connector
import faiss
import numpy as np
import pickle
import os

def crear_tablas_si_no_existen(conexion):
    try:
        # Ruta al archivo SQL
        ruta_sql = os.path.join(os.path.dirname(__file__), '../models/tablas.sql')
        with open(ruta_sql, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Dividir sentencias de manera más robusta
        sentencias = sql_script.split(';')
        cursor = conexion.cursor()

        for sentencia in sentencias:
            sentencia = sentencia.strip()
            if sentencia:
                try:
                    cursor.execute(sentencia)
                except Exception as e:
                    print(f"Error ejecutando sentencia: {sentencia[:50]}... Error: {e}")
        
        conexion.commit()
        print("Verificación/creación de tablas completada.")
    except Exception as e:
        print(f"Error al crear/verificar tablas: {e}")

def poner_camaras_inactivas():
    conn = conectar_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE camaras SET estado = 'Inactivo'")
        conn.commit()
        print("Todas las cámaras fueron marcadas como 'Inactivo'.")
    except Exception as e:
        print(f"Error actualizando estado de cámaras: {str(e)}")
    finally:
        conn.close()

def conectar_db():
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='tesis2',
            port=3306
        )
        if conexion.is_connected():
            print("Conexión exitosa a la base de datos")
        return conexion
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None


d = 512
faiss_index = faiss.IndexFlatL2(d)
indice_persona_id = {}

def cargar_embeddings_faiss():
    conexion = conectar_db()
    if not conexion:
        print("No se pudo establecer conexión con la base de datos. No se cargaron los embeddings.")
        return

    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT persona_id, embedding FROM embeddings_personas")
        for persona_id, embedding in cursor.fetchall():
            faiss_index.add(np.array(pickle.loads(embedding), dtype=np.float32).reshape(1, -1))
            indice_persona_id[faiss_index.ntotal - 1] = persona_id
        print("Embeddings cargados en FAISS exitosamente")
    except Exception as e:
        print(f"Error al cargar embeddings en FAISS: {e}")
    finally:
        conexion.close()
