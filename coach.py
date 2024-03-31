from flask import Flask, request, jsonify
import threading
import time
import threading
import traceback
import asterisk.manager
import time

app = Flask(__name__)

grabaciones_activas = {}

server = "localhost"
user = "telefonia"
pwd = "telefonia"


def iniciar_grabacion(manager:asterisk.manager.Manager, canal, path_file, unique_id, i):
    print(f"Iniciando grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action' : "Monitor",
            'Channel': canal,
            'File': f'{path_file}/{unique_id}-{i}.wav',
            'Format': 'wav',
            'Mix': '1'
        })
        if manager_msg.response == 'Success':
            print("Grabación iniciada correctamente.")
        else:
            print(f"Error al iniciar la grabación: {manager_msg.response}")
    except asterisk.manager.ManagerException as e:
        print(f"Error al iniciar la grabación en el canal {canal}: {e}")

def detener_grabacion(manager, canal):
    print(f"Deteniendo grabación en el canal {canal}")
    try:
        manager_msg = manager.send_action({
            'Action': 'StopMonitor',
            'Channel': canal
        })
        if manager_msg.response == 'Success':
            print("Grabación detenida correctamente.")
        else:
            print(f"Error al detener la grabación: {manager_msg.response}")
    except asterisk.manager.ManagerException as e:
        print(f"Error al detener la grabación en el canal {canal}: {e}")


def control_grabacion(canal_a_grabar, path_file, unique_id):
    try:
        # Crear una instancia de Manager
        manager = asterisk.manager.Manager()

        # Conectar al servidor Asterisk
        manager.connect(server)
        manager.login(user, pwd)

        i = 0
        # Bucle para iniciar grabaciones cada 5 segundos
        while grabaciones_activas.get(canal_a_grabar,False):
            # Obtener el nombre del canal a grabar desde la variable CHANNEL_TO_RECORD            
            if canal_a_grabar:
                iniciar_grabacion(manager, canal_a_grabar, path_file, unique_id, i)
                i+=1
                time.sleep(5)  # Esperar 5 segundos antes de detener la grabación
                detener_grabacion(manager, canal_a_grabar)
            else:
                print("No se especificó ningún canal para grabar.")
                time.sleep(5)

    except asterisk.manager.ManagerSocketException as e:
        print(f"Error conectando al servidor Asterisk: {e}")
    except asterisk.manager.ManagerAuthException as e:
        print(f"Error de autenticación en el servidor Asterisk: {e}")
    except asterisk.manager.ManagerException as e:
        print(f"Error general en el servidor Asterisk: {e}")
    except Exception as e:
        print(f"Error general: {traceback.format_exc()}")
    finally:
        # Cerrar la conexión con el servidor Asterisk
        manager.close()


@app.route('/iniciar_grabacion/', methods=['POST'])
def iniciar_coach():
    if request.args is None:
        return jsonify({"mensaje": "No se proporcionaron datos JSON en la solicitud"}), 400
    
    canal_a_grabar = request.args.get('canal_a_grabar')
    path_file = request.args.get('path_file')
    unique_id = request.args.get('unique_id')

    print(canal_a_grabar, path_file, unique_id)
    if canal_a_grabar is None or path_file is None or unique_id is None:
        return jsonify({"mensaje": "Faltan atributos necesarios"}), 400

    if unique_id not in grabaciones_activas:
        grabaciones_activas[unique_id] = True
        # Iniciamos la grabación en un hilo para no bloquear la aplicación
        threading.Thread(target=control_grabacion, args=(canal_a_grabar, path_file, unique_id)).start()
        return jsonify({"mensaje": "Grabación iniciada"})
    else:
        return jsonify({"mensaje": "La grabación ya está en curso"})
    

@app.route('/terminar_grabacion/', methods=['POST'])
def terminar_coach():
    if request.args is None:
        return jsonify({"mensaje": "No se proporcionaron datos JSON en la solicitud"})
    canal_a_grabar = request.args.get('canal_a_grabar')
    if canal_a_grabar in grabaciones_activas:
        grabaciones_activas.pop(canal_a_grabar)
        return jsonify({"mensaje": "Grabación terminada"})
    else:
        return jsonify({"mensaje": "No hay grabación en curso para este ID único"})

if __name__ == '__main__':
    app.run(debug=True)
