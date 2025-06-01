from flask import Blueprint, request, jsonify
import cv2
import base64
from flask_socketio import SocketIO
import threading
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from conexiondb import conectar_db
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity , get_jwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear un Blueprint
rutas_camaras = Blueprint('rutas_camaras', __name__)

# Diccionario para manejar hilos de cámaras
hilos_camaras = {}

# Scheduler para verificaciones periódicas
scheduler = BackgroundScheduler()

# Inicializar SocketIO
socketio = None


# Función para obtener datos del usuario actual
def obtener_usuario_actual():
    current_user = get_jwt_identity()
    claims = get_jwt()
    user_data = {}

    if isinstance(current_user, dict):
        user_data['id'] = current_user.get('id')
        user_data['rol'] = current_user.get('rol')
    else:
        user_data['id'] = current_user
        user_data['rol'] = claims.get('rol')
    
    return user_data

# Función para obtener cámaras según el rol
def obtener_camaras_por_rol(cursor, user_id, rol):
    if rol == 'admin':
        cursor.execute("SELECT * FROM camaras")
    else:
        cursor.execute("""
            SELECT c.* 
            FROM camaras c
            INNER JOIN usuario_camara uc ON c.id = uc.camara_id
            WHERE uc.usuario_id = %s
        """, (user_id,))
    return cursor.fetchall()

# Ruta para verificar cámaras
@rutas_camaras.route('/obtener', methods=['GET'])
@jwt_required()
def obtener_camaras():
    try:
        user_data = obtener_usuario_actual()
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)
        # Obtener cámaras según el rol
        camaras = obtener_camaras_por_rol(cursor, user_data['id'], user_data['rol'])
        cursor.close()
        conexion.close()

        return jsonify(camaras), 200
    except Exception as e:
        logger.error(f"Error al obtener cámaras: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las cámaras. Intente nuevamente más tarde.'}), 500


@rutas_camaras.route('/registrar', methods=['POST'])
@jwt_required()
def registrar_camara():
    try:
        current_user = get_jwt_identity()
        datos_camara = request.json
        
        if not current_user:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        conexion = conectar_db()
        cursor = conexion.cursor()

        # Insertar la nueva cámara en la tabla `camaras`
        query_camara = """
        INSERT INTO camaras (nombre, local, ubicacion, tipo_camara, fuente, estado, fecha_registro) 
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        valores_camara = (
            datos_camara.get('nombre'),
            datos_camara.get('local'),
            datos_camara.get('ubicacion'),
            datos_camara.get('tipo_camara'),
            datos_camara.get('fuente'),
            'Inactivo'  # Estado inicial hasta verificar
        )
        cursor.execute(query_camara, valores_camara)
        nueva_camara_id = cursor.lastrowid

        # Asociar la cámara con el usuario en la tabla `usuario_camara`
        query_usuario_camara = """
        INSERT INTO usuario_camara (usuario_id, camara_id, fecha_asignacion) 
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        """
        valores_usuario_camara = (current_user, nueva_camara_id)
        cursor.execute(query_usuario_camara, valores_usuario_camara)

        # Confirmar transacciones
        conexion.commit()
        conexion.close()

        logger.info(f"Nueva cámara registrada con ID: {nueva_camara_id} y asignada al usuario: {current_user}")
        return jsonify({'id_camara': nueva_camara_id}), 201
    except Exception as e:
        logger.error(f"Error al registrar nueva cámara: {str(e)}")
        return jsonify({'error': 'Error interno al registrar la cámara'}), 500



# ---- editar camara -------

@rutas_camaras.route('/editar/<int:camara_id>', methods=['PUT'])
@jwt_required()
def editar_camara(camara_id):
    try:
        user_data = obtener_usuario_actual()
        datos_camara = request.json
        
        if not camara_id:
            return jsonify({'error': 'ID de cámara no proporcionado'}), 400
        
        conexion = conectar_db()
        cursor = conexion.cursor()
        
        # Validar si el usuario tiene acceso a la cámara (si no es admin)
        if user_data['rol'] != 'admin':
            query_verificar_acceso = """
            SELECT 1 
            FROM usuario_camara 
            WHERE usuario_id = %s AND camara_id = %s
            """
            cursor.execute(query_verificar_acceso, (user_data['id'], camara_id))
            if not cursor.fetchone():
                return jsonify({'error': 'No tienes permiso para editar esta cámara'}), 403
        
        # Actualizar datos de la cámara
        query_actualizar = """
        UPDATE camaras
        SET nombre = %s, local = %s, ubicacion = %s, tipo_camara = %s, fuente = %s, estado = %s, fecha_modificacion = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        valores_actualizar = (
            datos_camara.get('nombre'),
            datos_camara.get('local'),
            datos_camara.get('ubicacion'),
            datos_camara.get('tipo_camara'),
            datos_camara.get('fuente'),
            datos_camara.get('estado'),
            camara_id
        )
        cursor.execute(query_actualizar, valores_actualizar)
        conexion.commit()
        conexion.close()

        logger.info(f"Cámara ID {camara_id} actualizada por el usuario ID {user_data['id']}")
        return jsonify({'mensaje': 'Cámara actualizada exitosamente'}), 200
    except Exception as e:
        logger.error(f"Error al editar cámara ID {camara_id}: {str(e)}")
        return jsonify({'error': 'Error interno al editar la cámara'}), 500





# Función para verificar el estado de las cámaras
def verificar_camaras():
    try:
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)
        
        # Obtener todas las cámaras excepto las desactivadas por usuario
        cursor.execute("""
            SELECT * FROM camaras 
            WHERE estado != 'Desactivado por Usuario'
        """)
        camaras = cursor.fetchall()
        cursor.close()
        conexion.close()

        for camara in camaras:
            try:
                # Verificar si la cámara está accesible
                if camara['tipo_camara'] == 'USB':
                    cap = cv2.VideoCapture(int(camara['fuente']))
                else:
                    cap = cv2.VideoCapture(camara['fuente'])

                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        actualizar_estado_db(camara['id'], 'Activo')
                        cap.release()
                        continue

                actualizar_estado_db(camara['id'], 'Inactivo')
                cap.release()
            except Exception as e:
                logger.error(f"Error al verificar cámara {camara['id']}: {str(e)}")
                actualizar_estado_db(camara['id'], 'Inactivo')

    except Exception as e:
        logger.error(f"Error en verificación de cámaras: {str(e)}")

# Función para actualizar el estado de una cámara en la base de datos
def actualizar_estado_db(id_camara, estado):
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE camaras SET estado = %s, fecha_registro = CURRENT_TIMESTAMP WHERE id = %s", 
            (estado, id_camara)
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        logger.info(f"Estado de cámara {id_camara} actualizado a {estado}")
    except Exception as e:
        logger.error(f"Error al actualizar estado de cámara en DB: {str(e)}")

# Función para detener una cámara específica
def detener_camara(id_camara):
    if id_camara in hilos_camaras:
        hilos_camaras[id_camara]['activo'] = False
        if 'thread' in hilos_camaras[id_camara]:
            hilos_camaras[id_camara]['thread'].join(timeout=1)
        del hilos_camaras[id_camara]
        logger.info(f"Cámara {id_camara} detenida")



# Ruta para actualizar el estado de una cámara
@rutas_camaras.route('/actualizar_estado_camara', methods=['POST'])
@jwt_required()
def actualizar_estado_camara():
    try:
        data = request.json
        id_camara = data.get('id_camara')
        estado = data.get('estado')
        current_user = get_jwt_identity()

        if not id_camara or estado not in ['Activo', 'Inactivo', 'Desactivado por Usuario']:
            return jsonify({'error': 'Datos inválidos'}), 400

        conexion = conectar_db()
        cursor = conexion.cursor()

        # Verificar permisos
        if current_user.get('rol') != 'admin':
            cursor.execute("""
                SELECT COUNT(*) FROM usuario_camara 
                WHERE usuario_id = %s AND camara_id = %s
            """, (current_user.get('id'), id_camara))
            if cursor.fetchone()[0] == 0:
                cursor.close()
                conexion.close()
                return jsonify({'error': 'No tiene permisos para esta cámara'}), 403

        cursor.execute(
            "UPDATE camaras SET estado = %s, fecha_registro = CURRENT_TIMESTAMP WHERE id = %s", 
            (estado, id_camara)
        )
        conexion.commit()
        cursor.close()
        conexion.close()

        # Si la cámara se marca como desactivada por usuario, detener su monitoreo
        if estado == 'Desactivado por Usuario':
            detener_camara(id_camara)

        logger.info(f"Estado de cámara {id_camara} actualizado a {estado}")
        return jsonify({'message': 'Estado actualizado'}), 200
    except Exception as e:
        logger.error(f"Error al actualizar estado de cámara: {str(e)}")
        return jsonify({'error': str(e)}), 500



# Ruta para iniciar monitoreo
@rutas_camaras.route('/iniciar_monitoreo', methods=['POST'])
@jwt_required()
def iniciar_monitoreo():
    try:
        if not scheduler.running:
            scheduler.add_job(verificar_camaras, 'interval', minutes=10)
            scheduler.start()
            logger.info("Monitoreo periódico de cámaras iniciado")
            verificar_camaras()
        return jsonify({'message': 'Monitoreo iniciado'}), 200
    except Exception as e:
        logger.error(f"Error al iniciar monitoreo: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Ruta para detener monitoreo
@rutas_camaras.route('/detener_monitoreo', methods=['POST'])
@jwt_required()
def detener_monitoreo():
    try:
        if scheduler.running:
            scheduler.shutdown()
        for id_camara in list(hilos_camaras.keys()):
            detener_camara(id_camara)
        logger.info("Monitoreo de cámaras detenido")
        return jsonify({'message': 'Monitoreo detenido'}), 200
    except Exception as e:
        logger.error(f"Error al detener monitoreo: {str(e)}")
        return jsonify({'error': str(e)}), 500


def iniciar_camara(camara):
    id_camara = camara['id']
    tipo = camara['tipo_camara']
    fuente = camara['fuente']
    
    # No iniciar si está desactivada por usuario
    if camara['estado'] == 'Desactivado por Usuario':
        logger.info(f"Cámara {id_camara} está desactivada por usuario, no se iniciará")
        return
    
    if id_camara in hilos_camaras:
        logger.info(f"La cámara {id_camara} ya está iniciada")
        return
    
    try:
        # Definir la fuente de video
        if tipo == 'USB':
            cap = cv2.VideoCapture(int(fuente))
        elif tipo == 'IP' or tipo == 'WEB':
            cap = cv2.VideoCapture(fuente)
        else:
            logger.error(f"Tipo de cámara no soportado: {tipo}")
            actualizar_estado_db(id_camara, 'Inactivo')
            return
        
        if not cap.isOpened():
            logger.error(f"Error al abrir la cámara {id_camara}: {fuente}")
            actualizar_estado_db(id_camara, 'Inactivo')
            return
        
        logger.info(f"Cámara {id_camara} iniciada correctamente")
        actualizar_estado_db(id_camara, 'Activo')
        
        # Registramos la cámara como activa
        hilos_camaras[id_camara] = {'activo': True}
        
        # Iniciamos el bucle de transmisión en un hilo separado
        def stream_video():
            try:
                while hilos_camaras.get(id_camara, {}).get('activo', False):
                    ret, frame = cap.read()
                    if not ret:
                        logger.error(f"Cámara {id_camara} dejó de responder")
                        break
                    
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    if socketio:
                        socketio.emit(f'video_frame_{id_camara}', {'frame': frame_base64})
                        socketio.sleep(0.03)
                    else:
                        logger.error(f"SocketIO no inicializado para cámara {id_camara}")
                        break
                
                cap.release()
                logger.info(f"Stream de cámara {id_camara} finalizado")
                actualizar_estado_db(id_camara, 'Inactivo')
                if id_camara in hilos_camaras:
                    del hilos_camaras[id_camara]
            except Exception as e:
                logger.error(f"Error en el hilo de la cámara {id_camara}: {str(e)}")
                actualizar_estado_db(id_camara, 'Inactivo')
                if id_camara in hilos_camaras:
                    del hilos_camaras[id_camara]
                
        # Iniciamos el hilo para esta cámara
        stream_thread = threading.Thread(target=stream_video, daemon=True)
        stream_thread.start()
        hilos_camaras[id_camara]['thread'] = stream_thread
        
    except Exception as e:
        logger.error(f"Error al iniciar cámara {id_camara}: {str(e)}")
        actualizar_estado_db(id_camara, 'Inactivo')
        if id_camara in hilos_camaras:
            del hilos_camaras[id_camara]


# Función para inicializar SocketIO
def set_socketio(socketio_instance):
    """Establece la instancia de SocketIO"""
    global socketio
    socketio = socketio_instance
