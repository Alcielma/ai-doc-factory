import redis

from app import config

# Conexão Redis compartilhada pelos routers.
r = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
