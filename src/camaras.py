from flask import Blueprint, request, jsonify
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from conexiondb import conectar_db
from flask_jwt_extended import jwt_required, get_jwt_identity , get_jwt
from multicamara import cerrarhiloCamara , verificar_y_lanzar_camaras
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
        cursor.execute("SELECT * FROM camaras where fecha_eliminacion IS NULL")
    else:
        cursor.execute("""
            SELECT c.* 
            FROM camaras c
            INNER JOIN usuario_camara uc ON c.id = uc.camara_id
            WHERE uc.usuario_id = %s AND c.fecha_eliminacion IS NULL
        """, (user_id,))
    return cursor.fetchall()



#ruta de camaras por user
def obtener_camaras_por_usuario(cursor, user_id, rol):
    if rol == 'admin':
        cursor.execute("""
            SELECT c.id AS camara_id, c.nombre AS camara_nombre, c.estado AS camara_estado,
                   u.id AS usuario_id, u.username AS usuario_nombre
            FROM camaras c
            LEFT JOIN usuario_camara uc ON c.id = uc.camara_id
            LEFT JOIN usuarios u ON uc.usuario_id = u.id
            WHERE c.estado = 'Activo'
        """)
        camaras = cursor.fetchall()

        # Organizar las cámaras y los usuarios en un formato agrupado
        resultado = {}
        for camara in camaras:
            camara_id = camara['camara_id']
            if camara_id not in resultado:
                resultado[camara_id] = {
                    "id": camara_id,
                    "nombre": camara['camara_nombre'],
                    "estado": camara['camara_estado'],
                    "usuarios": []
                }
            if camara['usuario_id']:
                resultado[camara_id]["usuarios"].append({
                    "usuario_id": camara['usuario_id'],
                    "usuario_nombre": camara['usuario_nombre']
                })
        return list(resultado.values())
    else:
        cursor.execute("""
            SELECT c.id AS camara_id, c.nombre AS camara_nombre, c.estado AS camara_estado
            FROM camaras c
            INNER JOIN usuario_camara uc ON c.id = uc.camara_id
            WHERE uc.usuario_id = %s AND c.estado = 'Activo'
        """, (user_id,))
        return cursor.fetchall()



@rutas_camaras.route('/obtener_activas', methods=['GET'])
@jwt_required()
def obtener_camaras_Activas():
    try:
        user_data = obtener_usuario_actual() 
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)

        # Obtener cámaras según el rol
        camaras = obtener_camaras_por_usuario(cursor, user_data['id'], user_data['rol'])
        cursor.close()
        conexion.close()

        return jsonify(camaras), 200
    except Exception as e:
        logger.error(f"Error al obtener cámaras: {str(e)}")
        return jsonify({'error': 'Ocurrió un error al obtener las cámaras. Intente nuevamente más tarde.'}), 500




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
        verificar_y_lanzar_camaras()
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
        if not cerrarhiloCamara(camara_id):
            return False
        # Actualizar datos de la cámara
        query_actualizar = """
        UPDATE camaras
        SET nombre = %s, local = %s, ubicacion = %s, tipo_camara = %s, fuente = %s, estado = %s
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
        verificar_y_lanzar_camaras()
        logger.info(f"Cámara ID {camara_id} actualizada por el usuario ID {user_data['id']}")
        return jsonify({'mensaje': 'Cámara actualizada exitosamente'}), 200
    except Exception as e:
        logger.error(f"Error al editar cámara ID {camara_id}: {str(e)}")
        return jsonify({'error': 'Error interno al editar la cámara'}), 500


@rutas_camaras.route('/eliminar/<int:camara_id>', methods=['DELETE'])
@jwt_required()
def eliminar_camara(camara_id):
    try:
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("SELECT estado FROM camaras WHERE id = %s", (camara_id,))
        estado = cursor.fetchone()

        
        if not cerrarhiloCamara(camara_id):
            return jsonify({'error': 'No se pudo cerrar el hilo de la cámara'}), 400
        cursor.execute(
            """
            UPDATE camaras 
            SET estado = 'Desactivado', 
                fecha_eliminacion = NOW() 
            WHERE id = %s
            """, 
            (camara_id,)
        )

        conexion.commit()
        conexion.close()
        return jsonify({'mensaje': 'Cámara desactivada exitosamente'}), 200

    except Exception as e:
        logger.error(f"Error al desactivar cámara ID {camara_id}: {str(e)}")
        return jsonify({'error': 'Error interno al desactivar la cámara'}), 500


