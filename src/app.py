import os
from flask import Flask, send_from_directory
import webbrowser
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager
import numpy as np
import cv2
import faiss  
import torch 
import logging
import atexit
from facenet_pytorch import MTCNN, InceptionResnetV1
from torchvision import transforms
from PIL import Image
import base64
import pytz
from datetime import datetime
import threading
import webbrowser
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
from conexiondb import conectar_db,crear_tablas_si_no_existen, cargar_embeddings_faiss, faiss_index, indice_persona_id
from registros import rutas_personas,obtener_datos_persona
from utils import detect_faces, generar_embedding, mtcnn, facenet, transform_facenet
from camaras import iniciar_monitoreo, detener_monitoreo, registrar_camara, obtener_camaras_activas, set_socketio, verificar_camaras

# Import the auth blueprint

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__)

#creacion de tablas 
db = conectar_db()
if db:
    crear_tablas_si_no_existen(db)
    db.close()

# Inicializar zona horaria (Perú)
zona_peru = pytz.timezone('America/Lima')

# Inicializar Flask
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar socketio en el módulo de cámaras
set_socketio(socketio)

# Configure JWT
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this in production!
jwt = JWTManager(app)

# Register the auth blueprint
app.register_blueprint(auth_bp)

def abrir_navegador():
    ruta_login = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '../frontend/index.html'))
    webbrowser.open_new(f"file://{ruta_login}")

# Inicializar FAISS cargando embeddings desde la base de datos
cargar_embeddings_faiss()

# Iniciar el sistema de monitoreo de cámaras
iniciar_monitoreo()

# Función de limpieza al cerrar la aplicación
def cleanup():
    try:
        detener_monitoreo()
        logger.info("Sistema de monitoreo de cámaras detenido")
    except Exception as e:
        logger.error(f"Error durante la limpieza: {str(e)}")

# Registrar función de limpieza
atexit.register(cleanup)

@app.route('/reconocer', methods=['POST'])
def reconocer():
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró ningún archivo"}), 400

    img = Image.open(io.BytesIO(request.files['file'].read())).convert('RGB')
    img_cv = np.array(img)  # Convertir a formato OpenCV
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

    rostros = detect_faces(img)
    if not rostros:
        return jsonify({"error": "No se detectaron rostros"}), 400

    draw = img_cv.copy()
    boxes, _ = mtcnn.detect(img)

    resultados = []
    umbral_confianza = 70

    if boxes is not None:
        for i, (box, rostro) in enumerate(zip(boxes, rostros)):
            x1, y1, x2, y2 = map(int, box)
            embedding = generar_embedding(rostro)

            if embedding is None:
                continue

            distancias, indices = faiss_index.search(np.array(embedding, dtype=np.float32).reshape(1, -1), 1)
            persona_id, nombre, dni, confianza = None, "Desconocido", "-", 0

            if indices[0][0] != -1:
                distancia = distancias[0][0]
                confianza = round((1 - distancia) * 100, 2)

                if confianza >= umbral_confianza:
                    persona_id = indice_persona_id[indices[0][0]]
                    datos = obtener_datos_persona(persona_id)
                    nombre = datos["nombre"]
                    dni = datos["dni"]

            resultados.append({
                "rostro": i + 1,
                "persona_id": persona_id,
                "nombre": nombre,
                "dni": dni,
                "confianza": confianza
            })

            # Dibujar rectángulo y texto sobre la imagen
            color = (0, 255, 0) if persona_id else (0, 0, 255)  # Verde si es reconocido, Rojo si no
            cv2.rectangle(draw, (x1, y1), (x2, y2), color, 2)
            cv2.putText(draw, f"{i+1}. {nombre} ({confianza}%)", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

    # Convertir la imagen procesada a formato base64
    _, img_encoded = cv2.imencode('.jpg', draw)
    img_base64 = img_encoded.tobytes()

    return jsonify({"resultados": resultados, "imagen": img_base64.hex()})



enviar_frames = False
reconocimiento_activo = False
video_thread = None
cap = None


## video de cámara 
def generar_video_socket():
    global video_thread, enviar_frames, reconocimiento_activo, cap
    # Verificar si la cámara está conectada
    if cap is None or not cap.isOpened():
        print("No se pudo abrir la cámara. Deteniendo transmisión.")
        return
    
    print("Transmisión de video iniciada.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se pudo leer el frame de la cámara.")
            break

        if reconocimiento_activo:
            # Procesar el reconocimiento facial
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            boxes, _ = mtcnn.detect(img_pil)
            rostros = [img_pil.crop(list(map(int, box))) for box in boxes] if boxes is not None else []
            
            if boxes is not None:
                for i, (box, rostro) in enumerate(zip(boxes, rostros)):
                    x1, y1, x2, y2 = map(int, box)
                    embedding = transform_facenet(rostro).unsqueeze(0)
                    with torch.no_grad():
                        embedding = facenet(embedding).squeeze().numpy()
                    
                    color = (0, 0, 255)  # Rojo por defecto
                    nombre = "Desconocido"
                    confianza = 0
                    
                    if faiss_index is not None:
                        distancias, indices = faiss_index.search(np.array(embedding, dtype=np.float32).reshape(1, -1), 1)
                        if indices[0][0] != -1:
                            distancia = distancias[0][0]
                            confianza = round((1 - distancia) * 100, 2)
                            if confianza >= 70:
                                persona_id = indice_persona_id[indices[0][0]]
                                nombre = f"Persona {persona_id}"
                                color = (0, 255, 0)  # Verde si reconocido
                                 # aqui va ir a una de seguimiento aun no esta (persona_id)
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{nombre} ({confianza}%)", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
        
        if enviar_frames:
            # Enviar el frame (procesado o no procesado)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_bytes = buffer.tobytes()
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
            
            socketio.emit('video_frame', {'frame': frame_base64}, namespace='/')
            print("Frame enviado correctamente")
        
        socketio.sleep(0.03)  # Reducir la carga del procesador
    
    cap.release()
    print("Transmisión de video finalizada.")


@socketio.on('start_video')
def start_video():
    global enviar_frames
    enviar_frames = True
    print("Envío de frames activado.")

@socketio.on('stop_video')
def stop_video():
    global enviar_frames
    enviar_frames = False
    print("Envío de frames desactivado.")

@socketio.on('start_recognition')
def start_recognition():
    global reconocimiento_activo
    reconocimiento_activo = True
    print("Reconocimiento facial activado.")

@socketio.on('stop_recognition')
def stop_recognition():
    global reconocimiento_activo
    reconocimiento_activo = False
    print("Reconocimiento facial desactivado.")

@socketio.on('request_video')
def send_video():
    global video_thread
    if video_thread is None or not video_thread.is_alive():
        print("Iniciando transmisión de video en vivo...")
        video_thread = threading.Thread(target=generar_video_socket, daemon=True)
        video_thread.start()
    else:
        print("El hilo de transmisión ya está activo.")


@app.route('/camaras', methods=['GET'])
def listar_camaras():
    """Endpoint para listar todas las cámaras"""
    try:
        camaras = obtener_camaras_activas()
        return jsonify({'camaras': camaras}), 200
    except Exception as e:
        logger.error(f"Error al listar cámaras: {str(e)}")
        return jsonify({'error': 'Error al obtener la lista de cámaras'}), 500

@app.route('/camaras', methods=['POST'])
def nueva_camara():
    """Endpoint para registrar una nueva cámara y verificar todas las cámaras"""
    try:
        datos_camara = request.json
        if not datos_camara:
            return jsonify({'error': 'No se proporcionaron datos de la cámara'}), 400
        
        # Validar datos requeridos
        campos_requeridos = ['nombre', 'local', 'tipo_camara', 'fuente']
        for campo in campos_requeridos:
            if campo not in datos_camara:
                return jsonify({'error': f'Falta el campo requerido: {campo}'}), 400
        
        # Registrar la nueva cámara - esto verificará todas las cámaras automáticamente
        nueva_camara_id = registrar_camara(datos_camara)
        if nueva_camara_id:
            return jsonify({
                'mensaje': 'Cámara registrada exitosamente',
                'id': nueva_camara_id
            }), 201
        else:
            return jsonify({'error': 'Error al registrar la cámara'}), 500
            
    except Exception as e:
        logger.error(f"Error al registrar nueva cámara: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/camaras/verificar', methods=['POST'])
def verificar_todas_camaras():
    """Endpoint para verificar manualmente todas las cámaras"""
    try:
        verificar_camaras()
        return jsonify({'mensaje': 'Verificación de cámaras iniciada correctamente'}), 200
    except Exception as e:
        logger.error(f"Error al verificar cámaras: {str(e)}")
        return jsonify({'error': 'Error al verificar cámaras'}), 500


if __name__ == "__main__":
    try:
        print("Sirviendo desde:", BASE_DIR)
        logger.info("Iniciando servidor FaceGuard con monitoreo de cámaras")
        webbrowser.open_new("http://localhost:5000/login.html")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {str(e)}")
    finally:
        cleanup()
