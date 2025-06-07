import cv2
import base64
import io
import numpy as np
from PIL import Image
from flask_socketio import SocketIO, emit
import threading
from flask import request, jsonify
from utils import detect_faces, generar_embedding, mtcnn
from conexiondb import faiss_index, indice_persona_id
from registros import obtener_datos_persona


def reconocer():
    """Recognize faces in an uploaded image."""
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró ningún archivo"}), 400

    img = Image.open(io.BytesIO(request.files['file'].read())).convert('RGB')
    img_cv = np.array(img) 
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
                    nombre = datos["nombres"]
                    dni = datos["dni"]

            resultados.append({
                "rostro": i + 1,
                "persona_id": persona_id,
                "nombre": nombre,
                "dni": dni,
                "confianza": confianza
            })

            # Draw rectangle and text on the image
            color = (0, 255, 0) if persona_id else (0, 0, 255)  # Green if recognized, Red if not
            cv2.rectangle(draw, (x1, y1), (x2, y2), color, 2)
            cv2.putText(draw, f"{i+1}. {nombre} ({confianza}%)", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

    # Convert the processed image to base64 format
    _, img_encoded = cv2.imencode('.jpg', draw)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')

    return jsonify({"resultados": resultados, "imagen": img_base64})

