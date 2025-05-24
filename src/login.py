from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from conexiondb import conectar_db
import bcrypt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a blueprint for auth routes
auth_bp = Blueprint('auth', __name__)
def authenticate(username, password, con):
    try:
        cursor = con.cursor()
        sql = "SELECT id, username, password FROM usuarios WHERE username = %s"
        cursor.execute(sql, (username,))
        result = cursor.fetchone()
        
        # Convertir manualmente el resultado a un diccionario
        user = dict(zip(cursor.column_names, result)) if result else None
        
        if not user:  # Si no se encuentra el usuario
            return {"mensaje": "Usuario no encontrado"}

        # Verificar la contraseña con bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return {"id": user['id'], "username": user['username']}
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

@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(user_login=current_user)


@auth_bp.route("/auth", methods=["POST"])
def auth():
    con = conectar_db()
    if not request.is_json:
        return jsonify({"mensaje": "Falta el formato JSON en la solicitud"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username or not password:
        return jsonify({"mensaje": "Usuario o contraseña no proporcionados"}), 400

    auth_result = authenticate(username, password, con)
    if "id" in auth_result: 
        access_token = create_access_token(identity={'id': auth_result['id'], 'username': auth_result['username']})
        return jsonify(access_token=access_token), 200
    else:  # Autenticación fallida
        return jsonify({"mensaje": auth_result["mensaje"]}), 401



@auth_bp.route("/api_guardarUsuario", methods=["POST"])
def api_guardarUsuario():
    con = None
    try:
        con = conectar_db()
        if con is None:
            logger.error("Failed to connect to database")
            return jsonify({"mensaje": "Error de conexión a la base de datos"}), 500

        # Log incoming request data (without sensitive info)
        logger.info("Received user registration request")
        
        datosUser = request.json
        if not datosUser:
            logger.warning("Missing JSON data in request")
            return jsonify({"mensaje": "Faltan datos en la solicitud"}), 400

        username = datosUser.get('username')
        password = datosUser.get('password')
        firstname = datosUser.get('firstname')
        lastname = datosUser.get('lastname')

        logger.info(f"Registration attempt for username: {username}")
        
        if not username or not password or not firstname or not lastname:
            logger.warning(f"Missing required fields for registration: {username}")
            return jsonify({"mensaje": "Todos los campos son requeridos"}), 400

        # Verificar si el usuario ya existe
        with con.cursor() as cursor:
            sql_check = "SELECT id FROM usuarios WHERE username = %s"
            logger.debug(f"Executing query: {sql_check} with username: {username}")
            cursor.execute(sql_check, (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                logger.info(f"User already exists: {username}")
                return jsonify({"mensaje": "El usuario ya existe"}), 409  # 409 Conflict

        # Encriptar la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        logger.debug("Password hashed successfully")

        # Insertar el nuevo usuario en la base de datos
        try:
            with con.cursor() as cursor:
                # Ensure table name is correct (case-sensitive)
                sql_insert = """
                    INSERT INTO usuarios (username, password, firstname, lastname, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """
                logger.debug(f"Executing insert query for username: {username}")
                cursor.execute(sql_insert, (username, hashed_password, firstname, lastname))
                con.commit()
                logger.info(f"User registered successfully: {username}")
        except Exception as db_err:
            logger.error(f"Database error during insert: {str(db_err)}")
            if 'Table' in str(db_err) and 'doesn\'t exist' in str(db_err):
                # Try to create the table if it doesn't exist
                logger.info("Attempting to create usuarios table")
                try:
                    with con.cursor() as cursor:
                        create_table_sql = """
                        CREATE TABLE IF NOT EXISTS usuarios (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            username VARCHAR(50) NOT NULL UNIQUE,
                            password VARCHAR(255) NOT NULL,
                            firstname VARCHAR(100) NOT NULL,
                            lastname VARCHAR(100) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        """
                        cursor.execute(create_table_sql)
                        con.commit()
                        logger.info("usuarios table created successfully")
                        
                        # Try inserting user again
                        cursor.execute(sql_insert, (username, hashed_password, firstname, lastname))
                        con.commit()
                        logger.info(f"User registered successfully after table creation: {username}")
                except Exception as create_err:
                    logger.error(f"Failed to create table: {str(create_err)}")
                    raise create_err
            else:
                raise db_err

        return jsonify({"mensaje": "Usuario registrado correctamente"}), 201  # 201 Created

    except Exception as e:
        logger.error(f"Exception in user registration: {repr(e)}")
        return jsonify({"mensaje": f"Error interno: {str(e)}"}), 500  # 500 Internal Server Error
    finally:
        if con is not None:
            try:
                con.close()
                logger.debug("Database connection closed")
            except Exception as close_err:
                logger.error(f"Error closing connection: {str(close_err)}")

