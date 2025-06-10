import mysql.connector
import faiss
import numpy as np
import pickle
import os
import threading

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
faiss_index = faiss.IndexIDMap2(faiss.IndexFlatL2(d)) 
faiss_lock = threading.Lock()  

def cargar_todos_embeddings_faiss():
    conexion = conectar_db()
    if not conexion:
        print("Error de conexión a la base de datos")
        return
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT persona_id, embedding FROM embeddings_personas")
        
        ids = []
        embeddings = []
        
        for persona_id, embedding in cursor:
            emb = np.array(pickle.loads(embedding), dtype=np.float32)
            ids.append(persona_id)
            embeddings.append(emb)
        
        with faiss_lock:
            faiss_index.reset()
            
            if embeddings:
                faiss_index.add_with_ids(np.vstack(embeddings), np.array(ids))
        
    except Exception as e:
        print(f"Error al cargar embeddings en FAISS: {e}")
        raise
    finally:
        conexion.close()

def agregar_embedding_faiss(persona_id, embedding):
    emb = np.array(embedding, dtype=np.float32) 
    with faiss_lock:
        faiss_index.add_with_ids(emb.reshape(1, -1), np.array([persona_id]))
        


def eliminar_embeddings_faiss(persona_id):
    with faiss_lock:
        try:
            id_array = np.array([persona_id], dtype=np.int64)
            
            if faiss_index.id_map:
                faiss_index.remove_ids(id_array)
            else:
                print(f"No se encontraron embeddings para persona_id {persona_id}")
        except Exception as e:
            print(f"Error al eliminar embeddings de FAISS: {e}")
            raise