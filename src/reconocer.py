import cv2
import base64
import io
import numpy as np
from PIL import Image
from flask import request, jsonify
from utils import detect_faces, generar_embedding, mtcnn,transform_facenet, facenet
from conexiondb import faiss_index
from registros import obtener_datos_persona
import torch

def reconocer():
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
    umbral_confianza = 70  # Puedes hacer esto configurable

    if boxes is not None:
        for i, (box, rostro) in enumerate(zip(boxes, rostros)):
            x1, y1, x2, y2 = map(int, box)
            embedding = generar_embedding(rostro)

            if embedding is None:
                continue

            # Búsqueda en FAISS
            distancias, indices = faiss_index.search(
                np.array(embedding, dtype=np.float32).reshape(1, -1), 1)
            
            persona_id, nombre, dni, confianza = None, "Desconocido", "-", 0

            if indices[0][0] != -1:  # Si se encontró un match
                distancia = distancias[0][0]
                confianza = round((1 - distancia) * 100, 2)
                
                if confianza >= umbral_confianza:
                    # Obtener directamente el ID de persona desde FAISS
                    persona_id = int(indices[0][0])  # FAISS ya almacena los IDs reales
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

            # Dibujar rectángulo y texto
            color = (0, 255, 0) if persona_id else (0, 0, 255)
            cv2.rectangle(draw, (x1, y1), (x2, y2), color, 2)
            cv2.putText(draw, f"{i+1}. {nombre} ({confianza}%)", (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

    # Convertir imagen procesada a base64
    _, img_encoded = cv2.imencode('.jpg', draw)
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')

    return jsonify({"resultados": resultados, "imagen": img_base64})




def procesar_frame(frame, reconocimiento_activo=False):
    print(f"Reconocimiento activo: {reconocimiento_activo}")  # Debug
    last_boxes = []
    last_names = []
    last_colors = []
    last_asistencia_msgs = []
    umbral_actual = 70
    
    if not reconocimiento_activo:
        return frame, {}  # Retorno temprano si no hay reconocimient
    if reconocimiento_activo:
        print("Procesando frame para reconocimiento...")  # Debug
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        boxes, _ = mtcnn.detect(img_pil)
        rostros = [img_pil.crop(list(map(int, box))) for box in boxes] if boxes is not None else []
        
        if boxes is not None:
            for i, (box, rostro) in enumerate(zip(boxes, rostros)):
                x1, y1, x2, y2 = map(int, box)
                embedding = transform_facenet(rostro).unsqueeze(0)
                with torch.no_grad():
                    embedding = facenet(embedding).squeeze().numpy()

                color = (0, 0, 255)
                nombre = "Desconocido"
                asistencia_msg = ""

                if faiss_index is not None:
                    distancias, indices = faiss_index.search(
                        np.array(embedding, dtype=np.float32).reshape(1, -1), 1)
                    if indices[0][0] != -1:
                        distancia = distancias[0][0]
                        confianza = round((1 - distancia) * 100, 2)
                        if confianza >= umbral_actual:
                            persona_id = int(indices[0][0])
                            datos = obtener_datos_persona(persona_id)
                            nombre = datos["nombres"]
                            color = (0, 255, 0)
                            
                last_boxes.append((x1, y1, x2, y2))
                last_names.append(nombre)
                last_colors.append(color)
                last_asistencia_msgs.append(asistencia_msg)

        # Dibujar resultados en el frame
        for (x1, y1, x2, y2), nombre, color, msg in zip(last_boxes, last_names, last_colors, last_asistencia_msgs):
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            if msg:
                cv2.putText(frame, nombre, (x1, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
                azul_claro = (180, 220, 255)
                cv2.putText(frame, msg, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, azul_claro, 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, nombre, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
    
    return frame, {
        'boxes': last_boxes,
        'names': last_names,
        'colors': last_colors,
    }
