import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from src.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
from src.utils.logger import get_current_logger


class RedisConnection:
    """
    Redis connection manager with async connection pooling.

    Provides efficient async connection pooling and automatic reconnection.
    """

    def __init__(self):
        """Initialize Redis async connection pool."""
        logger = get_current_logger()
        try:
            # Create async connection pool
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

            self.client = None
            logger.info(f"✅ Redis async connection pool initialized: {REDIS_HOST}:{REDIS_PORT}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis connection pool: {e}")
            raise

    async def get_client(self) -> redis.Redis:
        """
        Get Redis async client instance.

        Returns:
            Redis async client object
        """
        logger = get_current_logger()
        if self.client is None:
            self.client = redis.Redis(connection_pool=self.pool)
            await self.client.ping()
            logger.info(f"✅ Redis async client connected successfully")
        return self.client

    async def health_check(self) -> bool:
        """
        Check Redis connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        logger = get_current_logger()
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def close(self):
        """Close Redis connection and cleanup resources."""
        logger = get_current_logger()
        if self.client:
            await self.client.aclose()
            self.client = None
        if self.pool:
            await self.pool.aclose()
        logger.info("✅ Redis connection closed")


redis_connection = RedisConnection()
