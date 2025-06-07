from facenet_pytorch import InceptionResnetV1
import torch
from PIL import Image
import numpy as np
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# Cargar la imagen
img_path = "/home/alex/workspace/ING. JCA/prueba/87de3c84-5489-4936-80da-36d13be190e2.jpeg"
img = Image.open(img_path)

# Preprocesamiento
transform = transforms.Compose([
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])

img_tensor = transform(img).unsqueeze(0)  # Añadir batch

# Cargar modelo
model = InceptionResnetV1(pretrained='vggface2').eval()

# Obtener embedding
with torch.no_grad():
    embedding = model(img_tensor).numpy().flatten()

# Crear figura general
fig = plt.figure(figsize=(16, 7))

# Crear un GridSpec con 1 fila y 2 columnas: izquierda (imagen), derecha (gráfica + texto)
gs = GridSpec(1, 2, width_ratios=[1, 2], figure=fig)

# Subplot imagen a la izquierda
ax_img = fig.add_subplot(gs[0, 0])
ax_img.imshow(img)
ax_img.axis('off')
ax_img.set_title("Imagen Original")

# GridSpec anidado para la columna derecha (gráfica arriba, texto abajo)
gs_right = GridSpec(2, 1, height_ratios=[4, 1], figure=fig, 
                    left=0.55, right=0.95, bottom=0.1, top=0.9, hspace=0.5)

# Subplot gráfica en la parte superior derecha
ax_plot = fig.add_subplot(gs_right[0, 0])
ax_plot.plot(embedding, marker='o', linestyle='-', markersize=3)
ax_plot.set_title("Gráfica de los Embeddings")
ax_plot.set_xlabel("Índice del Valor")
ax_plot.set_ylabel("Valor")
ax_plot.grid()

# Subplot texto debajo de la gráfica (array)
ax_text = fig.add_subplot(gs_right[1, 0])

# Formatear parte del array para mostrar (primeros 50 valores)
array_text = np.array2string(embedding[:50], precision=3, separator=', ') + " ... (total 512 valores)"

ax_text.text(0, 0.5, array_text, fontsize=10, family='monospace')
ax_text.axis('off')

plt.show()
