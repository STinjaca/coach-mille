#!/usr/bin/python3

import threading
import traceback
import asterisk.manager
from asterisk.agi import AGI
import time

agi = AGI()

server = "localhost"
user = "telefonia"
pwd = "telefonia"


def iniciar_grabacion(manager:asterisk.manager.Manager, canal, path_file, unique_id, i):
    agi.verbose(f"Iniciando grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action' : "Monitor",
            'Channel': canal,
            'File': f'{path_file}/{unique_id}-{i}.wav',
            'Format': 'wav',
            'Mix': '1'
        })
        if manager_msg.response == 'Success':
            agi.verbose("Grabación iniciada correctamente.")
        else:
            agi.verbose("Error al iniciar la grabación")
    except asterisk.manager.ManagerException as e:
        agi.verbose(f"Error al iniciar la grabación en el canal {canal}: {e}")

def detener_grabacion(manager, canal):
    agi.verbose(f"Deteniendo grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action': 'StopMonitor',
            'Channel': canal
        })
        if manager_msg.response == 'Success':
            agi.verbose("Grabación detenida correctamente.")
        else:
            agi.verbose("Error al detener la grabación")
    except asterisk.manager.ManagerException as e:
        agi.verbose(f"Error al detener la grabación en el canal {canal}: {e}")


def main(canal_a_grabar, path_file, unique_id):
    try:
        # Crear una instancia de Manager
        manager = asterisk.manager.Manager()

        # Conectar al servidor Asterisk
        manager.connect(server)
        manager.login(user, pwd)

        i = 0
        continuar = 0
        # Bucle para iniciar grabaciones cada 5 segundos
        while continuar < 10:
            # Obtener el nombre del canal a grabar desde la variable CHANNEL_TO_RECORD            
            if canal_a_grabar:
                iniciar_grabacion(manager, canal_a_grabar, path_file, unique_id, i)
                i+=1
                time.sleep(5)  # Esperar 5 segundos antes de detener la grabación
                detener_grabacion(manager, canal_a_grabar)
            else:
                agi.verbose("No se especificó ningún canal para grabar.")
                time.sleep(5)
            continuar += 1

    except asterisk.manager.ManagerSocketException as e:
        agi.verbose(f"Error conectando al servidor Asterisk: {e}")
    except asterisk.manager.ManagerAuthException as e:
        agi.verbose(f"Error de autenticación en el servidor Asterisk: {e}")
    except asterisk.manager.ManagerException as e:
        agi.verbose(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        agi.verbose(f"Error general: {traceback.format_exc()}")
    finally:
        # Cerrar la conexión con el servidor Asterisk
        manager.close()

if __name__ == "__main__":
    # Obtenemos los argumentos de la línea de comandos
    canal_a_grabar = agi.env['agi_arg_1']
    path_file = agi.env['agi_arg_2']
    unique_id = agi.env['agi_arg_3']
    
    # Llamamos a la función principal
    threading.Thread(target=main, args=(canal_a_grabar, path_file, unique_id)).start()
    #main(canal_a_grabar, path_file, unique_id) 