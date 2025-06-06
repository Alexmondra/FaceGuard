from torchvision import transforms
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from flask_socketio import SocketIO
from flask_jwt_extended import JWTManager

# Inicializar modelos de detección y reconocimiento facial
mtcnn = MTCNN(keep_all=True)
facenet = InceptionResnetV1(pretrained='vggface2').eval()

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
jwt = JWTManager()

# Transformaciones para imágenes antes de FaceNet
transform_facenet = transforms.Compose([
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])


def detect_principal_face(image):
    try:
        boxes, _ = mtcnn.detect(image)
        if boxes is None or len(boxes) == 0:
            print("No se detectó ningún rostro en la imagen.")
            return []  
        areas = [(box[2] - box[0]) * (box[3] - box[1]) for box in boxes]
        max_idx = areas.index(max(areas))  
        principal_box = boxes[max_idx]
        print(f"Rostro detectado con coordenadas: {principal_box}")
        return [image.crop(list(map(int, principal_box)))]
    except Exception as e:
        print(f"Error en la detección de caras: {e}")
        return []

def detect_faces(image):
    boxes, _ = mtcnn.detect(image)
    return [image.crop(list(map(int, box))) for box in boxes] if boxes is not None else []

def generar_embedding(face_image):
    face_tensor = transform_facenet(face_image).unsqueeze(0)
    with torch.no_grad():
        return facenet(face_tensor).squeeze().numpy()
