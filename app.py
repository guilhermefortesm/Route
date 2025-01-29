from flask import Flask, request, render_template, jsonify, send_from_directory
import googlemaps
import os
from geopy.geocoders import Nominatim
import math
from dotenv import load_dotenv
import qrcode
import random
import string

app = Flask(__name__)

# Carrega a chave da API do Google Maps
load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("Chave da API do Google Maps não encontrada. Verifique o arquivo .env.")

gmaps = googlemaps.Client(key=API_KEY)

def calcular_distancia(coord1, coord2):
    # Utilizando a fórmula de Haversine para calcular distância entre dois pontos
    lat1, lng1 = coord1
    lat2, lng2 = coord2
    R = 6371  # Raio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular-rota', methods=['POST'])
def calcular_rota():
    enderecos = request.form.getlist('enderecos')
    if not enderecos:
        return jsonify({'error': 'Nenhum endereço fornecido'}), 400

    coordenadas = []
    for endereco in enderecos:
        geocode_result = gmaps.geocode(endereco)
        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']
            coordenadas.append((lat, lng))
        else:
            return jsonify({'error': f'Endereço não encontrado: {endereco}'}), 404

    if len(coordenadas) < 2:
        return jsonify({'error': 'Endereços insuficientes para calcular a rota'}), 400

    # Calcula a matriz de distâncias
    matriz_distancias = [[calcular_distancia(coord1, coord2) for coord2 in coordenadas] for coord1 in coordenadas]

    # Geração do QR Code com a rota (apenas ilustrativo, supõe a primeira rota)
    route_url = f"https://www.google.com/maps/dir/?api=1&origin={coordenadas[0][0]},{coordenadas[0][1]}&destination={coordenadas[-1][0]},{coordenadas[-1][1]}&travelmode=driving"
    qr = qrcode.make(route_url)
    qr_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=10)) + '.png'
    qr.save(os.path.join('static', qr_filename))

    return jsonify({
        'message': 'Rota calculada com sucesso',
        'url': route_url,
        'qr_code': qr_filename
    })

if __name__ == '__main__':
    app.run(debug=True)
