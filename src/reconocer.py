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
from reconocidos import guardarReconocido


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



def dibujar_resultados(frame, recognition_data):
    """Dibuja los resultados guardados en el frame"""
    for (x1, y1, x2, y2), nombre, color in zip(recognition_data['boxes'], 
                                            recognition_data['names'], 
                                            recognition_data['colors']):
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, nombre, (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return frame

def procesar_frame(frame, camara_id):
    try:
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        boxes, _ = mtcnn.detect(img_pil)
        
        if boxes is None:
            return frame, {
                'boxes': [],
                'names': [],
                'colors': [],
                'expire_count': 0
            }
        
        rostros = [img_pil.crop(list(map(int, box))) for box in boxes]
        names = []
        colors = []
        boxes_to_draw = []
        
        embeddings = []
        for rostro in rostros:
            try:
                embedding = transform_facenet(rostro).unsqueeze(0)
                with torch.no_grad():
                    embedding = facenet(embedding).squeeze().numpy()
                embeddings.append(embedding)
            except:
                embeddings.append(None)
        
        # Procesar reconocimiento para cada rostro
        for i, (box, embedding) in enumerate(zip(boxes, embeddings)):
            x1, y1, x2, y2 = map(int, box)
            color = (0, 0, 255)  # Rojo por defecto (desconocido)
            nombre = "Desconocido"
            
            if embedding is not None and faiss_index is not None:
                distancias, indices = faiss_index.search(
                    np.array(embedding, dtype=np.float32).reshape(1, -1), 1)
                
                if indices[0][0] != -1:
                    distancia = distancias[0][0]
                    confianza = round((1 - distancia) * 100, 2)
                    
                    if confianza >= 70:
                        persona_id = int(indices[0][0])
                        datos = obtener_datos_persona(persona_id)
                        guardarReconocido(frame,persona_id,camara_id)
                        nombre = datos["nombres"]
                        color = (0, 255, 0)  # Verde si es reconocido
            
            names.append(nombre)
            colors.append(color)
            boxes_to_draw.append([x1, y1, x2, y2])
            
            # Dibujar en el frame
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, nombre, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame, {
            'boxes': boxes_to_draw,
            'names': names,
            'colors': colors,
            'expire_count': 5  # Inicializar contador de expiración
        }
    
    except Exception as e:
        return frame, {
            'boxes': [],
            'names': [],
            'colors': [],
            'expire_count': 0
        }