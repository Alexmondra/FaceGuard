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

def detect_faces(image):
    boxes, _ = mtcnn.detect(image)
    return [image.crop(list(map(int, box))) for box in boxes] if boxes is not None else []

def generar_embedding(face_image):
    face_tensor = transform_facenet(face_image).unsqueeze(0)
    with torch.no_grad():
        return facenet(face_tensor).squeeze().numpy()
