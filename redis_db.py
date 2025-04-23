from environs import Env

import redis
def connect_to_redis():
    env = Env()
    env.read_env()
    host = env.str("REDIS_HOST")
    port = env.int("REDIS_PORT")
    username = env.str("REDIS_USERNAME","default")
    password = env.str("REDIS_PASSWORD")
    connect = redis.Redis(
        host=host,
        port=port,
        decode_responses=True,
        username=username,
        password=password,
    )
    return connect



