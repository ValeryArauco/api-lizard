import tempfile
import requests
import zipfile
import os
import lizard
from flask import Flask, request, jsonify
import logging
import re
from urllib.parse import urlparse
 
app = Flask(__name__)
 
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
 
def parse_repo_url(repo_url):
    """
    Parse the GitHub repo URL to extract the base repo URL and the ref (branch or commit).
    Returns a tuple (base_repo_url, ref).
    """
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
 
    if len(path_parts) < 2:
        raise ValueError("URL del repositorio inválida.")
 
    username = path_parts[0]
    repo = path_parts[1]

    if repo.endswith('.git'):
        repo = repo[:-4]


    base_repo_url = f"https://github.com/{username}/{repo}"
 
    ref = None
    if len(path_parts) > 3 and path_parts[2] == 'commit':
        ref = path_parts[3]
    elif len(path_parts) > 3 and path_parts[2] == 'tree':
        ref = path_parts[3]
 
    return base_repo_url, ref
 
def is_commit(ref):
    """
    Determine if the ref is a commit hash.
    """
    return bool(re.fullmatch(r'[0-9a-fA-F]{40}', ref))
 
@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    repo_url = data.get('repoUrl')
 
    if not repo_url:
        logging.debug("No se proporcionó el enlace del repositorio.")
        return jsonify({"error": "No se proporcionó el enlace del repositorio"}), 400
 
    try:
        base_repo_url, ref = parse_repo_url(repo_url)
        logging.debug(f"Base repo URL: {base_repo_url}")
        logging.debug(f"Ref: {ref}")
 
        download_urls = []
 
        if ref:
            if is_commit(ref):
                download_url = f"{base_repo_url}/archive/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para commit: {download_url}")
            else:
                download_url = f"{base_repo_url}/archive/refs/heads/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para rama: {download_url}")
        else:
            download_urls = [
                f"{base_repo_url}/archive/refs/heads/main.zip",
                f"{base_repo_url}/archive/refs/heads/master.zip"
            ]
            logging.debug("No se especificó ref, intentando con main y master.")
 
        response = None
        for url in download_urls:
            logging.debug(f"Intentando descargar el repositorio desde: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                logging.debug(f"Descarga exitosa desde: {url}")
                break
            else:
                logging.debug(f"Falló la descarga desde: {url} con estado {response.status_code}")
        else:
            return jsonify({"error": "Error al descargar el repositorio"}), 500
 
        with tempfile.TemporaryDirectory() as tmpdirname:
            zip_path = os.path.join(tmpdirname, 'repo.zip')
            with open(zip_path, 'wb') as zip_file:
                zip_file.write(response.content)
            logging.debug(f"Archivo ZIP descargado en: {zip_path}")
 
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
            logging.debug(f"Archivo ZIP extraído en: {tmpdirname}")
 
 
            extracted_dirs = [d for d in os.listdir(tmpdirname) if os.path.isdir(os.path.join(tmpdirname, d))]
            if not extracted_dirs:
                logging.debug("No se encontraron directorios después de extraer el ZIP.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400
            extracted_dir = os.path.join(tmpdirname, extracted_dirs[0])
            logging.debug(f"Directorio extraído: {extracted_dir}")
 
            extensions = ['.cs', '.java', '.js', '.ts', '.kts', '.py', '.rb', '.cpp', '.c', '.php', '.go', '.rs']
            results = []
 
            found_files = False
            for root, _, files in os.walk(extracted_dir):
                logging.debug(f"Revisando directorio: {root}")
                for file in files:
                    logging.debug(f"Archivo encontrado: {file}")
                    if any(file.endswith(ext) for ext in extensions):
                        found_files = True
                        file_path = os.path.join(root, file)
                        logging.debug(f"Analizando archivo: {file_path}")
                        analysis = lizard.analyze_file(file_path)
 
                        for func in analysis.function_list:
                            results.append({
                                "file": file_path,
                                "function_name": func.name,
                                "nloc": func.nloc,
                                "cyclomatic_complexity": func.cyclomatic_complexity,
                                "token_count": func.token_count,
                            })
 
            if not found_files:
                logging.debug("No se encontraron archivos con extensiones compatibles.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400
 
            return jsonify({"metrics": results})
 
    except Exception as e:
        logging.error(f"Error al procesar el repositorio: {str(e)}")
        return jsonify({"error": "Error al procesar el repositorio", "details": str(e)}), 500
 

# Definimos el umbral de complejidad ciclomatica alta
HIGH_COMPLEXITY_THRESHOLD = 5

@app.route('/analyze_commit', methods=['POST'])
def analyze_commit():
    data = request.get_json()
    repo_url = data.get('repoUrl')
 
    if not repo_url:
        logging.debug("No se proporcionó el enlace del repositorio.")
        return jsonify({"error": "No se proporcionó el enlace del repositorio"}), 400
 
    try:
        base_repo_url, ref = parse_repo_url(repo_url)
        logging.debug(f"Base repo URL: {base_repo_url}")
        logging.debug(f"Ref: {ref}")
 
        download_urls = []
 
        if ref:
            if is_commit(ref):
                download_url = f"{base_repo_url}/archive/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para commit: {download_url}")
            else:
                download_url = f"{base_repo_url}/archive/refs/heads/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para rama: {download_url}")
        else:
            download_urls = [
                f"{base_repo_url}/archive/refs/heads/main.zip",
                f"{base_repo_url}/archive/refs/heads/master.zip"
            ]
            logging.debug("No se especificó ref, intentando con main y master.")
 
        response = None
        for url in download_urls:
            logging.debug(f"Intentando descargar el repositorio desde: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                logging.debug(f"Descarga exitosa desde: {url}")
                break
            else:
                logging.debug(f"Falló la descarga desde: {url} con estado {response.status_code}")
        else:
            return jsonify({"error": "Error al descargar el repositorio"}), 500
 
        with tempfile.TemporaryDirectory() as tmpdirname:
            zip_path = os.path.join(tmpdirname, 'repo.zip')
            with open(zip_path, 'wb') as zip_file:
                zip_file.write(response.content)
            logging.debug(f"Archivo ZIP descargado en: {zip_path}")
 
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
            logging.debug(f"Archivo ZIP extraído en: {tmpdirname}")
 
 
            extracted_dirs = [d for d in os.listdir(tmpdirname) if os.path.isdir(os.path.join(tmpdirname, d))]
            if not extracted_dirs:
                logging.debug("No se encontraron directorios después de extraer el ZIP.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400
            extracted_dir = os.path.join(tmpdirname, extracted_dirs[0])
            logging.debug(f"Directorio extraído: {extracted_dir}")
 
            extensions = ['.cs', '.java', '.js', '.ts', '.kts', '.py', '.rb', '.cpp', '.c', '.php', '.go', '.rs']
            results = []
            high_complexity_functions = []
 
            found_files = False
            for root, _, files in os.walk(extracted_dir):
                logging.debug(f"Revisando directorio: {root}")
                for file in files:
                    logging.debug(f"Archivo encontrado: {file}")
                    if any(file.endswith(ext) for ext in extensions):
                        found_files = True
                        file_path = os.path.join(root, file)
                        logging.debug(f"Analizando archivo: {file_path}")
                        analysis = lizard.analyze_file(file_path)
 
                        for func in analysis.function_list:
                            result = {
                                "file": file_path,
                                "function_name": func.name,
                                "cyclomatic_complexity": func.cyclomatic_complexity
                            }
                            # Si la complejidad ciclomatica es alta, la añadimos a la lista
                            if func.cyclomatic_complexity >= HIGH_COMPLEXITY_THRESHOLD:
                                high_complexity_functions.append(result)
                            results.append(result)
 
            if not found_files:
                logging.debug("No se encontraron archivos con extensiones compatibles.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400
 
            if high_complexity_functions:
                return jsonify({"high_complexity_functions": high_complexity_functions})

            # Si todas las funciones tienen baja complejidad, devolvemos un mensaje simple
            return jsonify({"message": "Complejidad ciclomatica baja en todas las funciones"})
 
    except Exception as e:
        logging.error(f"Error al procesar el repositorio: {str(e)}")
        return jsonify({"error": "Error al procesar el repositorio", "details": str(e)}), 500




@app.route('/average_ccn', methods=['POST'])
def average_ccn():
    data = request.get_json()
    repo_url = data.get('repoUrl')

    if not repo_url:
        logging.debug("No se proporcionó el enlace del repositorio.")
        return jsonify({"error": "No se proporcionó el enlace del repositorio"}), 400

    try:
        base_repo_url, ref = parse_repo_url(repo_url)
        logging.debug(f"Base repo URL: {base_repo_url}")
        logging.debug(f"Ref: {ref}")

        download_urls = []

        if ref:
            if is_commit(ref):
                download_url = f"{base_repo_url}/archive/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para commit: {download_url}")
            else:
                download_url = f"{base_repo_url}/archive/refs/heads/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para rama: {download_url}")
        else:
            download_urls = [
                f"{base_repo_url}/archive/refs/heads/main.zip",
                f"{base_repo_url}/archive/refs/heads/master.zip"
            ]
            logging.debug("No se especificó ref, intentando con main y master.")

        response = None
        for url in download_urls:
            logging.debug(f"Intentando descargar el repositorio desde: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                logging.debug(f"Descarga exitosa desde: {url}")
                break
            else:
                logging.debug(f"Falló la descarga desde: {url} con estado {response.status_code}")
        else:
            return jsonify({"error": "Error al descargar el repositorio"}), 500

        with tempfile.TemporaryDirectory() as tmpdirname:
            zip_path = os.path.join(tmpdirname, 'repo.zip')
            with open(zip_path, 'wb') as zip_file:
                zip_file.write(response.content)
            logging.debug(f"Archivo ZIP descargado en: {zip_path}")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
            logging.debug(f"Archivo ZIP extraído en: {tmpdirname}")

            extracted_dirs = [d for d in os.listdir(tmpdirname) if os.path.isdir(os.path.join(tmpdirname, d))]
            if not extracted_dirs:
                logging.debug("No se encontraron directorios después de extraer el ZIP.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400
            extracted_dir = os.path.join(tmpdirname, extracted_dirs[0])
            logging.debug(f"Directorio extraído: {extracted_dir}")

            extensions = ['.cs', '.java', '.js', '.ts', '.kts', '.py', '.rb', '.cpp', '.c', '.php', '.go', '.rs']
            total_ccn = 0
            function_count = 0

            found_files = False
            for root, _, files in os.walk(extracted_dir):
                logging.debug(f"Revisando directorio: {root}")
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        found_files = True
                        file_path = os.path.join(root, file)
                        logging.debug(f"Analizando archivo: {file_path}")
                        analysis = lizard.analyze_file(file_path)

                        for func in analysis.function_list:
                            total_ccn += func.cyclomatic_complexity
                            function_count += 1

            if not found_files:
                logging.debug("No se encontraron archivos con extensiones compatibles.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400

            if function_count == 0:
                return jsonify({"message": "No se encontraron funciones para calcular el promedio"}), 400

            average_ccn = total_ccn / function_count
            return jsonify({"average_cyclomatic_complexity": average_ccn})

    except Exception as e:
        logging.error(f"Error al procesar el repositorio: {str(e)}")
        return jsonify({"error": "Error al procesar el repositorio", "details": str(e)}), 500


@app.route('/combined_analysis', methods=['POST'])
def combined_analysis():
    data = request.get_json()
    repo_url = data.get('repoUrl')

    if not repo_url:
        logging.debug("No se proporcionó el enlace del repositorio.")
        return jsonify({"error": "No se proporcionó el enlace del repositorio"}), 400

    try:
        base_repo_url, ref = parse_repo_url(repo_url)
        logging.debug(f"Base repo URL: {base_repo_url}")
        logging.debug(f"Ref: {ref}")

        download_urls = []

        if ref:
            if is_commit(ref):
                download_url = f"{base_repo_url}/archive/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para commit: {download_url}")
            else:
                download_url = f"{base_repo_url}/archive/refs/heads/{ref}.zip"
                download_urls.append(download_url)
                logging.debug(f"URL de descarga para rama: {download_url}")
        else:
            download_urls = [
                f"{base_repo_url}/archive/refs/heads/main.zip",
                f"{base_repo_url}/archive/refs/heads/master.zip"
            ]
            logging.debug("No se especificó ref, intentando con main y master.")

        response = None
        for url in download_urls:
            logging.debug(f"Intentando descargar el repositorio desde: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                logging.debug(f"Descarga exitosa desde: {url}")
                break
            else:
                logging.debug(f"Falló la descarga desde: {url} con estado {response.status_code}")
        else:
            return jsonify({"error": "Error al descargar el repositorio"}), 500

        with tempfile.TemporaryDirectory() as tmpdirname:
            zip_path = os.path.join(tmpdirname, 'repo.zip')
            with open(zip_path, 'wb') as zip_file:
                zip_file.write(response.content)
            logging.debug(f"Archivo ZIP descargado en: {zip_path}")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
            logging.debug(f"Archivo ZIP extraído en: {tmpdirname}")

            extracted_dirs = [d for d in os.listdir(tmpdirname) if os.path.isdir(os.path.join(tmpdirname, d))]
            if not extracted_dirs:
                logging.debug("No se encontraron directorios después de extraer el ZIP.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400
            extracted_dir = os.path.join(tmpdirname, extracted_dirs[0])
            logging.debug(f"Directorio extraído: {extracted_dir}")

            extensions = ['.cs', '.java', '.js', '.ts', '.kts', '.py', '.rb', '.cpp', '.c', '.php', '.go', '.rs']
            results = []
            high_complexity_functions = []
            total_ccn = 0
            function_count = 0

            found_files = False
            for root, _, files in os.walk(extracted_dir):
                logging.debug(f"Revisando directorio: {root}")
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        found_files = True
                        file_path = os.path.join(root, file)
                        logging.debug(f"Analizando archivo: {file_path}")
                        analysis = lizard.analyze_file(file_path)

                        for func in analysis.function_list:
                            result = {
                                "file": file_path,
                                "function_name": func.name,
                                "cyclomatic_complexity": func.cyclomatic_complexity
                            }
                            results.append(result)

                            total_ccn += func.cyclomatic_complexity
                            function_count += 1

                            if func.cyclomatic_complexity >= HIGH_COMPLEXITY_THRESHOLD:
                                high_complexity_functions.append(result)

            if not found_files:
                logging.debug("No se encontraron archivos con extensiones compatibles.")
                return jsonify({"error": "No se encontraron archivos compatibles"}), 400


            average_ccn = total_ccn / function_count if function_count > 0 else 0

            response_data = {
                "high_complexity_functions": high_complexity_functions,
                "average_cyclomatic_complexity": average_ccn
            }

            return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error al procesar el repositorio: {str(e)}")
        return jsonify({"error": "Error al procesar el repositorio", "details": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)
 
 
# curl -X POST http://127.0.0.1:5000/analyze -H "Content-Type: application/json" -d "{\"repoUrl\": \"https://github.com/ValeryArauco/prueba.git\"}"
# curl -X POST http://127.0.0.1:5000/analyze -H "Content-Type: application/json" -d "{\"repoUrl\": \"https://github.com/ibmg25/api-tiendita.git\"}"
# curl -X POST http://127.0.0.1:5000/analyze -H "Content-Type: application/json" -d "{\"repoUrl\": \"https://github.com/ibmg25/api-tiendita/commit/683bbbb2d6375080407ac33bca258ae3e7b37d77\"}"