from flask import Flask, request, render_template, jsonify
import googlemaps
import os
import qrcode
from io import BytesIO
from dotenv import load_dotenv
import logging
import base64

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Inicializando o Flask
app = Flask(__name__)

# Carregar a chave da API do Google Maps a partir do arquivo .env
load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    logger.error("Chave da API do Google Maps não encontrada. Verifique o arquivo .env.")
    raise ValueError("Chave da API do Google Maps não encontrada. Verifique o arquivo .env.")

# Cliente da API Google Maps
gmaps = googlemaps.Client(key=API_KEY)

def obter_coordenadas(endereco):
    """
    Função para obter coordenadas de um endereço.
    Se não encontrado, tenta sugerir correções.
    """
    try:
        logger.debug(f"Geocodificando endereço: {endereco}")
        geocode_result = gmaps.geocode(endereco)
        
        if geocode_result:
            logger.debug(f"Endereço encontrado: {geocode_result[0]['formatted_address']}")
            return (geocode_result[0]['geometry']['location']['lat'], geocode_result[0]['geometry']['location']['lng'], None)
        
        logger.debug("Endereço não encontrado. Buscando sugestões...")
        places_result = gmaps.places(endereco)
        
        if places_result:
            sugestoes = [place['formatted_address'] for place in places_result[:5]]
            logger.debug(f"Sugestões encontradas: {sugestoes}")
            return (None, None, sugestoes)
        else:
            logger.debug("Nenhuma sugestão disponível.")
            return (None, None, ['Endereço não encontrado. Nenhuma sugestão disponível.'])
        
    except Exception as e:
        logger.error(f"Erro ao buscar o endereço {endereco}: {str(e)}")
        return (None, None, [f"Erro ao buscar o endereço {endereco}: {str(e)}"])

@app.route('/')
def index():
    logger.debug("Acessando a página inicial.")
    return render_template('index.html')

@app.route('/calcular-rota', methods=['POST'])
def calcular_rota():
    try:
        logger.debug("Recebendo solicitação para calcular rota.")
        data = request.get_json()
        enderecos = data.get('enderecos', [])

        if not enderecos:
            logger.error("Nenhum endereço fornecido.")
            return jsonify({'error': 'Nenhum endereço fornecido'}), 400

        coordenadas = []
        sugestoes = []
        for endereco in enderecos:
            lat, lng, sugestao = obter_coordenadas(endereco)
            if lat is None and lng is None:
                sugestoes.append(sugestao)
            else:
                coordenadas.append((lat, lng))

        if len(coordenadas) < 2:
            logger.error("Endereços insuficientes para calcular a rota.")
            return jsonify({'error': 'Endereços insuficientes para calcular a rota'}), 400

        # Otimização da rota com Google Maps
        waypoints = [f"{coord[0]},{coord[1]}" for coord in coordenadas[1:-1]]
        route_url = f"https://www.google.com/maps/dir/?api=1&origin={coordenadas[0][0]},{coordenadas[0][1]}&destination={coordenadas[-1][0]},{coordenadas[-1][1]}&waypoints=" + '|'.join(waypoints) + "&optimize_waypoints=true"
        logger.debug(f"URL da rota gerada: {route_url}")

        # Gerar o QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(route_url)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

        logger.debug("QR Code gerado com sucesso.")
        return jsonify({
            'qrcode': img_base64,
            'suggestions': sugestoes,
            'coordenadas': coordenadas,  # Retorna as coordenadas para o mapa
        })

    except Exception as e:
        logger.error(f"Erro ao calcular a rota: {str(e)}")
        return jsonify({'error': f'Erro ao calcular a rota: {str(e)}'}), 500

if __name__ == '__main__':
    logger.debug("Iniciando o servidor Flask.")
    app.run(debug=True)