from flask import Flask, request, render_template, jsonify
import googlemaps
import os
import math
from dotenv import load_dotenv
import qrcode
import random
import string

# Inicializando o Flask
app = Flask(__name__)

# Carregar a chave da API do Google Maps a partir do arquivo .env
load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("Chave da API do Google Maps não encontrada. Verifique o arquivo .env.")

# Cliente da API Google Maps
gmaps = googlemaps.Client(key=API_KEY)

def calcular_distancia(coord1, coord2):
    """
    Função para calcular a distância entre duas coordenadas usando a fórmula de Haversine.
    """
    lat1, lng1 = coord1
    lat2, lng2 = coord2
    R = 6371  # Raio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def obter_coordenadas(endereco):
    """
    Função que utiliza a API do Google Maps para obter as coordenadas geográficas (latitude e longitude)
    de um endereço.
    Caso o endereço seja inválido, sugere endereços similares.
    """
    try:
        # Solicitar a geocodificação do endereço
        geocode_result = gmaps.geocode(endereco)
        
        if geocode_result:
            # Se encontrado, retorna as coordenadas
            return (geocode_result[0]['geometry']['location']['lat'], geocode_result[0]['geometry']['location']['lng'])
        
        else:
            # Caso o endereço não seja encontrado, sugerir alternativas de endereços
            places_result = gmaps.places(endereco)
            if places_result:
                sugestao = places_result[0]['formatted_address']
                return {'error': f"Endereço não encontrado. Você quis dizer: {sugestao}?"}
            else:
                return {'error': 'Endereço não encontrado e nenhuma sugestão disponível.'}
    except Exception as e:
        return {'error': f"Erro ao buscar o endereço {endereco}: {str(e)}"}

@app.route('/')
def index():
    """
    Rota para renderizar a página inicial do formulário de endereços.
    """
    return render_template('index.html')

@app.route('/calcular-rota', methods=['POST'])
def calcular_rota():
    """
    Rota para calcular a rota entre múltiplos endereços e gerar o QR code com a rota.
    """
    enderecos = request.form.getlist('enderecos')
    print(f"Endereços recebidos: {enderecos}")

    if not enderecos:
        return jsonify({'error': 'Nenhum endereço fornecido'}), 400

    coordenadas = []
    erros = []
    for endereco in enderecos:
        coords = obter_coordenadas(endereco)
        if isinstance(coords, dict) and 'error' in coords:
            erros.append(coords['error'])  # Adicionando erro na lista
        else:
            coordenadas.append(coords)

    if len(coordenadas) < 2:
        return jsonify({'error': 'Endereços insuficientes para calcular a rota'}), 400

    if erros:
        return jsonify({'errors': erros}), 400  # Retorna todos os erros encontrados

    # Calcular a rota otimizando os endereços
    try:
        directions_result = gmaps.directions(
            origin=coordenadas[0],
            destination=coordenadas[-1],
            waypoints=coordenadas[1:-1],
            optimize_waypoints=True,
            mode="driving"
        )
        if not directions_result:
            return jsonify({'error': 'Não foi possível calcular a rota'}), 500

        # Obter a URL da rota otimizada
        route_url = f"https://www.google.com/maps/dir/?api=1&origin={coordenadas[0][0]},{coordenadas[0][1]}&destination={coordenadas[-1][0]},{coordenadas[-1][1]}&waypoints=" + '|'.join([f"{coord[0]},{coord[1]}" for coord in coordenadas[1:-1]])

    except Exception as e:
        return jsonify({'error': f'Erro ao calcular a rota: {str(e)}'}), 500

    # Verificar se a pasta 'static' existe, se não, criar
    if not os.path.exists('static'):
        os.makedirs('static')

    # Gerar QR Code com a URL da rota
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(route_url)
    qr.make(fit=True)

    # Personalizar a cor do QR code (cor do fundo e do código)
    img = qr.make_image(fill='black', back_color='white')

    # Salvar o QR Code com um nome aleatório
    qr_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) + '.png'
    img.save(os.path.join('static', qr_filename))

    return jsonify({
        'message': 'Rota calculada com sucesso',
        'url': route_url,
        'qr_code': qr_filename
    })

if __name__ == '__main__':
    app.run(debug=True)
