#!/usr/bin/python3

import os
import sys
import threading
import traceback
from asterisk.manager import Manager, Event, ManagerSocketException, ManagerAuthException, ManagerException
from asterisk.agi import AGI
import time

import requests

#Credenciales Manager
server = "localhost"
user = "telefonia"
pwd = "telefonia"

#Url del servidor sin '/' al final
url_api = "http://10.72.180.6:8090"
url_start = "coachVirtual" #Endpoint inciar grabacion
url_end = "end_session" #Endpoint terminar grabacion

#Tiempo de grabacion
seg_grabacion = 5

#Nombre de la variable de respuesta
variable = "coach_mensaje"

def iniciar_grabacion(manager:Manager, canal, path_file, unique_id, i):
    print(f"Iniciando grabación en el canal {canal}")
    try:       
        manager_msg = manager.send_action({
            'Action' : "MixMonitor",
            'Channel': canal,
            'File': f'{path_file}/coach-{unique_id}-{i}.wav',
            'Format': 'wav',
            'options': f'r({path_file}/coach-{unique_id}-{i}-in.wav)t({path_file}/coach-{unique_id}-{i}-out.wav)'
        })
        
        print(manager_msg.response)
        if 'Success' in manager_msg.response[0]:
            print("Grabación iniciada correctamente.")
        else:
            print(f"Error al iniciar la grabación: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al iniciar la grabación en el canal {canal}: {e}")

def detener_grabacion(manager, canal):
    print(f"Deteniendo grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action': 'StopMixMonitor',
            'Channel': canal
        })
        print(manager_msg.response)
        if 'Success' in manager_msg.response[0]:
            print("Grabación detenida correctamente.")
        else:
            print(f"Error al detener la grabación: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al detener la grabación en el canal {canal}: {e}")

def enviar_grabacion(manager, canal_a_grabar, path_file, unique_id, i):
    # Definir la ruta de los archivos de grabación
    archivo_in = f"{path_file}/{unique_id}-{i}-in.wav"
    archivo_out = f"{path_file}/{unique_id}-{i}-out.wav"

    # Verificar si los archivos existen
    if not os.path.exists(archivo_in) or not os.path.exists(archivo_out):
        print("Los archivos de grabación no existen.")
        return

    # Abrir los archivos de grabación en modo binario
    with open(archivo_in, "rb") as f_in, open(archivo_out, "rb") as f_out:
        # Crear un diccionario con los datos a enviar
        datos = {
            "SessionID": unique_id,
            "AudioUser": f_in.read(),  # Leer el contenido del archivo de entrada
            "AudioAgent": f_out.read(),  # Leer el contenido del archivo de salida
            "AgentID": unique_id
        }

        # Enviar la solicitud POST con los datos
        response = requests.post(f'{url_api}/{url_start}', files=datos)

    
    print(response)
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        print("Archivos de grabación enviados correctamente.")
        set_var(manager, canal_a_grabar, response)
    else:
        print(f"Error al enviar archivos de grabación: {response.status_code}")

def detener_envio_grabacion(unique_id):
    # Crear un diccionario con los datos a enviar
    datos = {
        "SessionID": unique_id,
    }

    # Enviar la solicitud POST con los datos
    response = requests.post(f'{url_api}/{url_end}', files=datos)

    
    print(response)
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        print("Envio de Archivos de grabación detenido correctamente.")
    else:
        print(f"Error al detener envio de archivos de grabación: {response.status_code}")

def set_var(manager, canal, value):
    try:
        manager_msg = manager.send_action({
                'Action': 'Setvar',
                'Channel': canal,
                'Variable': variable,
                'Value': value
            })
        if 'Success' in manager_msg.response[0]:
                print("Variable establecidad correctamente")
        else:
            print(f"Error al establecer la variable: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al establecer la variable en el canal {canal}: {e}")

def grabaciones(manager, canal_a_grabar, path_file, unique_id):
    try: 
        i = 0
        # Bucle para iniciar grabaciones cada 5 segundos
        print(manager.status(canal_a_grabar).response[0])
        while 'Success' in manager.status(canal_a_grabar).response[0]:
            iniciar_grabacion(manager, canal_a_grabar, path_file, unique_id, i)
            time.sleep(seg_grabacion)  # Esperar $seg_grabacion segundos antes de detener la grabación
            detener_grabacion(manager, canal_a_grabar)
            i+=1
            threading.Thread(target=enviar_grabacion, args=(manager, canal_a_grabar, path_file, unique_id, i)).start()
        detener_envio_grabacion(unique_id)
    except ManagerException as e:
        print(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        print(f"Error general: {traceback.format_exc()}")
    finally:
        # Cerrar la conexión con el servidor Asterisk
        manager.close()

def main(canal_a_grabar, path_file, unique_id):
    try:
        # Crear una instancia de Manager
        manager = Manager()

        # Conectar al servidor Asterisk
        manager.connect(server)
        manager.login(user, pwd)
         
        # Registrar un manejador de eventos para el evento AgentConnect
        manager.register_event('AgentConnect', lambda m=manager, canal=canal_a_grabar, path=path_file, uid=unique_id: grabaciones(m, canal, path, uid))
        
        # Iniciar la escucha de eventos
        manager.event_dispatch()
        
    except ManagerSocketException as e:
        print(f"Error conectando al servidor Asterisk: {e}")
    except ManagerAuthException as e:
        print(f"Error de autenticación en el servidor Asterisk: {e}")
    except ManagerException as e:
        print(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        print(f"Error general: {traceback.format_exc()}")
    

if __name__ == "__main__":
    # Verificamos que se proporcionen los argumentos esperados
    if len(sys.argv) != 4:
        print("Uso: python coach.py canal path_file unique_id")
        sys.exit(1)
    
    # Obtenemos los argumentos de la línea de comandos
    canal_a_grabar = sys.argv[1]
    path_file = sys.argv[2]
    unique_id = sys.argv[3]
    
    main(canal_a_grabar, path_file, unique_id)
    
   