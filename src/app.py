import os
from flask import Flask, send_from_directory , request, jsonify , abort , render_template
from flask_cors import CORS
import logging
import pytz
from datetime import datetime
import threading
import webbrowser
from conexiondb import conectar_db,crear_tablas_si_no_existen, cargar_todos_embeddings_faiss ,poner_camaras_inactivas
from registros import rutas_personas
from utils import socketio, jwt
from camaras import rutas_camaras
import multicamara
from login import auth_bp
from reconocer import reconocer

# Inicializar zona horaria (Perú)
zona_peru = pytz.timezone('America/Lima')

# Inicializar Flask
app = Flask(__name__)
CORS(app)
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Cambiar en producción

# Configure JWT
socketio.init_app(app)
jwt.init_app(app)



multicamara.socketio = socketio


# Register the auth blueprint
app.register_blueprint(auth_bp)


# Configurar el logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


#creacion de tablas 
db = conectar_db()
if db:
    crear_tablas_si_no_existen(db)
    poner_camaras_inactivas()
    db.close()
    
    
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))

@app.route('/')
def root():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'auth.html')

@app.route('/sistema')
def sistema():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'menu.html')


@app.route('/<path:filename>')
def serve_html(filename):
    file_path = os.path.join(BASE_DIR, 'templates', filename)
    if os.path.isfile(file_path):
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), filename)
    else:
        abort(404)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'js'), filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    file_path = os.path.join(BASE_DIR, 'static', filename)
    if os.path.isfile(file_path):
        return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)
    else:
        abort(404)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)

# Inicializar FAISS cargando embeddings desde la base de datos
cargar_todos_embeddings_faiss()


# Registrar el Blueprint de rutas_camaras - rutas_personas

app.register_blueprint(rutas_camaras, url_prefix='/camara')
app.register_blueprint(rutas_personas, url_prefix='/registros')
@app.route('/persona/reconocer', methods=['POST'])
def route_reconocer():
    return reconocer()

@app.route('/ver')
def ver():
    return multicamara.listar_hilos_camaras()

@app.route('/vertodos')
def verT():
    return multicamara.listar_hilos_activos()

@app.route('/v')
def v():
    return multicamara.obtener_camaras_activas()



def ciclo_verificacion():
    socketio.sleep(20)  # Espera inicial para que el servidor se estabilice
    multicamara.verificar_y_lanzar_camaras()

if __name__ == "__main__":
    try:
        multicamara.verificar_y_lanzar_camaras()
        #thread_verificacion = threading.Thread(target=ciclo_verificacion, daemon=True)
        #thread_verificacion.start()
        #webbrowser.open_new("http://localhost:5000/")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {str(e)}")

