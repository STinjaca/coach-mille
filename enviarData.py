#!/usr/bin/python3

import logging
import sys
import requests

# Configuración del logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='EnviarData_ami.log',  # Nombre del archivo de log
                    filemode='w')  # 'w' para sobrescribir el archivo cada vez, 'a' para añadir

# Función para capturar excepciones no controladas
def log_uncaught_exceptions(exctype, value, tb):
    logging.critical("Unhandled exception", exc_info=(exctype, value, tb))

# Configurar sys.excepthook para usar la función anterior
sys.excepthook = log_uncaught_exceptions


def main(canal, path_file, unique_id):
    url = 'http://localhost:5039/iniciarGrabacion/'
    params = {
        'canal': canal,
        'path_file': path_file,
        'unique_id': unique_id
    }

    response = requests.get(url, params=params)
    logging.info(response)
    

if __name__ == "__main__":
    # Verificamos que se proporcionen los argumentos esperados
    if len(sys.argv) != 4:
        logging.error("Uso: python coach.py canal path_file unique_id")
        sys.exit(1)
    
    # Obtenemos los argumentos de la línea de comandos
    canal = sys.argv[1]
    path_file = sys.argv[2]
    unique_id = sys.argv[3]
    
    main(canal, path_file, unique_id)   