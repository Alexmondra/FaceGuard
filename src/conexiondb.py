import mysql.connector
import faiss
import numpy as np
import pickle

def crear_tablas_si_no_existen(conexion):
    # Ejecuta el SQL solo si la conexión es válida
    try:
        with open('model/tablas.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        # Divide en sentencias por el ';' y ejecuta sólo las CREATE TABLE
        sentencias = [s.strip() for s in sql_script.split(';') if s.strip()]
        cursor = conexion.cursor()
        for sentencia in sentencias:
            if sentencia.upper().startswith("CREATE TABLE IF NOT EXISTS"):
                cursor.execute(sentencia)
        conexion.commit()
        print("Verificación/creación de tablas completada.")
    except Exception as e:
        print(f"Error al crear/verificar tablas: {e}")

def conectar_db():
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='tesis',
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
