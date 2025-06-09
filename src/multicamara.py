import threading
import cv2
import numpy as np
import base64
from conexiondb import conectar_db
from utils import socketio
from flask_socketio import join_room, leave_room
from flask import request
import logging
import time
from reconocer import procesar_frame

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('camera_threads.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global variables
hilos_camaras = {}
hilos_lock = threading.Lock()


def listar_hilos_activos():
    """Lists all active threads in the system"""
    logger.debug("[THREAD-LIST] Generating list of all active threads")
    return [{
        'id': thread.ident,
        'name': thread.name,
        'alive': thread.is_alive(),
        'daemon': thread.daemon
    } for thread in threading.enumerate()]

def listar_hilos_camaras():
    """Lists all camera threads with detailed status"""
    logger.debug("[CAMERA-THREAD-LIST] Generating camera thread status")
    with hilos_lock:
        return [{
            'camara_id': cam_id,
            'thread_id': data.get('thread', {}).ident if 'thread' in data else None,
            'name': data.get('nombre', 'Desconocido'),
            'alive': data.get('thread', {}).is_alive() if 'thread' in data else False,
            'sending_frames': data.get('enviar_frames', False),
            'last_frame': data.get('last_frame') is not None,
            'activo': data.get('activo', False),
            'running': data.get('running', False),
            'last_activity': data.get('last_activity', 0)
        } for cam_id, data in hilos_camaras.items()]



def cerrarhiloCamara(camara_id):
    """Cierra el hilo y libera la cámara de manera forzosa"""
    with hilos_lock:
        if camara_id not in hilos_camaras:
            logger.warning(f"No se encontró hilo para cámara {camara_id}")
            return False

        data = hilos_camaras[camara_id]
        data['stop_event'].set()
        hilo = data['thread']
        cap = data.get('cap')

    # Liberación forzosa de la cámara
    if cap is not None:
        try:
            cap.release()
            time.sleep(0.5)
            cv2.destroyAllWindows()
            logger.info(f"Recursos de cámara {camara_id} liberados")
        except Exception as e:
            logger.error(f"Error liberando cámara {camara_id}: {str(e)}")

    # Espera controlada para el hilo
    if hilo.is_alive():
        hilo.join(timeout=1.0)
        if hilo.is_alive():
            logger.warning(f"Forzando terminación del hilo {camara_id}")
            try:
                hilo._stop()
            except:
                pass

    with hilos_lock:
        if camara_id in hilos_camaras:
            del hilos_camaras[camara_id]
    
    return True

# Función que ejecuta el hilo para una cámara
def hilo_camara(camara_id, nombre, tipo_camara, fuente, stop_event):
    """Thread persistente que maneja conexión y reconexión automática de la cámara"""
    logger.info(f"[THREAD-START] Iniciando hilo persistente para cámara {nombre} (ID: {camara_id})")
    
    while not stop_event.is_set():  # Bucle principal persistente
        # Inicialización del estado
        with hilos_lock:
            hilos_camaras[camara_id].update({
                'connecting': True,
                'running': True,
                'activo': False,
                'last_activity': time.time(),
                'errors': 0
            })
        
        cap = None
        frames_perdidos = 0
        max_frames_perdidos = 10
        frame_skip = 10
        frame_count = 0
        
        try:
            # Configuración de conexión
            logger.info(f"[CONEXIÓN] Intentando conectar a {nombre}...")
            if tipo_camara == 'USB':
                cap = cv2.VideoCapture(int(fuente), cv2.CAP_V4L2)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
            else:
                cap = cv2.VideoCapture(fuente)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
            
            # Espera activa para conexión (3 segundos máximo)
            inicio = time.time()
            while not cap.isOpened() and (time.time() - inicio) < 3 and not stop_event.is_set():
                time.sleep(0.1)
            
            if not cap.isOpened() or stop_event.is_set():
                raise ConnectionError(f"No se pudo conectar a {nombre}")
            
            # Conexión exitosa
            logger.info(f"[CONEXIÓN-EXITOSA] {nombre} conectada")
            with hilos_lock:
                hilos_camaras[camara_id].update({
                    'activo': True,
                    'connecting': False,
                    'cap': cap,
                    'last_success': time.time()
                })
            actualizar_estado_camara(camara_id, 'Activo')
            
            # Bucle principal de captura
            while not stop_event.is_set():
                ret, frame = cap.read()
                
                if not ret:
                    frames_perdidos += 1
                    with hilos_lock:
                        hilos_camaras[camara_id]['errors'] += 1
                    
                    if frames_perdidos >= max_frames_perdidos:
                        logger.error(f"[DESCONEXIÓN] Demasiados frames perdidos en {nombre}")
                        break
                    
                    time.sleep(0.1)
                    continue
                
                # Frame válido recibido
                frames_perdidos = 0
                frame_count += 1
                
                # Procesamiento del frame (código existente)
                with hilos_lock:
                    reconocimiento_activo = hilos_camaras[camara_id].get('reconocimiento_activo', False)
                    enviar_frames = hilos_camaras[camara_id].get('enviar_frames', True)
                
                frame_procesado = frame
                if reconocimiento_activo and frame_count % frame_skip == 0:
                    frame_procesado, _ = procesar_frame(frame, reconocimiento_activo=True)
                    with hilos_lock:
                        hilos_camaras[camara_id]['last_processed_frame'] = frame_procesado
                
                try:
                    _, buffer = cv2.imencode('.jpg', frame_procesado, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frame_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
                    
                    with hilos_lock:
                        if camara_id in hilos_camaras and enviar_frames:
                            socketio.emit('video_frame', {
                                'camera_id': camara_id,
                                'frame': frame_base64,
                                'reconocimiento_activo': reconocimiento_activo
                            }, room=f'camara_{camara_id}', namespace='/')
                            hilos_camaras[camara_id].update({
                                'last_frame': frame_base64,
                                'last_activity': time.time()
                            })
                    
                    time.sleep(0.03)  # Control de FPS (~30fps)
                
                except Exception as e:
                    logger.error(f"[PROCESAMIENTO] Error procesando frame: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"[ERROR] Error en cámara {nombre}: {str(e)}")
            actualizar_estado_camara(camara_id, 'Inactivo')
            
        finally:
            # Limpieza segura
            if cap is not None:
                try:
                    cap.release()
                except:
                    pass
            
            with hilos_lock:
                hilos_camaras[camara_id].update({
                    'activo': False,
                    'cap': None,
                    'last_activity': time.time()
                })
            
            # Espera para reconexión (excepto si nos pidieron detener)
            if not stop_event.is_set():
                logger.info(f"[RECONEXIÓN] Esperando 60 segundos para reconectar {nombre}")
                for _ in range(30):  # Espera en intervalos de 1 segundo para verificar stop_event
                    if stop_event.is_set():
                        break
                    time.sleep(1)
    
    # Limpieza final al detener el hilo
    logger.info(f"[HILO-TERMINADO] Hilo persistente de {nombre} finalizado")
    with hilos_lock:
        if camara_id in hilos_camaras:
            hilos_camaras[camara_id]['running'] = False       
        
        

def verificar_y_lanzar_camaras():
    logger.info("[MONITOR] Verificando cámaras nuevas")
    conn = conectar_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, tipo_camara, fuente FROM camaras")
        
        with hilos_lock:
            # Solo crear hilos para cámaras que no tienen uno
            for camara in cursor.fetchall():
                cam_id = camara['id']
                if cam_id not in hilos_camaras:
                    logger.info(f"[NUEVO-HILO] Creando hilo persistente para {camara['nombre']}")
                    stop_event = threading.Event()
                    thread = threading.Thread(
                        target=hilo_camara,
                        args=(cam_id, camara['nombre'], camara['tipo_camara'], camara['fuente'], stop_event),
                        daemon=True
                    )
                    
                    hilos_camaras[cam_id] = {
                        'thread': thread,
                        'stop_event': stop_event,
                        'nombre': camara['nombre'],
                        'running': True,
                        'activo': False
                    }
                    thread.start()
                    
    except Exception as e:
        logger.error(f"[MONITOR-ERROR] Error: {str(e)}")
    finally:
        conn.close()


def actualizar_estado_camara(camara_id, estado):
    """Actualiza el estado en la base de datos"""
    conn = conectar_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE camaras SET estado = %s WHERE id = %s", (estado, camara_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error actualizando estado cámara {camara_id}: {str(e)}")
    finally:
        conn.close()
        
1
# Handlers de Socket.IO
@socketio.on('subscribe_camera')
def handle_subscribe_camera(data):
    camara_id = data.get('camera_id')
    if camara_id:
        join_room(f'camara_{camara_id}')
        with hilos_lock:
            if camara_id in hilos_camaras:
                hilos_camaras[camara_id]['enviar_frames'] = True
                hilos_camaras[camara_id]['reconocimiento_activo'] = True  # Forzar activación
                logger.info(f"Reconocimiento ACTIVADO para cámara {camara_id}")  # Log de confirmación


@socketio.on('unsubscribe_camera')
def handle_unsubscribe_camera(data):
    """Único handler para desuscripción"""
    camara_id = data.get('camera_id')
    if camara_id:
        leave_room(f'camara_{camara_id}')
        logger.info(f"Cliente {request.sid} desuscrito de cámara {camara_id}")