import redis
import os

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')  # Configuração de Redis do Heroku ou local
cache = redis.from_url(redis_url)