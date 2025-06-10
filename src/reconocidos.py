from flask import Flask, Blueprint, jsonify, request, send_from_directory, current_app
from conexiondb import conectar_db
import os
from datetime import datetime
import uuid
import cv2
from collections import defaultdict


# Configuración
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imagenes_detectados")
rutas_detectados = Blueprint('rutas_detectados', __name__)

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
            
# --------------------------
# MOSTTRAAAAAAAAAAAAAAAAA
# --------------------------         
@rutas_detectados.route('/registros', methods=['GET'])
def get_detections():
    try:
        conn = conectar_db()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            d.id, d.fecha_hora, d.foto_captura, d.persona_id, d.camara_id,
            p.dni as persona_dni, p.nombres as persona_nombres, 
            p.apellidos as persona_apellidos, p.fecha_nacimiento as persona_fecha_nacimiento,
            p.genero as persona_genero, p.descripcion as persona_descripcion,
            c.nombre as camara_nombre, c.local as camara_local, 
            c.ubicacion as camara_ubicacion, c.tipo_camara as camara_tipo,
            c.estado as camara_estado
        FROM detectados d
        LEFT JOIN personas p ON d.persona_id = p.id
        LEFT JOIN camaras c ON d.camara_id = c.id
        ORDER BY d.fecha_hora DESC
        """
        
        cursor.execute(query)
        detections = cursor.fetchall()
        
        structured_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for det in detections:
            fecha = det['fecha_hora'] if isinstance(det['fecha_hora'], datetime) else datetime.strptime(det['fecha_hora'], '%Y-%m-%d %H:%M:%S')
            year = str(fecha.year)
            month = f"{fecha.month:02d}"
            day = f"{fecha.day:02d}"
            
            structured_data[year][month][day].append(det)
        
        return jsonify(structured_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

@rutas_detectados.route('/images/<path:filename>', methods=['GET'])
def serve_image(filename):
    try:
        return send_from_directory(IMAGES_DIR, filename)
    except FileNotFoundError:
        return jsonify({'error': 'Imagen no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
