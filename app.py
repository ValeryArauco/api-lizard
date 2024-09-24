import tempfile
import requests
import zipfile
import os
import lizard  # Usamos el módulo lizard directamente
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    repo_url = data.get('repoUrl')
    
    if not repo_url:
        return jsonify({"error": "No se proporcionó el enlace del repositorio"}), 400
    
    try:
        # Convertir la URL del repositorio en una URL de descarga de ZIP
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]  # Eliminar la extensión .git
        
        download_url = f"{repo_url}/archive/refs/heads/main.zip"

        # Descargar el archivo ZIP
        response = requests.get(download_url)
        if response.status_code != 200:
            return jsonify({"error": "Error al descargar el repositorio"}), 500
        
        # Crear un directorio temporal y extraer el archivo ZIP
        with tempfile.TemporaryDirectory() as tmpdirname:
            zip_path = os.path.join(tmpdirname, 'repo.zip')
            with open(zip_path, 'wb') as zip_file:
                zip_file.write(response.content)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)

            # Ejecutar lizard en el directorio extraído
            extracted_dir = os.path.join(tmpdirname, os.listdir(tmpdirname)[0])
            
            # Analizar todos los archivos dentro del directorio extraído
            results = []
            for root, _, files in os.walk(extracted_dir):
                for file in files:
                    if file.endswith('.rb'):  # Puedes ajustar esto para otros lenguajes si es necesario
                        file_path = os.path.join(root, file)
                        analysis = lizard.analyze_file(file_path)  # Analizar archivo con lizard
                        
                        # Extraer métricas importantes
                        for func in analysis.function_list:
                            results.append({
                                "file": file_path,
                                "function_name": func.name,
                                "nloc": func.nloc,  # Número de líneas de código
                                "cyclomatic_complexity": func.cyclomatic_complexity,
                                "token_count": func.token_count,
                            })

            # Devolver el resultado del análisis
            return jsonify({"metrics": results})

    except Exception as e:
        return jsonify({"error": "Error al procesar el repositorio", "details": str(e)}), 500

if __name__ == '__main__':
    app.run()
