from conexiondb import conectar_db
import os
from datetime import datetime
import uuid
import cv2

# Configuración de directorios
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imagenes_detectados")

def guardarReconocido(frame, persona_id, camara_id):
    try:
        # 1. Verificar si hay registros recientes
        conexion = conectar_db()
        cursor = conexion.cursor()
        
        query_verificacion = """
        SELECT COUNT(*) as total 
        FROM detectados 
        WHERE persona_id = %s 
        AND camara_id = %s 
        AND fecha_hora >= NOW() - INTERVAL 5 MINUTE
        """
        cursor.execute(query_verificacion, (persona_id, camara_id))
        resultado = cursor.fetchone()
        
        if resultado[0] > 0:
            print(f"Persona {persona_id} ya registrada en cámara {camara_id} en los últimos 5 minutos")
            conexion.close()
            return None
            
        # 2. Si no hay registros recientes, proceder con el guardado
        now = datetime.now()
        date_path = os.path.join(
            now.strftime("%Y"),
            now.strftime("%m"), 
            now.strftime("%d")
        )
        full_dir = os.path.join(IMAGES_DIR, date_path)
        os.makedirs(full_dir, exist_ok=True)
        
        filename = f"det_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
        full_path = os.path.join(full_dir, filename)
        rel_path = os.path.join(date_path, filename)
        
        cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        # 3. Insertar nuevo registro
        query_insert = """
        INSERT INTO detectados 
        (persona_id, camara_id, foto_captura)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query_insert, (persona_id, camara_id, rel_path))
        conexion.commit()
        
        print(f"Registro exitoso: Persona {persona_id} en cámara {camara_id}")
        return rel_path
        
    except Exception as e:
        print(f"Error en guardarReconocido: {str(e)}")
        return None
    finally:
        if 'conexion' in locals():
            conexion.close()