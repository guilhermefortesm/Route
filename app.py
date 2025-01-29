from flask import Flask, request, render_template, jsonify, send_file
import googlemaps
import os
import math
from dotenv import load_dotenv
import qrcode
import random
import string
from io import BytesIO

# Inicializando o Flask
app = Flask(__name__)

# Carregar a chave da API do Google Maps a partir do arquivo .env
load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("Chave da API do Google Maps não encontrada. Verifique o arquivo .env.")

# Cliente da API Google Maps
gmaps = googlemaps.Client(key=API_KEY)

def obter_coordenadas(endereco):
    """
    Função para obter coordenadas de um endereço.
    Se não encontrado, tenta sugerir correções.
    """
    try:
        # Tentando geocodificar o endereço
        geocode_result = gmaps.geocode(endereco)
        
        if geocode_result:
            return (geocode_result[0]['geometry']['location']['lat'], geocode_result[0]['geometry']['location']['lng'], None)
        
        # Se o endereço não foi encontrado, sugerir alternativas com places
        places_result = gmaps.places(endereco)
        
        if places_result:
            sugestoes = []
            for place in places_result[:5]:  # Limita a 5 sugestões
                sugestoes.append(place['formatted_address'])
            return (None, None, sugestoes)  # Retorna sugestões para o front-end
        else:
            return (None, None, ['Endereço não encontrado. Nenhuma sugestão disponível.'])
        
    except Exception as e:
        return (None, None, [f"Erro ao buscar o endereço {endereco}: {str(e)}"])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular-rota', methods=['POST'])
def calcular_rota():
    enderecos = request.form.getlist('enderecos')

    if not enderecos:
        return jsonify({'error': 'Nenhum endereço fornecido'}), 400

    coordenadas = []
    erros = []
    sugestoes = []
    for endereco in enderecos:
        lat, lng, sugestao = obter_coordenadas(endereco)
        if lat is None and lng is None:
            # Se o endereço é inválido ou não encontrado, guardamos as sugestões
            sugestoes.append(sugestao)
        else:
            coordenadas.append((lat, lng))

    if len(coordenadas) < 2:
        return jsonify({'error': 'Endereços insuficientes para calcular a rota'}), 400

    # Sempre geramos o QR code, independentemente de erros nos endereços
    try:
        # Gera a URL da rota com o Google Maps
        route_url = f"https://www.google.com/maps/dir/?api=1&origin={coordenadas[0][0]},{coordenadas[0][1]}&destination={coordenadas[-1][0]},{coordenadas[-1][1]}&waypoints=" + '|'.join([f"{coord[0]},{coord[1]}" for coord in coordenadas[1:-1]])

    except Exception as e:
        return jsonify({'error': f'Erro ao calcular a rota: {str(e)}'}), 500

    # Gerar o QR Code com a URL da rota
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(route_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    # Salvar a imagem em memória usando BytesIO
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    # Retornar a imagem do QR Code
    return jsonify({
        'qrcode': img_io.getvalue().decode('latin1'),  # Encodifica a imagem como base64
        'suggestions': sugestoes,
    })

if __name__ == '__main__':
    app.run(debug=True)
