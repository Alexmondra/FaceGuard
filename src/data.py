from PIL import ImageEnhance, ImageOps
import random

# Aplicar data augmentation con descripciones específicas






def aplicar_aumentaciones(img_pil):
    aumentaciones = []
    try:
        aumentaciones.append(("original", img_pil))  # Original

        # Contraste
        try:
            aumentaciones.append(("contraste", ImageEnhance.Contrast(img_pil).enhance(1.5)))
        except Exception as e:
            print(f"Error en contraste: {e}")

        # Brillo
        try:
            aumentaciones.append(("brillo", ImageEnhance.Brightness(img_pil).enhance(1.5)))
        except Exception as e:
            print(f"Error en brillo: {e}")

        # Rotación
        try:
            aumentaciones.append(("rotacion (x=15º)", img_pil.rotate(random.uniform(-15, 15), expand=True)))
        except Exception as e:
            print(f"Error en rotación: {e}")

        # Flip horizontal
        try:
            aumentaciones.append(("flip_horizontal", ImageOps.mirror(img_pil)))
        except Exception as e:
            print(f"Error en flip horizontal: {e}")

        # Nitidez
        try:
            aumentaciones.append(("nitidez", ImageEnhance.Sharpness(img_pil).enhance(2.0)))
        except Exception as e:
            print(f"Error en nitidez: {e}")

    except Exception as e:
        print(f"Error general en aplicar_aumentaciones: {e}")

    return aumentaciones
