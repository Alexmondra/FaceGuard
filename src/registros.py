from flask import Blueprint, jsonify, request, send_from_directory
from conexiondb import conectar_db, faiss_index, indice_persona_id
from utils import detect_faces, generar_embedding
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


def obtener_datos_persona(persona_id):
    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT nombre, dni FROM personas WHERE id = %s", (persona_id,))
    datos = cursor.fetchone()
    conexion.close()
    print(f"Datos recuperados para ID {persona_id}: {datos}") 
    return datos

# Verificar DNI
@rutas_personas.route('/verificar_dni', methods=['GET'])
def verificar_dni():
    try:
        dni = request.args.get('dni')
        if not dni:
            return "false", 400
        conexion = conectar_db()
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT 1 FROM personas WHERE dni = %s", (dni,))
            persona = cursor.fetchone()

        conexion.close()
        if persona:
            return "true", 200 
        else:
            return "false", 200 

    except Exception as e:
        print(f"Error en /verificar_dni: {e}")
        return "false", 500


@rutas_personas.route("/agregar_persona", methods=["POST"])
@jwt_required()
def agregar_persona():
    try:
        nombre = request.form.get("nombre", "").strip()
        apellido = request.form.get("apellido", "").strip()
        dni = request.form.get("dni", "").strip()
        imagenes = request.files.getlist("imagenes[]")

        # Validaciones
        if not nombre or not apellido or not dni:
            return jsonify({"error": "DNI, nombre y apellido son obligatorios"}), 400
        if len(imagenes) == 0:
            return jsonify({"error": "Debe subir al menos una imagen"}), 400
        if len(imagenes) > 10:
            return jsonify({"error": "Máximo 10 imágenes"}), 400

        conexion = conectar_db()
        cursor = conexion.cursor()
        # Verificar que el DNI no esté repetido
        cursor.execute("SELECT id FROM personas WHERE dni = %s", (dni,))
        if cursor.fetchone():
            return jsonify({"error": "El DNI ya está registrado"}), 400

        cursor.execute(
            "INSERT INTO personas (dni, nombres, apellidos, fecha_registro) VALUES (%s, %s, %s, NOW())",
            (dni, nombre, apellido),
        )
        persona_id = cursor.lastrowid

        conexion.commit()
        # Crear carpeta para almacenar imágenes
        base_path = os.path.dirname(os.path.abspath(__file__))
        carpeta_dni = os.path.join(base_path, 'imagenes_personas', dni)
        os.makedirs(carpeta_dni, exist_ok=True)

        # Procesar y guardar imágenes localmente y en BD
        from hashlib import sha256
        imagenes_rutas = []
        embeddings = []
        for img in imagenes:
            try:
                img_pil = Image.open(img.stream).convert("RGB")
                nombre_hash = sha256(img_pil.tobytes()).hexdigest()
                ruta_imagen = os.path.join(carpeta_dni, f"{nombre_hash}.jpg")
                if not os.path.exists(ruta_imagen):
                    img_pil.save(ruta_imagen)
                    imagenes_rutas.append(ruta_imagen)
                    # Detectar rostros y generar embeddings
                    for rostro in detect_faces(img_pil):
                        embeddings.append((ruta_imagen, generar_embedding(rostro)))
            except Exception as img_err:
                print(f"Error procesando imagen: {img_err}")

        # Guardar embeddings en la base de datos
        for ruta_imagen, embedding in embeddings:
            cursor.execute(
                """INSERT INTO embeddings_personas (persona_id, embedding, tipo, descripcion, imagen_ruta)
                   VALUES (%s, %s, %s, %s, %s)""",
                (persona_id, pickle.dumps(embedding), 'nuevo', 'Embedding generado desde imagen subida', ruta_imagen)
            )
            # Actualizar FAISS index
            faiss_index.add(np.array(embedding, dtype=np.float32).reshape(1, -1))
            indice_persona_id[faiss_index.ntotal - 1] = int(persona_id)

        conexion.commit()
        conexion.close()
        return jsonify({"mensaje": "Persona creada exitosamente", "persona_id": persona_id}), 200

    except Exception as e:
        print(f"Error en /agregar_persona: {e}")
        if "conexion" in locals():
            conexion.rollback()
            conexion.close()
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500


@rutas_personas.route('/agregar_imagenes', methods=['POST'])
@jwt_required()
def agregar_imagenes():
    try:
        # Validar datos obligatorios
        persona_id = request.form.get('persona_id')
        imagenes = request.files.getlist('imagenes[]')

        if not persona_id or not imagenes:
            return jsonify({"error": "ID de persona e imágenes son obligatorios"}), 400

        # Determinar carpeta de la persona (asumiendo que ya existe)
        import os
        from hashlib import sha256
        conexion = conectar_db()
        with conexion.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT dni FROM personas WHERE id = %s", (persona_id,))
            persona = cursor.fetchone()

        dni = persona['dni']
        carpeta_dni = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'imagenes_personas', dni)

        # Procesar y guardar nuevas imágenes
        imagenes_rutas = []
        embeddings = []

        for img in imagenes:
            img_pil = Image.open(img.stream).convert('RGB')
            nombre_hash = sha256(img_pil.tobytes()).hexdigest()
            ruta_imagen = os.path.join(carpeta_dni, f"{nombre_hash}.jpg")

            if not os.path.exists(ruta_imagen):
                img_pil.save(ruta_imagen)
                imagenes_rutas.append(ruta_imagen)

                # Detectar rostros y generar embeddings
                for rostro in detect_faces(img_pil):
                    embeddings.append(generar_embedding(rostro))

        # Guardar embeddings en la base de datos
        with conexion.cursor() as cursor:
            for embedding, ruta_imagen in zip(embeddings, imagenes_rutas):
                cursor.execute("""
                    INSERT INTO embeddings_personas (persona_id, embedding, tipo, descripcion, imagen_ruta)
                    VALUES (%s, %s, %s, %s, %s)
                """, (persona_id, pickle.dumps(embedding), 'nuevo', 'Embedding generado desde imagen subida', ruta_imagen))

        # Actualizar FAISS con los nuevos embeddings
        for embedding in embeddings:
            faiss_index.add(np.array(embedding, dtype=np.float32).reshape(1, -1))
            indice_persona_id[faiss_index.ntotal - 1] = int(persona_id)

        conexion.commit()
        conexion.close()

        return jsonify({"mensaje": "Imágenes agregadas exitosamente", "imagenes_rutas": imagenes_rutas}), 200

    except Exception as e:
        print(f"Error en /agregar_imagenes: {e}")
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500

## obtener personas :: 

@rutas_personas.route('/obtener_personas', methods=['GET'])
def obtener_personas():
    try:
        # Conectar a la base de datos
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)

        # Consulta para obtener personas y sus imágenes
        cursor.execute("""
            SELECT p.id AS persona_id, p.nombres AS nombre, p.apellidos AS apellido, p.dni, e.imagen_ruta 
            FROM personas p
            LEFT JOIN embeddings_personas e ON p.id = e.persona_id
            ORDER BY p.id
        """)

        # Organizar los resultados
        registros = {}
        for fila in cursor.fetchall():
            persona_id = fila['persona_id']
            if persona_id not in registros:
                registros[persona_id] = {
                    "id": persona_id,
                    "nombre": fila['nombre'],
                    "apellido": fila.get('apellido', ''),   # <--- Agregado siempre
                    "dni": fila['dni'],
                    "imagenes": []
                }
            if fila['imagen_ruta']:
                # Generar una ruta accesible para el frontend
                imagen_ruta_relativa = os.path.relpath(fila['imagen_ruta'], IMAGES_DIR)
                registros[persona_id]['imagenes'].append(f"/imagenes/{imagen_ruta_relativa}")

        # Cerrar la conexión
        conexion.close()

        # Convertir los datos en una lista para la respuesta
        resultado = list(registros.values())
        return jsonify({"personas": resultado}), 200

    except Exception as e:
        # Log detallado para depuración
        print(f"Error en /obtener_personas: {e}")
        return jsonify({"error": f"Error al obtener los datos: {str(e)}"}), 500

# Ruta para servir imágenes desde el directorio configurado
@rutas_personas.route('/imagenes/<path:filename>')
def servir_imagenes(filename):
    try:
        return send_from_directory(IMAGES_DIR, filename)
    except Exception as e:
        print(f"Error al servir imagen: {e}")
        return jsonify({"error": "Imagen no encontrada"}), 404



#editar personas datos 

@rutas_personas.route('/editar_persona/<int:persona_id>', methods=['POST'])
@jwt_required()
def editar_persona(persona_id):
    conexion = None
    try:
        dni = request.form.get('dni', '').strip()
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        imagenes = request.files.getlist('imagenes[]')
        imagenes_eliminar = request.form.getlist('imagenes_eliminar[]')

        # Validación robusta
        if not dni or not nombre or not apellido:
            return jsonify({"error": "DNI, nombre y apellido son obligatorios"}), 400

        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)

        with conexion.cursor() as cursor:
            # Verifica persona existe y recupera dni actual
            cursor.execute("SELECT dni FROM personas WHERE id = %s", (persona_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": "Persona no encontrada"}), 404
            current_dni = result[0]

            # Si cambia el DNI, verificar no exista duplicado
            if dni != current_dni:
                cursor.execute("SELECT id FROM personas WHERE dni = %s AND id != %s", (dni, persona_id))
                if cursor.fetchone():
                    return jsonify({"error": "El nuevo DNI ya está registrado"}), 400

            # Actualiza los datos principales
            cursor.execute(
                "UPDATE personas SET dni = %s, nombres = %s, apellidos = %s, fecha_actualizacion = NOW() WHERE id = %s",
                (dni, nombre, apellido, persona_id)
            )

            # === Eliminar imágenes ===
            # (imagenes_eliminar contiene hashes o nombres, por convención hash del jpg)
            if imagenes_eliminar:
                for imagen_hash in imagenes_eliminar:
                    # Buscar rutas de imagen coincidiendo por hash
                    cursor.execute(
                        "SELECT imagen_ruta, embedding FROM embeddings_personas WHERE persona_id = %s AND imagen_ruta LIKE %s",
                        (persona_id, f"%{imagen_hash}%"))
                    for result_img in cursor.fetchall():
                        ruta_imagen, embedding = result_img
                        # Quitar de la base
                        cursor.execute(
                            "DELETE FROM embeddings_personas WHERE persona_id = %s AND imagen_ruta = %s",
                            (persona_id, ruta_imagen))
                        # Borrar archivo físico
                        if os.path.exists(ruta_imagen):
                            try:
                                os.remove(ruta_imagen)
                            except Exception as img_rm_err:
                                print(f"Error eliminando imagen: {img_rm_err}")
                        # Quitar embedding de FAISS (simplificado, lo recomendable sería reconstruir faiss offline periódicamente)
                        if embedding:
                            embedding_array = pickle.loads(embedding)
                            search_embedding = np.array(embedding_array, dtype=np.float32).reshape(1, -1)
                            _, indices = faiss_index.search(search_embedding, 1)
                            if indices.size > 0:
                                faiss_index.remove_ids(np.array([indices[0][0]]))

            # === Agregar nuevas imágenes ===
            if imagenes:
                carpeta_dni = os.path.join(IMAGES_DIR, dni)
                os.makedirs(carpeta_dni, exist_ok=True)
                # Leer hashes ya existentes para la persona (evitar duplicados)
                cursor.execute("SELECT imagen_ruta FROM embeddings_personas WHERE persona_id = %s", (persona_id,))
                rutas_existentes = [row[0] for row in cursor.fetchall() if row[0]]
                hashes_existentes = set()
                for ruta in rutas_existentes:
                    m = os.path.basename(ruta)
                    if m.endswith('.jpg'):
                        hashes_existentes.add(m[:-4])  # sin .jpg

                for img in imagenes:
                    try:
                        img_pil = Image.open(img.stream).convert("RGB")
                        nombre_hash = sha256(img_pil.tobytes()).hexdigest()
                        if nombre_hash in hashes_existentes:
                            print(f"Saltando imagen duplicada {nombre_hash}")
                            continue  # No guardar duplicado en BD ni disco
                        ruta_imagen = os.path.join(carpeta_dni, f"{nombre_hash}.jpg")
                        img_pil.save(ruta_imagen)
                        # Generar embeddings y guardar
                        faces = detect_faces(img_pil)
                        for face in faces:
                            embedding = generar_embedding(face)
                            cursor.execute(
                                """INSERT INTO embeddings_personas (persona_id, embedding, tipo, descripcion, imagen_ruta)
                                   VALUES (%s, %s, %s, %s, %s)""",
                                (persona_id, pickle.dumps(embedding), 'nuevo', 'Embedding from edit', ruta_imagen)
                            )
                            faiss_index.add(np.array(embedding, dtype=np.float32).reshape(1, -1))
                            indice_persona_id[faiss_index.ntotal - 1] = int(persona_id)
                    except Exception as e:
                        print(f"Error procesando imagen en edición: {e}")
                        continue

        conexion.commit()
        return jsonify({"mensaje": "Persona actualizada exitosamente"}), 200

    except Exception as e:
        if conexion:
            conexion.rollback()
        print(f"Error en /editar_persona: {e}")
        return jsonify({"error": f"Error procesando la solicitud: {str(e)}"}), 500
    finally:
        if conexion:
            conexion.close()


@rutas_personas.route("/eliminar_persona/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar_persona(id):
    conexion = None
    try:
        conexion = conectar_db()
        with conexion.cursor() as cursor:
            # Buscar datos clave y dni
            cursor.execute("SELECT dni FROM personas WHERE id = %s", (id,))
            result = cursor.fetchone()
            if not result:
                if conexion: conexion.close()
                return jsonify({"error": "Persona no encontrada"}), 404
            dni = result[0]

            # Obtener y borrar imágenes asociadas
            cursor.execute("SELECT imagen_ruta FROM embeddings_personas WHERE persona_id = %s", (id,))
            imagen_rutas = [row[0] for row in cursor.fetchall()]
            for ruta in imagen_rutas:
                if ruta and os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except Exception as ex:
                        print(f"Error eliminando archivo: {ex}")

            cursor.execute("DELETE FROM embeddings_personas WHERE persona_id = %s", (id,))
            cursor.execute("DELETE FROM asistencias WHERE persona_id = %s", (id,))
            cursor.execute("DELETE FROM horarios WHERE persona_id = %s", (id,))
            cursor.execute("DELETE FROM personas WHERE id = %s", (id,))

            # Borrar carpeta
            carpeta_dni = os.path.join(IMAGES_DIR, dni)
            if carpeta_dni and os.path.exists(carpeta_dni):
                import shutil
                shutil.rmtree(carpeta_dni)

            conexion.commit()
        conexion.close()
        return jsonify({"success": True, "mensaje": "Persona eliminada exitosamente"}), 200

    except Exception as e:
        print(f"Error en eliminar_persona: {e}")
        if conexion:
            conexion.rollback()
            conexion.close()
        return jsonify({"error": f"Error al eliminar: {str(e)}"}), 500
