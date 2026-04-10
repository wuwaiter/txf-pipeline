import redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB


def get_redis_client(decode_responses: bool = True) -> redis.Redis:
    """Return a connected Redis client."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=decode_responses,
    )
