#!/usr/bin/python3

import os
import sys
import threading
import logging
from asterisk.manager import Manager, Event, ManagerException

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#Credenciales Manager
server = "localhost"
user = "telefonia"
pwd = "telefonia"

# Configuración de la API y rutas de los archivos de grabación
url_api = "http://10.72.180.6:8090"
url_start = "coachVirtual"  # Endpoint para iniciar grabación
url_end = "end_session"  # Endpoint para terminar grabación

# Tiempo de grabación en segundos
seg_grabacion = 2

response_json_anterior = {}

def set_var(manager, canal, variable, value):
    """ Establece una variable en un canal específico usando AMI """
    manager.send_action({
        'Action': 'Setvar',
        'Channel': canal,
        'Variable': variable,
        'Value': value
    })
    logging.info(f"Set var {variable}={value} on {canal}")

def iniciar_grabacion(manager, canal, archivo):
    """ Inicia la grabación en un canal específico """
    manager.send_action({
        'Action': 'MixMonitor',
        'Channel': canal,
        'File': archivo,
        'Format': 'wav',
        'Options': 'bW(2)'
    })
    logging.info(f"Iniciando grabación en {canal}, archivo: {archivo}")

def detener_grabacion(manager, canal):
    """ Detiene la grabación en un canal específico """
    manager.send_action({
        'Action': 'StopMixMonitor',
        'Channel': canal
    })
    logging.info(f"Deteniendo grabación en {canal}")

def enviar_grabacion(manager, canal, archivo):
    """ Envia la grabación a una API externa """
    logging.info(f"Enviando grabación de {canal}, archivo: {archivo} a la API")

def handle_newexten(event, canal, path_file, unique_id, manager):
    """ Maneja el evento Newexten para iniciar grabaciones """
    logging.info(f"Manejando evento Newexten: {canal}")
    archivo = f"{path_file}/coach-{unique_id}.wav"
    iniciar_grabacion(manager, canal, archivo)

def main(canal, path_file, unique_id):
    manager = Manager()

    
    
    manager.register_event('Newexten', lambda event, c=canal, p=path_file, u=unique_id, m=manager: handle_newexten(event, c, p, u, m))
    manager.event_dispatch()
    logging.info("Escuchando eventos Newexten...")
    
    try:
        # Mantener el script en ejecución indefinidamente para escuchar eventos
        while True:
            pass
    except KeyboardInterrupt:
        logging.info("Deteniendo el script.")
    finally:
        manager.logoff()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        logging.error("Uso: python coach.py canal path_file unique_id")
        sys.exit(1)

    canal = sys.argv[1]
    path_file = sys.argv[2]
    unique_id = sys.argv[3]

    main(canal, path_file, unique_id)