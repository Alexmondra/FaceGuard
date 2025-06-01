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

# Crear carpeta para la persona
def crear_carpeta_persona(dni):
    base_path = os.path.dirname(os.path.abspath(__file__))
    carpeta_dni = os.path.join(base_path, 'imagenes_personas', dni)
    os.makedirs(carpeta_dni, exist_ok=True)
    return carpeta_dni

# Guardar imágenes y embeddings
def procesar_imagenes(cursor, persona_id, carpeta_dni, imagenes):
    for img in imagenes:
        ruta_imagen_original = None 

        try:
            # Convertir la imagen a RGB
            img_pil = Image.open(img.stream).convert("RGB")
            # Aplicar aumentaciones
            aumentadas = aplicar_aumentaciones(img_pil)

            embeddings = []
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

                    # Guardar el embedding con descripción y ruta solo para la original
                    ruta_guardada = ruta_imagen_original if tipo == "original" else None
                    embeddings.append((embedding, tipo, ruta_guardada))

            # Guardar embeddings en la base de datos
            for embedding, tipo, ruta_imagen in embeddings:
                cursor.execute("""
                    INSERT INTO embeddings_personas (persona_id, embedding, descripcion, imagen_ruta)
                    VALUES (%s, %s, %s, %s)
                """, (persona_id, pickle.dumps(embedding), tipo, ruta_imagen))

        except Exception as img_err:
            print(f"Error procesando imagen: {img_err}")

# Ruta para agregar persona
@rutas_personas.route("/agregar_persona", methods=["POST"])
@jwt_required()
def agregar_persona():
    try:
        # Datos básicos de la persona
        dni = request.form.get("dni", "").strip()
        nombres = request.form.get("nombres", "").strip()
        apellidos = request.form.get("apellidos", "").strip()
        fecha_nacimiento = request.form.get("fecha_nacimiento", "").strip()
        genero = request.form.get("genero", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        imagenes = request.files.getlist("imagenes[]")

        # Validaciones
        if not dni:
            return jsonify({"error": "DNI es obligatorio"}), 400
        if len(genero) != 1:
            return jsonify({"error": "El género debe ser un carácter (M/F)"}), 400
        if len(imagenes) == 0:
            return jsonify({"error": "Debe subir al menos una imagen"}), 400

        conexion = conectar_db()
        cursor = conexion.cursor()

        # Verificar que el DNI no esté repetido
        cursor.execute("SELECT id FROM personas WHERE dni = %s", (dni,))
        if cursor.fetchone():
            return jsonify({"error": "El DNI ya está registrado"}), 400

        # Insertar persona en la base de datos
        cursor.execute("""
            INSERT INTO personas (dni, nombres, apellidos, fecha_nacimiento, genero, descripcion, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (dni, nombres, apellidos, fecha_nacimiento or None, genero, descripcion))
        persona_id = cursor.lastrowid

        # Crear carpeta para imágenes
        carpeta_dni = crear_carpeta_persona(dni)

        # Procesar imágenes
        procesar_imagenes(cursor, persona_id, carpeta_dni, imagenes)

        conexion.commit()
        conexion.close()

        return jsonify({"mensaje": "Persona creada exitosamente", "persona_id": persona_id}), 200

    except Exception as e:
        print(f"Error en /agregar_persona: {e}")
        if "conexion" in locals():
            conexion.rollback()
            conexion.close()
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500

## obtener personas :: 

def get_all_personas_with_images():

    try:
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)

        # Consulta para obtener todas las personas
        cursor.execute("""
            SELECT p.id AS persona_id, p.dni, p.nombres, p.apellidos, p.fecha_nacimiento, 
                   p.genero, p.descripcion, p.fecha_registro
            FROM personas p
        """)
        personas = cursor.fetchall()

        # Consulta para obtener las rutas de imágenes originales de cada persona
        cursor.execute("""
            SELECT e.persona_id, e.imagen_ruta
            FROM embeddings_personas e
            WHERE e.descripcion = 'original'
        """)
        imagenes = cursor.fetchall()

        # Indexar imágenes por persona_id para unir datos fácilmente
        imagenes_por_persona = {}
        for imagen in imagenes:
            persona_id = imagen['persona_id']
            ruta = imagen['imagen_ruta']
            if persona_id not in imagenes_por_persona:
                imagenes_por_persona[persona_id] = []
            imagenes_por_persona[persona_id].append(ruta)

        # Agregar las imágenes originales a cada persona
        for persona in personas:
            persona_id = persona['persona_id']
            persona['imagenes_originales'] = imagenes_por_persona.get(persona_id, [])

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
    """Endpoint para obtener todas las personas y sus imágenes."""
    try:
        resultado = get_all_personas_with_images()
        return jsonify({"personas": resultado}), 200
    except Exception as e:
        print(f"Error en /obtener_personas: {e}")
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500
