import threading
import cv2
import numpy as np
import base64
import torch
from PIL import Image
from conexiondb import conectar_db
from facenet_pytorch import MTCNN
from utils import mtcnn, facenet, transform_facenet, socketio
from flask_socketio import join_room, leave_room
from flask import request
import logging
import time
import fcntl 
import os


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
            'thread_id': data['thread'].ident,
            'name': data['nombre'],
            'alive': data['thread'].is_alive(),
            'sending_frames': data['enviar_frames'],
            'last_frame': data['last_frame'] is not None
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
    """Thread que gestiona la conexión y captura de frames de la cámara"""
    logger.info(f"[THREAD-START] Iniciando hilo para cámara {nombre} (ID: {camara_id})")
    
    # Registrar el hilo con estado inicial
    with hilos_lock:
        hilos_camaras[camara_id] = {
            'thread': threading.current_thread(),
            'stop_event': stop_event,
            'enviar_frames': True,
            'last_frame': None,
            'nombre': nombre,
            'activo': True,
            'running': True  # Nuevo flag para controlar estado real
        }
    
    cap = None
    tiempo_espera_conexion = 3  # Segundos para esperar conexión
    
    try:
        # Intento de conexión único
        logger.debug(f"[CONEXIÓN] Intentando conectar a {nombre}...")
        
        if tipo_camara == 'USB':
            cap = cv2.VideoCapture(int(fuente), cv2.CAP_V4L2)
            # Configuración óptima para USB
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
        else:
            cap = cv2.VideoCapture(fuente)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)  # 3 segundos timeout
        
        # Espera activa para conexión
        inicio = time.time()
        while not cap.isOpened() and (time.time() - inicio) < tiempo_espera_conexion:
            time.sleep(0.1)
        
        if not cap.isOpened():
            logger.error(f"[CONEXIÓN-FALLIDA] No se pudo conectar a {nombre}")
            actualizar_estado_camara(camara_id, 'Inactivo')
            return
        
        # Conexión exitosa
        logger.info(f"[CONEXIÓN-EXITOSA] {nombre} conectada")
        actualizar_estado_camara(camara_id, 'Activo')
        
        # Variables para control de frames perdidos
        max_frames_perdidos = 10
        frames_perdidos = 0
        
        # Bucle principal de captura
        while not stop_event.is_set():
            ret, frame = cap.read()
            
            if not ret:
                frames_perdidos += 1
                logger.warning(f"[FRAME-ERROR] Frame perdido #{frames_perdidos} en {nombre}")
                
                if frames_perdidos >= max_frames_perdidos:
                    logger.error(f"[DESCONEXIÓN] Demasiados frames perdidos en {nombre}")
                    actualizar_estado_camara(camara_id, 'Inactivo')
                    break
                
                time.sleep(0.1)
                continue
            
            # Resetear contador si frame es válido
            frames_perdidos = 0
            
            # Procesamiento del frame
            try:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
                
                with hilos_lock:
                    if camara_id in hilos_camaras and hilos_camaras[camara_id]['enviar_frames']:
                        socketio.emit('video_frame', {
                            'camera_id': camara_id,
                            'frame': frame_base64
                        }, room=f'camara_{camara_id}', namespace='/')
                        hilos_camaras[camara_id]['last_frame'] = frame_base64
                
                time.sleep(0.03)  # Control de FPS (~30fps)
            
            except Exception as e:
                logger.error(f"[PROCESAMIENTO] Error procesando frame en {nombre}: {str(e)}")
                continue
    
    except Exception as e:
        logger.error(f"[ERROR-HILO] Error en hilo {nombre}: {str(e)}")
        actualizar_estado_camara(camara_id, 'Inactivo')
    
    finally:
        logger.info(f"[FINALIZACIÓN] Limpiando recursos de {nombre}")
        
        # Cerrar conexión con la cámara
        if cap is not None:
            try:
                cap.release()
            except:
                pass
        
        # Marcar como terminado pero no eliminar inmediatamente
        with hilos_lock:
            if camara_id in hilos_camaras:
                hilos_camaras[camara_id]['running'] = False
                hilos_camaras[camara_id]['activo'] = False
        
        logger.info(f"[HILO-TERMINADO] Hilo de {nombre} finalizado")

def verificar_y_lanzar_camaras():
    """Verifica y gestiona el estado de los hilos de cámara"""
    logger.info("[MONITOR] Verificando estado de cámaras")
    
    conn = conectar_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, tipo_camara, fuente FROM camaras WHERE estado = 'Inactivo'")
        camaras = cursor.fetchall()
        
        with hilos_lock:
            # Primero limpiar hilos terminados
            ahora = time.time()
            for camara_id in list(hilos_camaras.keys()):
                hilo_data = hilos_camaras[camara_id]
                
                # Eliminar solo si el hilo terminó y está marcado como no running
                if not hilo_data['running'] and not hilo_data['thread'].is_alive():
                    logger.info(f"[LIMPIAR-HILO] Eliminando hilo terminado para {hilo_data['nombre']}")
                    del hilos_camaras[camara_id]
            
            # Luego crear nuevos hilos para cámaras inactivas
            for camara in camaras:
                camara_id = camara['id']
                
                if camara_id not in hilos_camaras or (
                    not hilos_camaras[camara_id]['thread'].is_alive() and 
                    not hilos_camaras[camara_id]['running']
                ):
                    logger.info(f"[CREAR-HILO] Iniciando hilo para {camara['nombre']}")
                    stop_event = threading.Event()
                    new_thread = threading.Thread(
                        target=hilo_camara,
                        args=(camara_id, camara['nombre'], camara['tipo_camara'], camara['fuente'], stop_event),
                        daemon=True
                    )
                    
                    hilos_camaras[camara_id] = {
                        'thread': new_thread,
                        'stop_event': stop_event,
                        'enviar_frames': True,
                        'last_frame': None,
                        'nombre': camara['nombre'],
                        'activo': False,
                        'running': True
                    }
                    
                    new_thread.start()
    
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
        

def diagnostico_hilos():
    """Función para diagnosticar problemas con los hilos"""
    with hilos_lock:
        # 1. Ver hilos registrados
        registrados = list(hilos_camaras.keys())
        
        # 2. Ver hilos activos del sistema
        activos = [t.name for t in threading.enumerate() if t.name.startswith('Camara_')]
        
        # 3. Encontrar discrepancias
        problemas = []
        for camara_id, data in hilos_camaras.items():
            if not data['thread'].is_alive():
                problemas.append(f"Cámara {camara_id} registrada pero hilo muerto")
        
        for thread_name in activos:
            parts = thread_name.split('_')
            if len(parts) >= 2 and parts[0] == 'Camara':
                camara_id = parts[1]
                if camara_id not in hilos_camaras:
                    problemas.append(f"Hilo {thread_name} activo pero no registrado")
    
    return {
        'registrados': registrados,
        'activos': activos,
        'problemas': problemas
    }


# Demonio para supervisar los hilos             
# Handlers de Socket.IO
@socketio.on('subscribe_camera')
def handle_subscribe_camera(data):
    """Único handler para suscripción"""
    camara_id = data.get('camera_id')
    if camara_id:
        join_room(f'camara_{camara_id}')
        with hilos_lock:
            if camara_id in hilos_camaras:
                hilos_camaras[camara_id]['enviar_frames'] = True
        logger.info(f"Cliente {request.sid} suscrito a cámara {camara_id}")

        # Enviar último frame si existe
        with hilos_lock:
            if camara_id in hilos_camaras and hilos_camaras[camara_id].get('last_frame'):
                socketio.emit('video_frame', {
                    'camera_id': camara_id,
                    'frame': hilos_camaras[camara_id]['last_frame']
                }, room=request.sid, namespace='/')

@socketio.on('unsubscribe_camera')
def handle_unsubscribe_camera(data):
    """Único handler para desuscripción"""
    camara_id = data.get('camera_id')
    if camara_id:
        leave_room(f'camara_{camara_id}')
        logger.info(f"Cliente {request.sid} desuscrito de cámara {camara_id}")