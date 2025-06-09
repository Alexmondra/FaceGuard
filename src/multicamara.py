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
from reconocer import procesar_frame , dibujar_resultados
from seguimineto import personas_registradas ,calcular_distancia ,inicializar_modelo_yolo,detectar_personas_con_yolo,asociar_rostros_con_personas ,dibujar_seguimiento 

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
seguimiento_por_camara = {}

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
# --------------------------
# NUEVAS FUNCIONES MODULARES
# --------------------------

def conectar_camara(tipo_camara, fuente, stop_event):
    """Establece conexión con la cámara según su tipo"""
    cap = None
    try:
        if tipo_camara == 'USB':
            cap = cv2.VideoCapture(int(fuente), cv2.CAP_V4L2)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
        else:
            cap = cv2.VideoCapture(fuente)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
        
        # Espera activa para conexión
        inicio = time.time()
        while not cap.isOpened() and (time.time() - inicio) < 3 and not stop_event.is_set():
            time.sleep(0.1)
        
        if not cap.isOpened() or stop_event.is_set():
            raise ConnectionError("No se pudo conectar a la cámara")
        
        return cap
    
    except Exception as e:
        if cap is not None:
            cap.release()
        raise e

def procesar_reconocimiento(frame, camara_id):
    try:
        frame_procesado, recognition_data = procesar_frame(frame, camara_id)
        
        if not all(key in recognition_data for key in ['boxes', 'names', 'colors']):
            logger.warning("Estructura de datos de reconocimiento incompleta")
            recognition_data = {
                'boxes': [],
                'names': [],
                'colors': [],
                'expire_count': frames_to_keep_results
            }
        
        return frame_procesado, recognition_data
    
    except Exception as e:
        logger.error(f"Error en procesar_frame: {str(e)}")
        return frame.copy(), {
            'boxes': [],
            'names': [],
            'colors': [],
            'expire_count': frames_to_keep_results
        }

def realizar_seguimiento(frame, camara_id, recognition_data, yolo_model, personas_registradas):
    """Realiza el seguimiento de personas combinando YOLO y reconocimiento facial"""
    personas_seguimiento = []
    
    # Detectar personas con YOLO
    yolo_detections = detectar_personas_con_yolo(frame, yolo_model)
    
    # Preparar datos de rostros reconocidos
    rostros_reconocidos = []
    if 'boxes' in recognition_data and 'names' in recognition_data:
        rostros_reconocidos = [
            {'box': box, 'nombre': name}
            for box, name in zip(recognition_data['boxes'], recognition_data['names'])
            if name != "Desconocido"
        ]
    
    # Asociar rostros con personas
    try:
        personas_seguimiento = asociar_rostros_con_personas(rostros_reconocidos, yolo_detections)
    except Exception as e:
        logger.error(f"Error al asociar rostros: {str(e)}")
    
    # Actualizar personas_registradas con las detectadas
    for persona in personas_seguimiento:
        if persona['nombre'] not in personas_registradas:
            personas_registradas[persona['nombre']] = {
                'last_centro': persona.get('centro', (0, 0)),
                'last_box': persona.get('box_rostro', [0, 0, 0, 0])
            }
        else:
            personas_registradas[persona['nombre']]['last_centro'] = persona.get('centro', (0, 0))
            personas_registradas[persona['nombre']]['last_box'] = persona.get('box_rostro', [0, 0, 0, 0])
    
    # Para personas registradas pero no detectadas en este frame, intentar seguir
    for nombre, datos in personas_registradas.items():
        if nombre not in [p['nombre'] for p in personas_seguimiento]:
            mejor_distancia = 150  # Máxima distancia permitida
            mejor_persona = None
            
            for persona in yolo_detections:
                distancia = calcular_distancia(datos['last_centro'], persona['centro'])
                if distancia < mejor_distancia:
                    mejor_distancia = distancia
                    mejor_persona = persona
            
            if mejor_persona is not None:
                personas_seguimiento.append({
                    'box_persona': mejor_persona['box'],
                    'nombre': nombre,
                    'box_rostro': datos['last_box'],
                    'confianza': mejor_persona['confianza']
                })
    
    return personas_seguimiento

def seguir_personas_registradas(frame, yolo_model, personas_registradas):
    """Sigue a personas registradas usando solo detección YOLO"""
    personas_seguimiento = []
    yolo_detections = detectar_personas_con_yolo(frame, yolo_model)
    
    for nombre, datos in personas_registradas.items():
        mejor_distancia = 150  # Máxima distancia permitida
        mejor_persona = None
        
        for persona in yolo_detections:
            distancia = calcular_distancia(datos['last_centro'], persona['centro'])
            if distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_persona = persona
        
        if mejor_persona is not None:
            personas_seguimiento.append({
                'box_persona': mejor_persona['box'],
                'nombre': nombre,
                'box_rostro': datos['last_box'],
                'confianza': mejor_persona['confianza']
            })
    
    return personas_seguimiento

def enviar_frame(camara_id, frame, enviar_frames=True):
    """Envía el frame procesado a los clientes suscritos"""
    try:
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_base64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
        
        with hilos_lock:
            if camara_id in hilos_camaras and hilos_camaras[camara_id].get('enviar_frames', True):
                socketio.emit('video_frame', {
                    'camera_id': camara_id,
                    'frame': frame_base64
                }, room=f'camara_{camara_id}', namespace='/')
                hilos_camaras[camara_id].update({
                    'last_frame': frame_base64,
                    'last_activity': time.time()
                })
        
        return True
    
    except Exception as e:
        logger.error(f"[PROCESAMIENTO] Error enviando frame: {str(e)}")
        return False

# --------------------------
# FUNCIÓN PRINCIPAL REFACTORIZADA
# --------------------------

def hilo_camara(camara_id, nombre, tipo_camara, fuente, stop_event):
    """Thread persistente que maneja conexión y reconexión automática de la cámara"""
    logger.info(f"[THREAD-START] Iniciando hilo persistente para cámara {nombre} (ID: {camara_id})")
    global personas_registradas
    
    # Configuración de procesamiento
    skip_frames = 10  # Procesar reconocimiento cada 10 frames
    frame_counter = 0
    frames_to_keep_results = 15  
    yolo_model = inicializar_modelo_yolo()
    
    
    # Variables para retención de resultados
    last_recognition_results = {
        'boxes': [],
        'names': [],
        'colors': [],
        'expire_count': 0
    }
    last_yolo_results = {
        'boxes': [],
        'confidences': [],
        'expire_count': 0
    }
    # Estado de seguimiento para esta cámara
    personas_seguimiento = []
    
    while not stop_event.is_set():
        # Conexión inicial
        with hilos_lock:
            hilos_camaras[camara_id].update({
                'connecting': True,
                'running': True,
                'activo': False,
                'last_activity': time.time(),
                'errors': 0
            })
        
        cap = None
        try:
            # Conectar a la cámara
            cap = conectar_camara(tipo_camara, fuente, stop_event)
            logger.info(f"[CONEXIÓN-EXITOSA] {nombre} conectada")
            
            with hilos_lock:
                hilos_camaras[camara_id].update({
                    'activo': True,
                    'connecting': False,
                    'cap': cap,
                    'last_success': time.time(),
                    'seguimiento_activo': True
                })
            actualizar_estado_camara(camara_id, 'Activo')
            
            # Bucle principal de captura
            while not stop_event.is_set():
                ret, frame = cap.read()
                
                if not ret:
                    with hilos_lock:
                        hilos_camaras[camara_id]['errors'] += 1
                    time.sleep(0.1)
                    continue
                
                frame_counter += 1
                frame_procesado = frame.copy()
                
                # Obtener estado de seguimiento actualizado
                with hilos_lock:
                    seguimiento_activo = hilos_camaras[camara_id].get('seguimiento_activo', False)
                
                # Procesamiento con reconocimiento (cada skip_frames)
                if frame_counter % skip_frames == 0:
                    try:
                        # Procesar reconocimiento facial
                        frame_procesado, recognition_data = procesar_reconocimiento(frame, camara_id)
                        last_recognition_results = recognition_data
                        
                        # Si hay seguimiento activo, procesar asociaciones
                        if seguimiento_activo:
                            logger.info(f"[SEGUIMIENTO] Procesando seguimiento para cámara {camara_id}")
                            
                            personas_seguimiento = realizar_seguimiento(
                                frame, camara_id, recognition_data, yolo_model, personas_registradas
                            )
                        
                        with hilos_lock:
                            hilos_camaras[camara_id]['last_processed_frame'] = frame_procesado
                    
                    except Exception as e:
                        logger.error(f"Error en procesamiento: {str(e)}")
                else:
                    # Entre frames de reconocimiento, usar YOLO para seguir personas registradas
                    if seguimiento_activo and personas_registradas:
                        try:
                            personas_seguimiento = seguir_personas_registradas(
                                frame, yolo_model, personas_registradas
                            )
                        except Exception as e:
                            logger.error(f"Error en seguimiento YOLO: {str(e)}")
                    
                    # Dibujar resultados anteriores
                    if last_recognition_results.get('expire_count', 0) > 0:
                        last_recognition_results['expire_count'] -= 1
                        frame_procesado = dibujar_resultados(frame.copy(), last_recognition_results)
                
                # Dibujar seguimiento en TODOS los frames si hay personas a seguir
                if seguimiento_activo and personas_seguimiento:
                    frame_procesado = dibujar_seguimiento(frame_procesado, personas_seguimiento)
                
                # Envío del frame
                enviar_frame(camara_id, frame_procesado)
                
                # Control FPS más flexible
                time.sleep(0.03 if frame_counter % skip_frames == 0 else 0.01)
        
        except Exception as e:
            logger.error(f"[ERROR] Error en cámara {nombre}: {str(e)}")
            actualizar_estado_camara(camara_id, 'Inactivo')
            time.sleep(1)
        
        finally:
            if cap is not None:
                try:
                    cap.release()
                except:
                    pass
            
            with hilos_lock:
                hilos_camaras[camara_id].update({
                    'activo': False,
                    'cap': None
                })
            
            if not stop_event.is_set():
                logger.info(f"[RECONEXIÓN] Esperando 5 segundos para reconectar {nombre}")
                time.sleep(5)
    
    # Limpieza al terminar el hilo
    with hilos_lock:
        personas_registradas = {k: v for k, v in personas_registradas.items() 
            if v['nombre'] not in [p['nombre'] for p in personas_seguimiento]}
        
        if camara_id in seguimiento_por_camara:
            del seguimiento_por_camara[camara_id]
    
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
                        'activo': False,
                        'seguimiento_activo': False
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
        

# Handlers de Socket.IO
@socketio.on('subscribe_camera')
def handle_subscribe_camera(data):
    camara_id = data.get('camera_id')
    if camara_id:
        join_room(f'camara_{camara_id}')
        with hilos_lock:
            if camara_id in hilos_camaras:
                hilos_camaras[camara_id]['enviar_frames'] = True
                logger.info(f"Cliente {request.sid} suscrito a cámara {camara_id}")

@socketio.on('unsubscribe_camera')
def handle_unsubscribe_camera(data):
    """Único handler para desuscripción"""
    camara_id = data.get('camera_id')
    if camara_id:
        leave_room(f'camara_{camara_id}')
        logger.info(f"Cliente {request.sid} desuscrito de cámara {camara_id}")
        
        
# Nuevos handlers para control por cámara
@socketio.on('activar_seguimiento')
def handle_activar_seguimiento(data):
    camara_id = data.get('camera_id')
    if camara_id:
        with hilos_lock:
            if camara_id in hilos_camaras:
                hilos_camaras[camara_id]['seguimiento_activo'] = True
        logger.info(f"Seguimiento activado para cámara {camara_id}")

@socketio.on('desactivar_seguimiento')
def handle_desactivar_seguimiento(data):
    camara_id = data.get('camera_id')
    if camara_id:
        with hilos_lock:
            if camara_id in hilos_camaras:
                hilos_camaras[camara_id]['seguimiento_activo'] = False
        logger.info(f"Seguimiento desactivado para cámara {camara_id}")