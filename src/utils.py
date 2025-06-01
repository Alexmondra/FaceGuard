from torchvision import transforms
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch

# Inicializar modelos de detección y reconocimiento facial
mtcnn = MTCNN(keep_all=True)
facenet = InceptionResnetV1(pretrained='vggface2').eval()

# Transformaciones para imágenes antes de FaceNet
transform_facenet = transforms.Compose([
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])

def detect_principal_face(image):
    boxes, _ = mtcnn.detect(image)
    if boxes is None or len(boxes) == 0:
        return [] 
    areas = [(box[2] - box[0]) * (box[3] - box[1]) for box in boxes]
    max_idx = areas.index(max(areas))  
    principal_box = boxes[max_idx]
    return [image.crop(list(map(int, principal_box)))] 

def detect_faces(image):
    boxes, _ = mtcnn.detect(image)
    return [image.crop(list(map(int, box))) for box in boxes] if boxes is not None else []

def generar_embedding(face_image):
    face_tensor = transform_facenet(face_image).unsqueeze(0)
    with torch.no_grad():
        return facenet(face_tensor).squeeze().numpy()
