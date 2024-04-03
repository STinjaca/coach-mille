#!/usr/bin/python3

import os
import sys
import threading
import traceback
from asterisk.manager import Manager, Event, ManagerAuthException, ManagerException, ManagerSocketException
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
variables = {"coach-estado": None,
            "coach-agent": None,
            "coach-user": None
            }

def iniciar_grabacion(manager:Manager, canal:str, archivo:str, archivo_in:str, archivo_out:str):
    set_var(manager, canal, "coach-estado", f"Iniciando grabación en el canal {canal}")
    try:       
        manager_msg = manager.send_action({
            'Action' : "MixMonitor",
            'Channel': canal,
            'File': archivo,
            'Format': 'wav',
            'options': f'br({archivo_in})t({archivo_out})'
        })
        
        if 'Success' in manager_msg.response[0]:
            set_var(manager, canal, "coach-estado", "Grabación iniciada correctamente.")
        else:
            set_var(manager, canal, "coach-estado", f"Error al iniciar la grabación: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al iniciar la grabación en el canal {canal}: {e}")

def detener_grabacion(manager:Manager, canal:str):
    set_var(manager, canal, "coach-estado", f"Deteniendo grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action': 'StopMixMonitor',
            'Channel': canal
        })
        if 'Success' in manager_msg.response[0]:
            set_var(manager, canal, "coach-estado", "Grabación detenida correctamente.")
        else:
            set_var(manager, canal, "coach-estado", f"Error al detener la grabación: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al detener la grabación en el canal {canal}: {e}")

def enviar_grabacion(manager:Manager, canal, archivo_in, archivo_out, unique_id):

    # Verificar si los archivos existen
    if not os.path.exists(archivo_in) or not os.path.exists(archivo_out):
        set_var(manager, canal, "coach-estado", "Los archivos de grabación no existen.")
        return

    # Abrir los archivos de grabación en modo binario
    with open(archivo_in, "rb") as f_in, open(archivo_out, "rb") as f_out:
        # Crear un diccionario con los datos a enviar
        datos = {
            "SessionID": unique_id,
            "AgentID": unique_id
        }
        
        files = {
            "AudioUser": f_in,
            "AudioAgent": f_out
        }

        # Enviar la solicitud POST con los datos
        response = requests.post(f'{url_api}/{url_start}', data=datos, files=files)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        set_var(manager, canal, "coach-estado", "Archivos de grabación enviados correctamente.")
        for k,v in response.json()['Agent'].items():
            set_var(manager, canal, f"coach-agent-{k}", str(v))
        for k,v in response.json()['User'].items():
            set_var(manager, canal, f"coach-user-{k}", str(v))
    else:
        set_var(manager, canal, "coach-estado", f"Error al enviar archivos de grabación: {response.status_code}")

def detener_envio_grabacion(manager:Manager, canal, unique_id):
    # Crear un diccionario con los datos a enviar
    datos = {
        "SessionID": unique_id
    }

    # Enviar la solicitud POST con los datos
    response = requests.post(f'{url_api}/{url_end}', data=datos)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        set_var(manager, canal, "coach-estado", "Envio de Archivos de grabación detenido correctamente.")
        for k,v in response.json()['Agent'].items():
            set_var(manager, canal, f"coach-agent-{k}", str(v))
        for k,v in response.json()['User'].items():
            set_var(manager, canal, f"coach-user-{k}", str(v))
    else:
        set_var(manager, canal, "coach-estado", f"Error al detener envio de archivos de grabación: {response.status_code}")

def set_var(manager:Manager, canal, variable, value):
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
        print(manager, canal, f"Error al establecer la variable en el canal {canal}: {e}")

def user_event(manager:Manager, mensaje):
    try:
        manager_msg = manager.send_action({
                'Action': 'UserEvent',
                'Header1': mensaje,
            })
        if 'Success' in manager_msg.response[0]:
                print("Mensaje enviado correctamente")
        else:
            print(f"Error al enviar el mensaje: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al establecer la variable en el canal {canal}: {e}")

def noop(manager:Manager, mensaje):
    try:
        manager_msg = manager.send_action({
                'Action': 'Command',
                'Command': f'Show CLI message: {mensaje}',
            })
        if 'Success' in manager_msg.response[0]:
                print("Mensaje enviado correctamente")
        else:
            print(f"Error al enviar el mensaje: {manager_msg.response}")
    except ManagerException as e:
        print(f"Error al establecer la variable en el canal {canal}: {e}")
        

def send_text(manager:Manager, canal, message):
    try:
        manager.send_action({
                'Action': 'SendText',
                'Channel': canal,
                'Message': message
            })
                
    except ManagerException as e:
        print(f"Error al establecer la variable en el canal {canal}: {e}")
    finally:
        print(f"{message}")


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
        print(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        print(f"Error general: {traceback.format_exc()}")
    finally:
        # Cerrar la conexión con el servidor Asterisk
        manager.close()

def main(canal, path_file, unique_id):
    try:
        # Crear una instancia de Manager
        manager = Manager()

        # Conectar al servidor Asterisk
        manager.connect(server)
        manager.login(user, pwd)
         
        # Registrar un manejador de eventos para el evento AgentConnect
        manager.register_event('AgentConnect', lambda event, m=manager, canal=canal, path=path_file, uid=unique_id: grabaciones(event, m, canal, path, uid))
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
        manager.close()
    

if __name__ == "__main__":
    # Verificamos que se proporcionen los argumentos esperados
    if len(sys.argv) != 4:
        print("Uso: python coach.py canal path_file unique_id")
        sys.exit(1)
    
    # Obtenemos los argumentos de la línea de comandos
    canal = sys.argv[1]
    path_file = sys.argv[2]
    unique_id = sys.argv[3]
    
    main(canal, path_file, unique_id)
    
   