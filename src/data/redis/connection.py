import redis
from redis.connection import ConnectionPool
from src.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
from src.utils.logger import logger


class RedisConnection:
    """
    Redis connection manager with connection pooling.

    Provides efficient connection pooling and automatic reconnection.
    """

    def __init__(self):
        """Initialize Redis connection pool."""
        try:
            # Create connection pool
            self.pool = ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                db=REDIS_DB,
                decode_responses=True,  # Auto decode bytes to str
                max_connections=20,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            self.client.ping()
            logger.info(f"✅ Redis connected successfully: {REDIS_HOST}:{REDIS_PORT}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    def get_client(self) -> redis.Redis:
        """
        Get Redis client instance.

        Returns:
            Redis client object
        """
        return self.client

    def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


redis_connection = RedisConnection()
