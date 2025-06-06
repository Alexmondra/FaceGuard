import threading
import cv2
import numpy as np
import base64
import torch
from PIL import Image
from conexiondb import conectar_db, indice_persona_id, faiss_index
from facenet_pytorch import MTCNN
from utils import mtcnn, facenet, transform_facenet, socketio
from flask_socketio import join_room, leave_room
from flask import request
import logging
import time
import fcntl 
import os

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

hilos_camaras = {}
hilos_lock = threading.Lock()  # Lock para operaciones con hilos

def obtener_estado_hilos_activos():
    with hilos_lock:
        hilos_vivos = {camara_id: data for camara_id, data in hilos_camaras.items() if data['thread'].is_alive()}
        
        estado = {
            'total_hilos_activos': len(hilos_vivos),
            'detalle': []
        }
        
        for camara_id, data in hilos_vivos.items():
            thread = data['thread']
            estado['detalle'].append({
                'camara_id': camara_id,
                'hilo_nombre': thread.name,
                'hilo_vivo': True,
                'ultimo_frame': data.get('last_frame'),
                'enviando_frames': data.get('enviar_frames', False)
            })
            
        return estado
  
    
def verificar_conexion_segura(tipo_camara, fuente):
    """Verifica la cámara SIN dejar recursos abiertos"""
    try:
        if tipo_camara == 'USB':
            if not os.path.exists(f"/dev/video{fuente}"):
                return False
            
            # Prueba ultra-rápida sin interferir
            cap = cv2.VideoCapture(int(fuente))
            if not cap.isOpened():
                return False
            
            # Cierre inmediato y limpieza
            cap.release()
            time.sleep(0.1)  # Breve pausa para liberar dispositivo
            return True
            
        else:  # Para cámaras IP/Web
            cap = cv2.VideoCapture(fuente)
            if not cap.isOpened():
                return False
            cap.release()
            return True
            
    except Exception as e:
        logger.warning(f"Error en verificación: {str(e)}")
        return False
    
    
# Función que ejecuta el hilo para una cámara
def hilo_camara(camara_id, nombre, tipo_camara, fuente, stop_event):
    """Hilo principal optimizado para una cámara"""
    try:
        cap = None
        intentos = 0
        max_intentos = 3

        while not stop_event.is_set() and intentos < max_intentos:
            try:
                # Intentar conectar a la cámara
                cap = cv2.VideoCapture(int(fuente), cv2.CAP_V4L2) if tipo_camara == 'USB' else cv2.VideoCapture(fuente)

                if not cap.isOpened():
                    raise RuntimeError("No se pudo abrir la cámara")

                actualizar_estado_camara(camara_id, 'Activo')
                logger.info(f"Cámara {nombre} conectada exitosamente")

                while not stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning(f"Error de frame en cámara {nombre}. Reiniciando...")
                        raise RuntimeError("La cámara dejó de enviar frames")

                    # Procesar el frame una sola vez
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frame_bytes = buffer.tobytes()
                    frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

                    # Enviar solo si hay suscriptores
                    with hilos_lock:
                        if camara_id in hilos_camaras and hilos_camaras[camara_id].get('enviar_frames', False):
                            socketio.emit('video_frame', {
                                'camera_id': camara_id,
                                'frame': frame_base64
                            }, room=f'camara_{camara_id}', namespace='/')
                            hilos_camaras[camara_id]['last_frame'] = frame_base64

                    time.sleep(0.03)  # Control de FPS (~30fps)

            except Exception as e:
                logger.error(f"Error en cámara {nombre}: {str(e)}")
                intentos += 1
                time.sleep(1)
            finally:
                if cap:
                    cap.release()

        if intentos >= max_intentos:
            logger.error(f"Cámara {nombre} superó el máximo de reintentos")
            actualizar_estado_camara(camara_id, 'Inactivo')

    except Exception as e:
        logger.critical(f"Error crítico en hilo de cámara {nombre}: {str(e)}")
    finally:
        with hilos_lock:
            if camara_id in hilos_camaras:
                del hilos_camaras[camara_id]
        logger.info(f"Hilo para cámara {nombre} finalizado")

def verificar_y_lanzar_camaras():
    conn = conectar_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, tipo_camara, fuente FROM camaras WHERE estado = 'Inactivo'")
        camaras = cursor.fetchall()

        with hilos_lock:
            for camara in camaras:
                camara_id = camara['id']
                
                # Evitar duplicados
                if camara_id in hilos_camaras and hilos_camaras[camara_id]['thread'].is_alive():
                    continue
                
                # Verificación NO BLOQUEANTE
                if not verificar_conexion_segura(camara['tipo_camara'], camara['fuente']):
                    logger.warning(f"Cámara {camara['nombre']} no disponible. Omitiendo...")
                    continue
                
                # Crear hilo (la conexión real ocurrirá DENTRO del hilo)
                stop_event = threading.Event()
                new_thread = threading.Thread(
                    target=hilo_camara,
                    args=(camara_id, camara['nombre'], camara['tipo_camara'], camara['fuente'], stop_event),
                    daemon=True
                    
                )
                
                hilos_camaras[camara_id] = {
                    'thread': new_thread,
                    'stop_event': stop_event,
                    'last_frame': None
                }
                
                new_thread.start()
                logger.info(f"Hilo asignado para cámara {camara['nombre']}")

    except Exception as e:
        logger.error(f"Error en verificar_y_lanzar_camaras: {str(e)}")
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