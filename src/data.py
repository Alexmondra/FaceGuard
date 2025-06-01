from PIL import ImageEnhance, ImageOps
import random

# Aplicar data augmentation con descripciones específicas

def aplicar_aumentaciones(img_pil):
    aumentaciones = [
        ("original", img_pil),  # Original
        ("contraste", ImageEnhance.Contrast(img_pil).enhance(1.5)),  # Increased contrast
        ("brillo", ImageEnhance.Brightness(img_pil).enhance(1.5)),  # Increased brightness
        ("rotacion (x=15º)", img_pil.rotate(random.uniform(-15, 15), expand=True)),  # Z-rotation 15º
        ("flip_horizontal", ImageOps.mirror(img_pil)),  # Horizontal flip
        ("nitidez", ImageEnhance.Sharpness(img_pil).enhance(2.0))  # Increased sharpness
    ]
    return aumentaciones


