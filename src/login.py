from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from conexiondb import conectar_db
import bcrypt
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

CORS(auth_bp, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

def authenticate(email, password, con):
    try:
        cursor = con.cursor()
        sql = "SELECT id, username, email, password_hash, rol FROM usuarios WHERE email = %s"
        cursor.execute(sql, (email,))
        result = cursor.fetchone()
        
        user = dict(zip(cursor.column_names, result)) if result else None
        
        if not user:  # Si no se encuentra el usuario
            return {"mensaje": "Usuario no encontrado"}

        # Verificar la contraseña con bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return {"id": user['id'], "username": user['username'],"rol": user['rol']}
        else:
            return {"mensaje": "Credenciales inválidas"}
    except mysql.connector.Error as err:
        logging.error(f"MySQL Error: {err}")
        return {"mensaje": f"Error de base de datos: {err}"}
    except Exception as e:
        logging.error(f"Error inesperado: {str(e)}")
        return {"mensaje": f"Error inesperado: {str(e)}"}
    finally:
        if cursor:
            cursor.close()

@auth_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    identity = get_jwt_identity()
    return jsonify(user_id=identity), 200

@auth_bp.route("/auth", methods=["POST"])
def auth():
    con = conectar_db()
    if not request.is_json:
        return jsonify({"mensaje": "Falta el formato JSON en la solicitud"}), 400

    email = request.json.get('email', None)
    password = request.json.get('password', None)

    if not email or not password:
        return jsonify({"mensaje": "Usuario o contraseña no proporcionados"}), 400

    auth_result = authenticate(email, password, con)
    if "id" in auth_result: 
        access_token = create_access_token(identity=str(auth_result['id']), additional_claims={'username': auth_result['username'],'rol': auth_result['rol']})
        return jsonify(access_token=access_token), 200
    else:  # Autenticación fallida
        return jsonify({"mensaje": auth_result["mensaje"]}), 401

@auth_bp.route("/api_guardarUsuario", methods=["POST"])
def api_guardarUsuario():
    con = None
    try:
        # Conexión a la base de datos
        con = conectar_db()
        if not con:
            logger.error("No se pudo conectar a la base de datos en el registro")
            return jsonify({"mensaje": "Error de conexión a la base de datos", "success": False}), 500

        # Obtener datos de la solicitud
        datosUser = request.json
        if not datosUser:
            return jsonify({"mensaje": "Faltan datos en la solicitud", "success": False}), 400

        username = datosUser.get('username')
        email = datosUser.get('email')
        password = datosUser.get('password')
        rol = datosUser.get('rol', 'usuario')  # Rol predeterminado
        estado = 'inactivo'  # Estado predeterminado

        # Validación de campos obligatorios
        if not all([username, email, password]):
            return jsonify({"mensaje": "Todos los campos son requeridos", "success": False}), 400

        # Verificar existencia de usuario o correo
        with con.cursor(dictionary=True) as cursor:
            sql_check = "SELECT email FROM usuarios WHERE email = %s"
            cursor.execute(sql_check, (email,))
            existing = cursor.fetchone()

        if existing:
            return jsonify({"mensaje": "El correo ya está registrado", "campo": "email", "success": False}), 409

        # Encriptar contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insertar nuevo usuario
        with con.cursor() as cursor:
            sql_insert = """
                INSERT INTO usuarios (username, email, password_hash, rol, estado, fecha_registro)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(sql_insert, (username, email, hashed_password, rol, estado))
            con.commit()

        return jsonify({"mensaje": "Usuario registrado correctamente", "success": True}), 201

    except Exception as e:
        # Manejo detallado de excepciones
        stack_trace = traceback.format_exc()
        logger.error(f"Error en el registro de usuario: {e}\n{stack_trace}")
        return jsonify({"mensaje": "Error interno del servidor", "success": False}), 500

    finally:
        # Cerrar conexión a la base de datos
        if con:
            try:
                con.close()
            except Exception as close_error:
                logger.warning(f"Error al cerrar la conexión: {close_error}")


# Error handling
@auth_bp.errorhandler(404)
def not_found(e):
    return jsonify({"mensaje": "Recurso no encontrado"}), 404


@auth_bp.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({"mensaje": "Error interno del servidor"}), 500
