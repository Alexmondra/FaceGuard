from flask import Blueprint, jsonify, request, send_from_directory
from conexiondb import conectar_db, faiss_index, indice_persona_id
from utils import generar_embedding , detect_principal_face
from data import aplicar_aumentaciones
import os
from PIL import Image
from hashlib import sha256
import pickle
import numpy as np
import faiss
import requests
from flask_jwt_extended import jwt_required, get_jwt_identity
# Crear un Blueprint

rutas_personas = Blueprint('rutas_personas', __name__)
# Configuración del directorio de imágenes
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "imagenes_personas")


# devuelve datos de las personas esto es para reconocer

def obtener_datos_persona(persona_id):
    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT nombres, dni FROM personas WHERE id = %s", (persona_id,))
    datos = cursor.fetchone()
    conexion.close()
    print(f"Datos recuperados para ID {persona_id}: {datos}") 
    return datos



# Crear carpeta para la persona
def crear_carpeta_persona(dni):
    base_path = os.path.dirname(os.path.abspath(__file__))
    carpeta_dni = os.path.join(base_path, 'imagenes_personas', dni)
    os.makedirs(carpeta_dni, exist_ok=True)
    return carpeta_dni

# Guardar imágenes y embeddings
def procesar_imagenes(cursor, persona_id, carpeta_dni, imagenes):
    contador_imagenes = 1
    for img in imagenes:
        ruta_imagen_original = None 

        try:
            # Convertir la imagen a RGB
            img_pil = Image.open(img.stream).convert("RGB")

            # Aplicar aumentaciones
            aumentadas = aplicar_aumentaciones(img_pil)
            embeddings = []

            descripcion_imagen = f"{persona_id}-{contador_imagenes}"

            for tipo, img_aumentada in aumentadas:
                # Generar hash único para identificar la imagen
                nombre_hash = sha256(img_aumentada.tobytes()).hexdigest()

                # Guardar la imagen original en el sistema de archivos
                if tipo == "original" and ruta_imagen_original is None:
                    ruta_imagen_original = os.path.join(carpeta_dni, f"{nombre_hash}.jpg")
                    if not os.path.exists(ruta_imagen_original):
                        img_aumentada.save(ruta_imagen_original)  # Guardar solo la original.

                # Detectar rostros y generar embeddings
                for rostro in detect_principal_face(img_aumentada):
                    embedding = generar_embedding(rostro)

                    ruta_guardada = ruta_imagen_original if tipo == "original" else None
                    embeddings.append((embedding, tipo, ruta_guardada))

            # Guardar embeddings en la base de datos
            for embedding, tipo, ruta_imagen in embeddings:
                cursor.execute("""
                    INSERT INTO embeddings_personas (persona_id, embedding, tipo, descripcion, imagen_ruta)
                    VALUES (%s, %s, %s, %s, %s)
                """, (persona_id, pickle.dumps(embedding), tipo, descripcion_imagen, ruta_imagen))

            contador_imagenes += 1

        except Exception as img_err:
            print(f"Error procesando imagen: {img_err}")



@rutas_personas.route("/agregar_persona", methods=["POST"])
@jwt_required()
def agregar_persona():
    conexion = None
    try:
        dni = request.form.get("idNumber", "").strip()
        nombres = request.form.get("fullName", "").strip()
        apellidos = request.form.get("lastName", "").strip()
        fecha_nacimiento = request.form.get("idFecha", "").strip()
        genero = request.form.get("idSexo", "").strip()
        descripcion = request.form.get("physicDescription", "").strip()
        imagenes = request.files.getlist("photos")

        if not dni:
            return jsonify({"error": "DNI es obligatorio"}), 400
        if len(genero) != 1:
            return jsonify({"error": "El género debe ser un carácter (M/F)"}), 400
        if len(imagenes) == 0:
            return jsonify({"error": "Debe subir al menos una imagen"}), 400

        conexion = conectar_db()
        cursor = conexion.cursor()

        cursor.execute("SELECT id FROM personas WHERE dni = %s", (dni,))
        if cursor.fetchone():
            return jsonify({"error": "El DNI ya está registrado"}), 400

        cursor.execute("""
            INSERT INTO personas (dni, nombres, apellidos, fecha_nacimiento, genero, descripcion, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (dni, nombres, apellidos, fecha_nacimiento or None, genero, descripcion))

        persona_id = cursor.lastrowid
        print(f"Persona creada con ID: {persona_id}")

        carpeta_dni = crear_carpeta_persona(dni)

        procesar_imagenes(cursor, persona_id, carpeta_dni, imagenes)

        conexion.commit()
        conexion.close()

        return jsonify({"mensaje": "Persona creada exitosamente", "persona_id": persona_id}), 200

    except Exception as e:
        print(f"Error en /agregar_persona: {e}")
        if conexion:
            conexion.rollback()
            conexion.close()
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500

## obtener personas :: 
 
def get_all_personas_with_images():
    """Obtiene la lista de personas con sus imágenes asociadas."""
    try:
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)

        # Obtener personas
        cursor.execute("""
            SELECT p.id AS persona_id, p.nombres AS nombre, p.apellidos AS apellido, 
                   p.dni, p.fecha_nacimiento, p.genero, p.descripcion, p.fecha_registro
            FROM personas p
        """)
        personas = cursor.fetchall()

        # Obtener imágenes originales (tipo='original')
        cursor.execute("""
            SELECT persona_id, imagen_ruta
            FROM embeddings_personas
            WHERE tipo = 'original'
        """)
        imagenes = cursor.fetchall()

        # Indexar imágenes por persona_id
        imagenes_por_persona = {}
        for img in imagenes:
            persona_id = img['persona_id']
            ruta_absoluta = img['imagen_ruta']

            # Obtener ruta relativa segura
            try:
                ruta_relativa = os.path.relpath(ruta_absoluta, IMAGES_DIR)
            except ValueError:
                # En caso que la ruta no sea relativa a IMAGES_DIR (por ejemplo por ../)
                ruta_relativa = os.path.basename(ruta_absoluta)

            # Formar URL accesible (asegúrate que el frontend use /imagenes/<ruta_relativa>)
            url_imagen = f"/registros/imagenes/{ruta_relativa.replace(os.sep, '/')}"

            if persona_id not in imagenes_por_persona:
                imagenes_por_persona[persona_id] = []
            imagenes_por_persona[persona_id].append(url_imagen)

        # Asignar imágenes a cada persona
        for persona in personas:
            pid = persona['persona_id']
            persona['imagenes_originales'] = imagenes_por_persona.get(pid, [])

        conexion.close()
        return personas

    except Exception as e:
        print(f"Error en get_all_personas_with_images: {e}")
        if "conexion" in locals():
            conexion.close()
        raise


@rutas_personas.route('/obtener_personas', methods=['GET'])
@jwt_required()
def obtener_personas():
    """Endpoint para obtener todas las personas con sus imágenes."""
    try:
        resultado = get_all_personas_with_images()
        return jsonify({"personas": resultado}), 200
    except Exception as e:
        print(f"Error en /obtener_personas: {e}")
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500


@rutas_personas.route('imagenes/<path:filename>')
def servir_imagenes(filename):
    """Sirve imágenes desde el directorio configurado."""
    try:
        ruta_segura = os.path.abspath(os.path.join(IMAGES_DIR, filename))
        if not ruta_segura.startswith(IMAGES_DIR):
            raise ValueError("Acceso denegado a la ruta solicitada.")

        return send_from_directory(IMAGES_DIR, filename)

    except Exception as e:
        print(f"Error al servir imagen: {e}")
        return jsonify({"error": "Imagen no encontrada"}), 404
   
   
#elimanar persona y sus imagenes :: 

@rutas_personas.route("/eliminar/<int:id>", methods=["DELETE"])
def eliminar_persona(id):
    conexion = None
    try:
        conexion = conectar_db()
        with conexion.cursor() as cursor:
            # Buscar datos clave y dni
            cursor.execute("SELECT dni FROM personas WHERE id = %s", (id,))
            result = cursor.fetchone()
            if not result:
                if conexion:
                    conexion.close()
                return jsonify({"error": "Persona no encontrada"}), 404
            dni = result[0]

            # Obtener y borrar imágenes asociadas en embeddings_personas
            cursor.execute("SELECT imagen_ruta FROM embeddings_personas WHERE persona_id = %s", (id,))
            imagen_rutas = [row[0] for row in cursor.fetchall()]
            for ruta in imagen_rutas:
                if ruta and os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except Exception as ex:
                        print(f"Error eliminando archivo: {ex}")

            # Borrar registros relacionados en detectados
            cursor.execute("DELETE FROM detectados WHERE persona_id = %s", (id,))

            # Borrar registros en embeddings_personas (ya borraste las imágenes físicas)
            cursor.execute("DELETE FROM embeddings_personas WHERE persona_id = %s", (id,))

            # Borrar persona
            cursor.execute("DELETE FROM personas WHERE id = %s", (id,))

            # Borrar carpeta física con imágenes de la persona
            carpeta_dni = os.path.join(IMAGES_DIR, dni)
            if carpeta_dni and os.path.exists(carpeta_dni):
                import shutil
                try:
                    shutil.rmtree(carpeta_dni)
                except Exception as ex:
                    print(f"Error eliminando carpeta: {ex}")

            conexion.commit()
        conexion.close()
        return jsonify({"success": True, "mensaje": "Persona eliminada exitosamente"}), 200

    except Exception as e:
        print(f"Error en eliminar_persona: {e}")
        if conexion:
            conexion.rollback()
            conexion.close()
        return jsonify({"error": f"Error al eliminar: {str(e)}"}), 500

