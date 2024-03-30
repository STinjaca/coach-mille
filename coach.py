from flask import Flask, request, jsonify
import threading
import time

app = Flask(__name__)

grabaciones_activas = {}


def iniciar_grabacion(unique_id):
    while grabaciones_activas.get(unique_id, False):
        print(f"Iniciando nueva grabación para {unique_id}")
        # Aquí iría el código para iniciar la grabación en Asterisk
        # Supongamos que la grabación dura 5 segundos
        time.sleep(5)
        print(f"Deteniendo grabación para {unique_id}")
        # Aquí iría el código para detener la grabación en Asterisk
        grabaciones_activas[unique_id] = False

@app.route('/iniciar_grabacion/<unique_id>', methods=['POST'])
def iniciar_coach(unique_id):
    if unique_id not in grabaciones_activas:
        grabaciones_activas[unique_id] = True
        # Iniciamos la grabación en un hilo para no bloquear la aplicación
        threading.Thread(target=iniciar_grabacion, args=(unique_id,)).start()
        return jsonify({"mensaje": "Grabación iniciada"})
    else:
        return jsonify({"mensaje": "La grabación ya está en curso"})

@app.route('/terminar_grabacion/<unique_id>', methods=['POST'])
def terminar_coach(unique_id):
    if unique_id in grabaciones_activas:
        grabaciones_activas.pop(unique_id)
        return jsonify({"mensaje": "Grabación terminada"})
    else:
        return jsonify({"mensaje": "No hay grabación en curso para este ID único"})

if __name__ == '__main__':
    app.run(debug=True)
