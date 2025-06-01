import os
from flask import Flask, send_from_directory , request, jsonify , abort , render_template
import webbrowser 
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
from conexiondb import conectar_db,crear_tablas_si_no_existen, cargar_embeddings_faiss, faiss_index, indice_persona_id
from registros import rutas_personas
from utils import detect_faces, generar_embedding, mtcnn, facenet, transform_facenet
from camaras import rutas_camaras ,iniciar_monitoreo, detener_monitoreo
from login import auth_bp

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

# Configure JWT
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this in production!
jwt = JWTManager(app)

# Register the auth blueprint
app.register_blueprint(auth_bp)


# Configurar el logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

@app.route('/')
def root():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'auth.html')

@app.route('/sistema')
def sistema():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'menu.html')


@app.route('/<path:filename>')
def serve_html(filename):
    file_path = os.path.join(BASE_DIR, 'templates', filename)
    if os.path.isfile(file_path):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), filename)
    else:
        abort(404)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'js'), filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    file_path = os.path.join(BASE_DIR, 'static', filename)
    if os.path.isfile(file_path):
        return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)
    else:
        abort(404)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)

# Inicializar FAISS cargando embeddings desde la base de datos
cargar_embeddings_faiss()


# Registrar el Blueprint de rutas_camaras - rutas_personas

app.register_blueprint(rutas_camaras, url_prefix='/camara')
app.register_blueprint(rutas_personas, url_prefix='/registros')





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



if __name__ == "__main__":
    try:
        print("Sirviendo desde:", BASE_DIR)
        #webbrowser.open_new("http://localhost:5000/")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {str(e)}")


