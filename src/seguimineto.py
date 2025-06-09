import cv2
from ultralytics import YOLO
from collections import defaultdict
import numpy as np


personas_registradas = {}  
ultimo_id = 0
max_distancia_seguimiento = 150  
historial_longitud = 10  

def inicializar_modelo_yolo():
    model = YOLO('../models/yolov8n.pt')
    return model

def detectar_personas_con_yolo(frame, model):
    results = model(frame, stream=True, classes=[0], verbose=False)  # Solo personas (clase 0)
    personas = []
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            
            if conf >= 0.5:  # Filtro de confianza
                personas.append({
                    'box': [x1, y1, x2, y2],
                    'centro': ((x1+x2)//2, (y1+y2)//2),
                    'confianza': conf
                })
    
    return personas

def calcular_distancia(punto1, punto2):
    """Calcula la distancia euclidiana entre dos puntos"""
    return np.linalg.norm(np.array(punto1) - np.array(punto2))

def asociar_rostros_con_personas(rostros_reconocidos, yolo_detections):

    personas_a_seguir = []
    
    for rostro in rostros_reconocidos:
        mejor_persona = None
        mejor_distancia = float('inf')
        rx1, ry1, rx2, ry2 = rostro['box']
        centro_rostro = ((rx1+rx2)//2, (ry1+ry2)//2)
        
        for persona in yolo_detections:
            distancia = calcular_distancia(centro_rostro, persona['centro'])
            if distancia < max_distancia_seguimiento and distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_persona = persona
        
        if mejor_persona is not None:
            personas_a_seguir.append({
                'nombre': rostro['nombre'],
                'box_persona': mejor_persona['box'],
                'box_rostro': rostro['box'],
                'confianza': mejor_persona['confianza'],
                'centro': mejor_persona['centro']
            })
    
    return personas_a_seguir

def dibujar_seguimiento(frame, personas_a_seguir):
    for persona in personas_a_seguir:
        # Dibujar bounding box de persona
        x1, y1, x2, y2 = persona['box_persona']
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        
        # Dibujar nombre
        texto = f"{persona['nombre']}"
        cv2.putText(frame, texto, (x1, y1 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    return frame