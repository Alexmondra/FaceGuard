from flask import Flask, Blueprint, jsonify, request, send_from_directory, current_app
from conexiondb import conectar_db, agregar_embedding_faiss,eliminar_embeddings_faiss
from utils import generar_embedding, detect_principal_face
from data import aplicar_aumentaciones
import os
from PIL import Image
from hashlib import sha256
import pickle
import numpy as np 
from flask_jwt_extended import jwt_required, get_jwt_identity
from multiprocessing import Pool, cpu_count
from io import BytesIO
from functools import partial
from werkzeug.utils import secure_filename
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor
import re
from datetime import datetime

# Crear un Blueprint
rutas_personas = Blueprint('rutas_personas', __name__)

# Configuración del directorio de imágenes (relativa al blueprint)
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imagenes_personas")
MAX_WORKERS = 2  # Ajustar según los núcleos del CPU
processing_queue = queue.Queue()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# --------------------------
# Funciones de apoyo
# --------------------------

def obtener_datos_persona(persona_id):
    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT nombres, dni FROM personas WHERE id = %s", (persona_id,))
    datos = cursor.fetchone()
    conexion.close()
    print(f"Datos recuperados para ID {persona_id}: {datos}") 
    return datos

def crear_carpeta_persona(dni):
    carpeta = os.path.join(IMAGES_DIR, secure_filename(dni))
    if not os.path.exists(carpeta):
        os.makedirs(carpeta, exist_ok=True)
    return carpeta


def guardar_embedding_db(persona_id, embedding, tipo, descripcion, ruta_imagen):
    conexion = conectar_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO embeddings_personas 
                (persona_id, embedding, tipo, descripcion, imagen_ruta)
                VALUES (%s, %s, %s, %s, %s)
            """, (persona_id, pickle.dumps(embedding), tipo, descripcion, ruta_imagen))
        conexion.commit()
        agregar_embedding_faiss(persona_id, embedding)

    finally:
        conexion.close() 


# --------------------------
# Funciones para el worker
# --------------------------

def procesar_imagen_async(img_bytes, persona_id, carpeta_dni, contador_imagenes):
    try:
        img_pil = Image.open(BytesIO(img_bytes)).convert("RGB")
        aumentadas = aplicar_aumentaciones(img_pil)
        
        for tipo, img_aumentada in aumentadas:
            nombre_hash = sha256(img_aumentada.tobytes()).hexdigest()
            ruta_imagen = os.path.join(carpeta_dni, f"{nombre_hash}.jpg") if tipo == "original" else None
            
            if ruta_imagen and not os.path.exists(ruta_imagen):
                img_aumentada.save(ruta_imagen)
            
            rostros = detect_principal_face(img_aumentada)
            if rostros:
                for rostro in rostros:
                    embedding = generar_embedding(rostro)
                    guardar_embedding_db(
                        persona_id, 
                        embedding, 
                        tipo, 
                        f"{persona_id}-{contador_imagenes}", 
                        ruta_imagen
                    )
        
        # Reconstruir índices después de procesar
        
    except Exception as e:
        print(f"Error procesando imagen: {e}")

def eliminar_imagenes_async(persona_id, hashes_a_eliminar):
    try:
        conexion = conectar_db()
        cursor = conexion.cursor(dictionary=True)
        
        # Obtener el DNI de la persona para construir la ruta base
        cursor.execute("SELECT dni FROM personas WHERE id = %s", (persona_id,))
        persona = cursor.fetchone()
        if not persona:
            print(f"No se encontró persona con ID {persona_id}")
            return
            
        dni = persona['dni']
        base_dir = os.path.join(IMAGES_DIR, dni)
        
        for img_hash in hashes_a_eliminar:
            # 1. Buscar la ruta completa usando el hash
            cursor.execute("""
                SELECT imagen_ruta, descripcion 
                FROM embeddings_personas 
                WHERE persona_id = %s AND imagen_ruta LIKE %s
                LIMIT 1
            """, (persona_id, f"%{img_hash}%"))
            
            registro = cursor.fetchone()
            
            if not registro:
                print(f"No se encontró imagen con hash {img_hash} para persona {persona_id}")
                continue
                
            ruta_imagen = registro['imagen_ruta']
            descripcion = registro['descripcion']
            
            # Extraer la parte común de la descripción (ej: "17-1" de "17-1-cara")
            identificador = '-'.join(descripcion.split('-')[:2])
            
            # 2. Eliminar todos los registros con la misma descripción base
            cursor.execute("""
                DELETE FROM embeddings_personas 
                WHERE persona_id = %s AND descripcion LIKE %s
            """, (persona_id, f"{identificador}%"))
            
            print(f"Eliminados registros para descripción: {identificador}")
            
            # 3. Eliminar archivo físico
            if ruta_imagen:
                # Construir ruta completa
                nombre_archivo = os.path.basename(ruta_imagen)
                ruta_completa = os.path.join(base_dir, nombre_archivo)
                
                if os.path.exists(ruta_completa):
                    try:
                        os.remove(ruta_completa)
                        print(f"Archivo eliminado: {ruta_completa}")
                    except Exception as e:
                        print(f"Error eliminando archivo {ruta_completa}: {e}")
                else:
                    print(f"Archivo no encontrado: {ruta_completa}")
        
        conexion.commit()
        print(f"Proceso completado para persona {persona_id}")
        
    except Exception as e:
        print(f"Error en eliminar_imagenes_async: {str(e)}")
        if conexion:
            conexion.rollback()
    finally:
        if conexion:
            conexion.close()

def worker():
    """Worker que procesa diferentes tipos de tareas"""
    while True:
        try:
            task_type, *task_data = processing_queue.get()
            if task_type is None:  # Señal para terminar
                break
                
            if task_type == 'procesar_imagen':
                img_bytes, persona_id, carpeta_dni, contador_imagenes = task_data
                procesar_imagen_async(img_bytes, persona_id, carpeta_dni, contador_imagenes)
                
            elif task_type == 'eliminar_imagenes':
                eliminar_embeddings_faiss(persona_id)
                persona_id, rutas_a_eliminar = task_data
                eliminar_imagenes_async(persona_id, rutas_a_eliminar)
                
        except Exception as e:
            print(f"Error en worker: {e}")
        finally:
            processing_queue.task_done()

# Iniciar workers
for _ in range(MAX_WORKERS):
    threading.Thread(target=worker, daemon=True).start()



@rutas_personas.route("/agregar_persona", methods=["POST"])
@jwt_required()
def agregar_persona_async():
    try:
        # Validación de datos básica
        dni = request.form.get("idNumber", "").strip()
        nombres = request.form.get("fullName", "").strip()
        if not dni or not nombres:
            return jsonify({"error": "DNI y nombres son obligatorios"}), 400

        # Obtener demás datos
        datos_persona = {
            'apellidos': request.form.get("lastName", "").strip(),
            'sexo': request.form.get("idSexo", "").strip(),
            'fecha_nac': request.form.get("idFecha", "").strip(),
            'descripcion': request.form.get("physicDescription", "").strip()
        }

        conexion = conectar_db()
        persona_id = None
        carpeta_dni = None
        imagenes_procesadas = 0

        try:
            with conexion.cursor() as cursor:
                # Verificar existencia del DNI
                cursor.execute("SELECT id FROM personas WHERE dni = %s", (dni,))
                existing_person = cursor.fetchone()
                
                if existing_person:
                    # Actualizar persona existente
                    persona_id = existing_person[0]
                    cursor.execute("""
                        UPDATE personas 
                        SET nombres = %s,
                            apellidos = %s,
                            fecha_nacimiento = %s,
                            genero = %s,
                            descripcion = %s,
                            fecha_registro = NOW()
                        WHERE id = %s
                    """, (nombres, datos_persona['apellidos'], datos_persona['fecha_nac'], 
                          datos_persona['sexo'], datos_persona['descripcion'], persona_id))
                    
                    # Manejo de carpeta existente
                    carpeta_dni = crear_carpeta_persona(dni)
                else:
                    # Insertar nueva persona
                    cursor.execute("""
                        INSERT INTO personas 
                        (dni, nombres, apellidos, fecha_nacimiento, genero, descripcion, fecha_registro)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (dni, nombres, datos_persona['apellidos'], datos_persona['fecha_nac'],
                          datos_persona['sexo'], datos_persona['descripcion']))
                    persona_id = cursor.fetchone()[0]
                    
                    # Crear carpeta para nuevo DNI
                    carpeta_dni = crear_carpeta_persona(dni)

            conexion.commit()

            # Procesamiento de imágenes
            imagenes = request.files.getlist("photos")
            for i, img in enumerate(imagenes, 1):
                try:
                    if img.filename:  # Solo procesar si tiene nombre
                        img_bytes = img.read()
                        # Nombre único para la imagen
                        timestamp = int(time.time())
                        extension = os.path.splitext(img.filename)[1].lower()
                        nombre_imagen = f"{timestamp}_{i}{extension}"
                        
                        processing_queue.put(('procesar_imagen', img_bytes, persona_id, carpeta_dni, nombre_imagen))
                        imagenes_procesadas += 1
                except Exception as img_error:
                    current_app.logger.error(f"Error procesando imagen {i}: {str(img_error)}")

            return jsonify({
                "status": "success",
                "message": "Procesamiento iniciado correctamente",
                "persona_id": persona_id,
                "dni": dni,
                "imagenes_recibidas": len(imagenes),
                "imagenes_procesadas": imagenes_procesadas,
                "carpeta": os.path.basename(carpeta_dni),
                "registro_existente": existing_person is not None,
                "timestamp": datetime.now().isoformat()
            }), 202

        except Exception as db_error:
            conexion.rollback()
            current_app.logger.error(f"Error en base de datos: {str(db_error)}")
            return jsonify({
                "status": "error",
                "message": "Error al procesar el registro",
                "detalle": str(db_error)
            }), 500

        finally:
            if conexion:
                conexion.close()

    except Exception as e:
        current_app.logger.error(f"Error general: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error inesperado en el servidor",
            "detalle": str(e)
        }), 500


@rutas_personas.route('/editar_persona/<int:persona_id>', methods=['PUT'])
@jwt_required()
def editar_persona(persona_id):
    conexion = None
    try:
        # Obtener datos del formulario
        dni = request.form.get("idNumber", "").strip()
        nombres = request.form.get("fullName", "").strip()
        apellidos = request.form.get("lastName", "").strip()
        sexo = request.form.get("idSexo", "").strip()
        fecha_nac = request.form.get("idFecha", "").strip()
        descripcion = request.form.get("physicDescription", "").strip()
        imagenes_eliminar = request.form.getlist('imagenes_eliminar[]')
        nuevas_imagenes = request.files.getlist("photos")

        # Validación básica
        if not dni or not nombres:
            return jsonify({"error": "DNI y nombres son obligatorios"}), 400

        # 1. Actualizar datos básicos
        conexion = conectar_db()
        with conexion.cursor() as cursor:
            # Verificar persona y obtener DNI actual
            cursor.execute("SELECT dni FROM personas WHERE id = %s", (persona_id,))
            persona_data = cursor.fetchone()
            if not persona_data:
                return jsonify({"error": "Persona no encontrada"}), 404
            
            dni_actual = persona_data[0]
            cambio_dni = dni != dni_actual

            # Actualizar datos (sin RETURNING)
            cursor.execute("""
                UPDATE personas 
                SET dni = %s, nombres = %s, apellidos = %s, 
                    genero = %s, fecha_nacimiento = %s, descripcion = %s
                WHERE id = %s
            """, (dni, nombres, apellidos, sexo, fecha_nac, descripcion, persona_id))

            # Si cambió el DNI, manejar el cambio
            if cambio_dni:
                # Renombrar carpeta
                carpeta_vieja = os.path.join(IMAGES_DIR, secure_filename(dni_actual))
                carpeta_nueva = os.path.join(IMAGES_DIR, secure_filename(dni))
                
                if os.path.exists(carpeta_vieja):
                    os.rename(carpeta_vieja, carpeta_nueva)
                
                # Actualizar rutas en la base de datos
                cursor.execute("""
                    UPDATE embeddings_personas 
                    SET imagen_ruta = REPLACE(imagen_ruta, %s, %s)
                    WHERE persona_id = %s AND imagen_ruta LIKE %s
                """, (f"/{dni_actual}/", f"/{dni}/", persona_id, f"%/{dni_actual}/%"))

        conexion.commit()

        # 2. Procesar imágenes en segundo plano
        if imagenes_eliminar:
            processing_queue.put(('eliminar_imagenes', persona_id, imagenes_eliminar))

        if nuevas_imagenes:
            carpeta_dni = crear_carpeta_persona(dni)
            
            # Obtener último número de imagen usado
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(CAST(SUBSTRING_INDEX(descripcion, '-', -1) AS UNSIGNED)) as max_num
                    FROM embeddings_personas 
                    WHERE persona_id = %s
                """, (persona_id,))
                resultado = cursor.fetchone()
                contador_imagenes = (resultado[0] or 0) + 1

                for img in nuevas_imagenes:
                    img_bytes = img.read()
                    processing_queue.put(('procesar_imagen', img_bytes, persona_id, carpeta_dni, contador_imagenes))
                    contador_imagenes += 1

        return jsonify({
            "status": "success",
            "message": "Edición iniciada. Las imágenes se están procesando en segundo plano",
            "persona_id": persona_id,
            "imagenes_a_eliminar": len(imagenes_eliminar),
            "nuevas_imagenes": len(nuevas_imagenes),
            "cambio_dni": cambio_dni
        }), 202

    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conexion:
            conexion.close()


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

#obetener personas


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
            eliminar_embeddings_faiss(id)
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




@rutas_personas.route("/cargar_carpeta_personas", methods=["POST"])
@jwt_required()
def cargar_carpeta_personas():
    try:
        if 'files[]' not in request.files:
            return jsonify({"error": "No se recibió ninguna carpeta"}), 400
        
        archivos = request.files.getlist('files[]')
        if not archivos or all(not archivo.filename for archivo in archivos):
            return jsonify({"error": "La carpeta está vacía o los nombres de archivos son inválidos"}), 400

        personas_archivos = {}
        dni_invalidos = []
        
        for archivo in archivos:
            filename = secure_filename(archivo.filename)
            dni = os.path.splitext(filename)[0].strip()
            dni_match = re.match(r'^[a-zA-Z_]*?(\d{8})$', dni)
            if dni_match:
                dni = dni_match.group(1) 
            else:
                dni_invalidos.append(filename)
                continue

            if dni not in personas_archivos:
                personas_archivos[dni] = []
            personas_archivos[dni].append(archivo)

        if dni_invalidos:
            return jsonify({
                "error": "Algunos archivos no tienen nombres válidos (DNI de 8 dígitos)",
                "archivos_invalidos": dni_invalidos
            }), 400

        resultados = []
        for dni, archivos in personas_archivos.items():
            conexion = conectar_db()
            try:
                with conexion.cursor(buffered=True) as cursor:  
                    # Insertar o ignorar si ya existe
                    cursor.execute("""
                        INSERT IGNORE INTO personas (dni, fecha_registro)
                        VALUES (%s, NOW())
                    """, (dni,))
                    
                    # Obtener el ID (nuevo o existente)
                    cursor.execute("SELECT id FROM personas WHERE dni = %s", (dni,))
                    persona_id = cursor.fetchone()[0]
                
                conexion.commit()
            except Exception as e:
                conexion.rollback()
                return jsonify({"error": f"Error al registrar/obtener persona {dni}: {str(e)}"}), 500
            finally:
                conexion.close()

            carpeta_dni = crear_carpeta_persona(dni)
            
            for i, img in enumerate(archivos, 1):
                img_bytes = img.read()
                processing_queue.put(('procesar_imagen', img_bytes, persona_id, carpeta_dni, i))

            resultados.append({
                "dni": dni,
                "persona_id": persona_id,
                "imagenes_recibidas": len(archivos),
                "status": "encolado"
            })

        return jsonify({
            "status": "success",
            "message": "Procesamiento iniciado en segundo plano",
            "personas_procesadas": len(resultados),
            "detalles": resultados,
            "timestamp": datetime.now().isoformat()
        }), 202

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500