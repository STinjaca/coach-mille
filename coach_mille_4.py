#!/usr/bin/python3

import os
import sys
import threading
import logging
import traceback
from asterisk.manager import Manager, Event, ManagerAuthException, ManagerException, ManagerSocketException
import time
import requests
from prometheus_client import start_http_server, Gauge
from flask import Flask, request, jsonify

app = Flask(__name__)
# Configuración del logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='ami_monitoreo_mille.log',  # Nombre del archivo de log
                    filemode='w')  # 'w' para sobrescribir el archivo cada vez, 'a' para añadir

# Función para capturar excepciones no controladas
def log_uncaught_exceptions(exctype, value, tb):
    logging.critical("Unhandled exception", exc_info=(exctype, value, tb))

# Configurar sys.excepthook para usar la función anterior
sys.excepthook = log_uncaught_exceptions

# Iniciar servidor HTTP para exponer las métricas a Prometheus en el puerto 8000
start_http_server(8001)

# Definir métricas 
metricas = {
    "Agent": {
        #"chain_rate": Gauge('Tasa de encadenamiento del agente', 'Tasa de encadenamiento del agente'),
        "speak_porcentage": Gauge('Porcentaje_hablado_Agente', 'Porcentaje de habla del agente'),
        "number_silences": Gauge('Numero_silencios_Agente', 'Número de silencios del agente'),
        "duration_silences": Gauge('Duracion_de_silencios_del_agente', 'Duración de silencios del agente'),
        "silences_porcentage": Gauge('Porcentaje_de_silencios_del_agente', 'Porcentaje de silencios del agente'),
        "sentimient": Gauge('Sentimiento_agente', 'Sentimientos Agente')
        #"vocabulary_stress": [],
        #"inadequate_vacabulary": []
    },
    "User": {
        #"chain_rate": Gauge('Tasa de encadenamiento del usuario', 'Tasa de encadenamiento del Usuario'),
        "speak_porcentage": Gauge('Porcentaje_hablado_usuario', 'Porcentaje de habla del Usuario'),
        "number_silences": Gauge('Numero_silencios_usuario', 'Número de silencios del Usuario'),
        "duration_silences": Gauge('Duracion_de_silencios_del_Usuario', 'Duración de silencios del Usuario'),
        "silences_porcentage": Gauge('Porcentaje_de_silencios_del_Usuario', 'Porcentaje de silencios del Usuario'),
        "sentimient": Gauge('Sentimiento_usuario', 'Sentimientos usuario'),
        "intention": Gauge('Intension_usuario', 'Intension Usuario')
        #"inadequate_vacabulary": [],
        #"intention": Gauge('Sentimiento_asesor', 'Sentiminetos Asesor')
    }
}

#Credenciales Manager
server = "localhost"
user = "telefonia"
pwd = "telefonia"

#Url del servidor sin '/' al final
url_api = "http://10.72.180.6:8090"
url_start = "coachVirtual" #Endpoint inciar grabacion
url_end = "end_session" #Endpoint terminar grabacion

#Tiempo de grabacion
seg_grabacion = 2

def update_prometheus_metrics(response_json):
    for k,v in metricas['Agent'].items():
        v.set(response_json['Agent'] [k])       
    for k,v in metricas['User'].items():
        v.set(response_json['User'] [k])   
                

def iniciar_grabacion(manager:Manager, canal:str, archivo:str, archivo_in:str, archivo_out:str):
    logging.info(f"coach-estado - Iniciando grabación en el canal {canal}")
    try:       
        manager_msg = manager.send_action({
            'Action' : "MixMonitor",
            'Channel': canal,
            'File': archivo,
            'Format': 'wav',
            'options': f'bW(2)r({archivo_in})t({archivo_out})'
        })
        
        if 'Success' in manager_msg.response[0]:
            logging.info(f"coach-estado - Grabación iniciada correctamente - canal {canal}")
        else:
            logging.error(f"coach-estado - Error al iniciar la grabación: {manager_msg.response}")
    except ManagerException as e:
        logging.exception(f"Error al iniciar la grabación en el canal {canal}: {e}")

def detener_grabacion(manager:Manager, canal:str):
    logging.info(f"coach-estado - Deteniendo grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action': 'StopMixMonitor',
            'Channel': canal
        })
        if 'Success' in manager_msg.response[0]:
            logging.info(f"coach-estado - Grabación detenida correctamente - canal {canal}")
        else:
            logging.error(f"coach-estado - Error al detener la grabación: {manager_msg.response}")
    except ManagerException as e:
        logging.exception(f"Error al detener la grabación en el canal {canal}: {e}")


def enviar_grabacion(manager:Manager, canal, archivo_in, archivo_out, unique_id):
    if not os.path.exists(archivo_in) or not os.path.exists(archivo_out):
        logging.error(f"coach-estado - Los archivos de grabación no existen - canal {canal}")
        return

    with open(archivo_in, "rb") as f_in, open(archivo_out, "rb") as f_out:
        datos = {
            "SessionID": unique_id,
            "AgentID": unique_id
        }
        files = {
            "AudioUser": f_in,
            "AudioAgent": f_out
        }

        try:
            response = requests.post(f'{url_api}/{url_start}', data=datos, files=files)
            
            if response.status_code != 200:
                logging.error(f"coach-estado - Error al enviar archivos de grabación: {response.status_code}")
                return
            
            response_json = response.json()
            if not isinstance(response_json, dict):
                logging.error(f"coach-estado - La respuesta no es un diccionario - canal {canal}")
                return 
            # Asegurar que 'Agent' y 'User' son claves en el diccionario
            if 'Agent' not in response_json and 'User' not in response_json:
                logging.error(f"coach-estado - Las claves 'Agent' o 'User' no están presentes en la respuesta - canal {canal}")
                return
            
            update_prometheus_metrics(response_json)

            for role in ['Agent', 'User']:
                for k, v in response_json[role].items():
                    valor_actual = get_var(manager, canal, f"coach-{role.lower()}-{k}", default="")
                    nuevo_valor = f"{valor_actual} {v}".strip() if valor_actual else str(v)
                    set_var(manager, canal, f"coach-{role.lower()}-{k}", nuevo_valor)
                
        except ValueError:
            logging.exception(f"coach-estado - Error procesando JSON - {canal}")
        except requests.RequestException as e:
            logging.exception(f"coach-estado - Error en la solicitud: {str(e)}")
        except Exception as e:
            logging.exception(f"coach-estado - Excepción en la función enviar_grabacion: {str(e)}")




def detener_envio_grabacion(manager:Manager, canal, unique_id):
    # Crear un diccionario con los datos a enviar
    datos = {
        "SessionID": unique_id
    }

    # Enviar la solicitud POST con los datos
    response = requests.post(f'{url_api}/{url_end}', data=datos)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        logging.info(f"coach-estado - Envio de Archivos de grabación detenido correctamente - canal {canal}")
        response_json = response.json()
        update_prometheus_metrics(response_json)  # Actualiza las métricas en Prometheus basadas en la respuesta

        for k,v in response.json()['Agent'].items():
            set_var(manager, canal, f"coach-agent-{k}", str(v))
        for k,v in response.json()['User'].items():
            set_var(manager, canal, f"coach-user-{k}", str(v))
    else:
        logging.error(f"coach-estado - Error al detener envio de archivos de grabación: {response.status_code}")

def set_var(manager:Manager, canal, variable, value):
    try:
        manager_msg = manager.send_action({
                'Action': 'Setvar',
                'Channel': canal,
                'Variable': variable,
                'Value': value
            })
        if 'Success' in manager_msg.response[0]:
            logging.info(f"coach-estado - Variable establecidad correctamente - canal {canal}")
        else:
            logging.error(f"coach-estado - Error al establecer la variable: {manager_msg.response}")
    except ManagerException as e:
        logging.exception(manager, canal, f"Error al establecer la variable en el canal {canal}: {e}")

def get_var(manager: Manager, canal, variable, default=None):
    try:
        response = manager.send_action({
            'Action': 'GetVar',
            'Channel': canal,
            'Variable': variable
        })
        if 'Success' in response.response[0]:
            logging.info(f"coach-estado - Variable obtenida correctamente - canal {canal}")
            return response.response[1]['Value']
        else:
            logging.error(f"No se pudo obtener la variable {variable}: {response.response}")
            return default
    except ManagerException as e:
        logging.exception(f"Error al obtener la variable {variable} en el canal {canal}: {e}")
        return default


def grabaciones(event:Event, manager:Manager, canal, path_file, unique_id):
    try: 
        set_var(manager, canal, "coach-event-data", event.data)
        i = 0
        # Bucle para iniciar grabaciones cada 5 segundos

        while 'Success' in manager.status(canal).response[0]:
            # Definir la ruta de los archivos de grabación
            archivo = f"{path_file}/coach-{unique_id}-{i}.wav"
            archivo_in = f"{path_file}/coach-{unique_id}-{i}-in.wav"
            archivo_out = f"{path_file}/coach-{unique_id}-{i}-out.wav"
        
            #Inicia la grabacion del canal
            iniciar_grabacion(manager, canal, archivo, archivo_in, archivo_out)
            time.sleep(seg_grabacion) # Esperar $seg_grabacion segundos antes de detener la grabación
            #Detiene la grabacion del canal
            detener_grabacion(manager, canal)
            #Envia al API las grabaciones
            threading.Thread(target=enviar_grabacion, args=(manager, canal, archivo_in, archivo_out, unique_id)).start()
            #enviar_grabacion(manager, canal, archivo_in, archivo_out, unique_id)
            i+=1
            
        detener_envio_grabacion(manager, canal, unique_id)
    except ManagerException as e:
        logging.exception(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        logging.exception(f"Error general: {traceback.format_exc()}")


@app.route('/iniciarGrabacion/', methods=['GET'])
def iniciar_grabacion_route():
    data = request.args.to_dict()
    canal = data["canal"]
    path_file = data["path_file"]
    unique_id = data["unique_id"]
    
    logging.info(f"Manejando evento Newexten: {canal}")
    try:        
        # Registrar un manejador de eventos para el evento AgentConnect
        manager.register_event('Newexten', lambda event, m=manager, canal=canal, path=path_file, uid=unique_id: grabaciones(event, m, canal, path, uid))
        # Iniciar la escucha de eventos
        manager.event_dispatch()
        return jsonify({"status_code": 200})
        
    except ManagerSocketException as e:
        logging.exception(f"Error conectando al servidor Asterisk: {e}")
    except ManagerAuthException as e:
        logging.exception(f"Error de autenticación en el servidor Asterisk: {e}")
    except ManagerException as e:
        logging.exception(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        logging.exception(f"Error general: {traceback.format_exc()}")
    return jsonify({"status_code": 500})

def conectar_manager():
    manager = Manager()
    while True:
        try:
            manager.connect(server)
            manager.login(user, pwd)
            logging.info("Conectado al servidor Asterisk")
            return manager
        except (ManagerSocketException, ManagerAuthException, ManagerException) as e:
            logging.exception(f"Error conectando al servidor Asterisk: {e}")
            time.sleep(5)  # Espera 5 segundos antes de intentar reconectar

if __name__ == "__main__":
    manager = conectar_manager()
    app.run(port=5039, host='0.0.0.0')
