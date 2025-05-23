import cv2
import base64
from flask_socketio import SocketIO
import threading
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from conexiondb import conectar_db

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar SocketIO (referencia a la instancia de app.py)
socketio = None

# Obtener lista de cámaras activas
def obtener_camaras_activas():
    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM camaras")
    camaras = cursor.fetchall()
    conexion.close()
    return camaras

# Actualizar estado de la cámara
def actualizar_estado_camara(id_camara, estado):
    """Actualiza el estado de la cámara en la base de datos"""
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE camaras SET estado = %s, fecha_registro = CURRENT_TIMESTAMP WHERE id = %s", 
            (estado, id_camara)
        )
        conexion.commit()
        conexion.close()
        logger.info(f"Estado de cámara {id_camara} actualizado a {estado}")
    except Exception as e:
        logger.error(f"Error al actualizar estado de cámara {id_camara}: {str(e)}")

# Diccionario para manejar hilos de cámaras
hilos_camaras = {}

# Scheduler para verificaciones periódicas
scheduler = BackgroundScheduler()

def verificar_conexion_camara(camara):
    """Verifica la conexión de una cámara específica y actualiza su estado"""
    try:
        tipo = camara['tipo_camara']
        fuente = camara['fuente']
        
        if tipo == 'USB':
            cap = cv2.VideoCapture(int(fuente))
        elif tipo == 'IP' or tipo == 'WEB':
            cap = cv2.VideoCapture(fuente)
        else:
            logger.error(f"Tipo de cámara no soportado: {tipo}")
            return False
            
        if not cap.isOpened():
            logger.error(f"No se pudo conectar a la cámara {camara['id']}")
            return False
            
        ret, _ = cap.read()
        cap.release()
        
        return ret
        
    except Exception as e:
        logger.error(f"Error al verificar cámara {camara['id']}: {str(e)}")
        return False

def verificar_camaras():
    """Verifica todas las cámaras registradas y actualiza sus estados"""
    logger.info("Iniciando verificación periódica de cámaras")
    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM camaras")
    camaras = cursor.fetchall()
    conexion.close()
    
    for camara in camaras:
        estado = verificar_conexion_camara(camara)
        nuevo_estado = 'Activo' if estado else 'Inactivo'
        if nuevo_estado != camara['estado']:
            actualizar_estado_camara(camara['id'], nuevo_estado)
            
            # Si la cámara está activa y no tiene un hilo corriendo, iniciarlo
            if nuevo_estado == 'Activo' and camara['id'] not in hilos_camaras:
                iniciar_camara(camara)
            # Si la cámara está inactiva y tiene un hilo corriendo, detenerlo
            elif nuevo_estado == 'Inactivo' and camara['id'] in hilos_camaras:
                detener_camara(camara['id'])

def detener_camara(id_camara):
    """Detiene la transmisión de una cámara específica"""
    if id_camara in hilos_camaras:
        hilos_camaras[id_camara]['activo'] = False
        # El hilo finalizará por sí mismo al detectar activo=False
        logger.info(f"Cámara {id_camara} detenida")

def iniciar_monitoreo():
    """Inicia el scheduler para el monitoreo periódico"""
    if not scheduler.running:
        scheduler.add_job(verificar_camaras, 'interval', minutes=10)
        scheduler.start()
        logger.info("Monitoreo periódico de cámaras iniciado")
        # Realizar verificación inicial
        verificar_camaras()

def detener_monitoreo():
    """Detiene el scheduler y todas las cámaras activas"""
    if scheduler.running:
        scheduler.shutdown()
    for id_camara in list(hilos_camaras.keys()):
        detener_camara(id_camara)
    logger.info("Monitoreo de cámaras detenido")

def iniciar_camara(camara):
    """Versión actualizada de iniciar_camara con mejor manejo de errores y reconexión"""
    id_camara = camara['id']
    tipo = camara['tipo_camara']
    fuente = camara['fuente']
    
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
            actualizar_estado_camara(id_camara, 'Inactivo')
            return
        
        if not cap.isOpened():
            logger.error(f"Error al abrir la cámara {id_camara}: {fuente}")
            actualizar_estado_camara(id_camara, 'Inactivo')
            return
        
        logger.info(f"Cámara {id_camara} iniciada correctamente")
        actualizar_estado_camara(id_camara, 'Activo')
        
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
                actualizar_estado_camara(id_camara, 'Inactivo')
                if id_camara in hilos_camaras:
                    del hilos_camaras[id_camara]
            except Exception as e:
                logger.error(f"Error en el hilo de la cámara {id_camara}: {str(e)}")
                actualizar_estado_camara(id_camara, 'Inactivo')
                if id_camara in hilos_camaras:
                    del hilos_camaras[id_camara]
                
        # Iniciamos el hilo para esta cámara
        stream_thread = threading.Thread(target=stream_video, daemon=True)
        stream_thread.start()
        hilos_camaras[id_camara]['thread'] = stream_thread
        
    except Exception as e:
        logger.error(f"Error al iniciar cámara {id_camara}: {str(e)}")
        actualizar_estado_camara(id_camara, 'Inactivo')
        if id_camara in hilos_camaras:
            del hilos_camaras[id_camara]

# Registra una nueva cámara e inicia la verificación
def registrar_camara(datos_camara):
    """Registra una nueva cámara y actualiza todas las cámaras"""
    try:
        conexion = conectar_db()
        cursor = conexion.cursor()
        
        # Insertar la nueva cámara
        query = """
        INSERT INTO camaras (nombre, local, ubicacion, tipo_camara, fuente, estado, fecha_registro) 
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        valores = (
            datos_camara.get('nombre'), 
            datos_camara.get('local'), 
            datos_camara.get('ubicacion'), 
            datos_camara.get('tipo_camara'), 
            datos_camara.get('fuente'), 
            'Inactivo'  # Inicialmente inactivo hasta verificar
        )
        
        cursor.execute(query, valores)
        conexion.commit()
        nueva_camara_id = cursor.lastrowid
        conexion.close()
        
        logger.info(f"Nueva cámara registrada con ID: {nueva_camara_id}")
        
        # Verificamos todas las cámaras después de un nuevo registro
        verificar_camaras()
        
        return nueva_camara_id
        
    except Exception as e:
        logger.error(f"Error al registrar nueva cámara: {str(e)}")
        return None

# Función para inicializar SocketIO
def set_socketio(socketio_instance):
    """Establece la instancia de SocketIO"""
    global socketio
    socketio = socketio_instance
