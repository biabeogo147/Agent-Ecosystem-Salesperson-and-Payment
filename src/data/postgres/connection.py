from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import src.config as config
from src.utils.logger import get_current_logger


class PostgresConnection:
    """
    PostgreSQL async connection manager using SQLAlchemy.

    Provides async connection pooling and session management for database operations.
    """

    def __init__(self, database: str):
        """
        Initialize PostgreSQL async connection.

        Args:
            database: Database name to connect to
        """
        logger = get_current_logger()
        user = config.POSTGRES_USER
        password = config.POSTGRES_PASSWORD
        host = config.POSTGRES_HOST
        port = config.POSTGRES_PORT

        self.engine = create_async_engine(
            f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}",
            pool_size=20,
            max_overflow=10,
            echo=False,  # Set to True for SQL query logging
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info(f"✅ PostgreSQL async engine initialized: {host}:{port}/{database}")

    def get_session(self) -> AsyncSession:
        """
        Get a new async database session.

        Returns:
            SQLAlchemy AsyncSession object
        """
        return self.AsyncSessionLocal()

    async def close(self):
        """Close database engine and cleanup resources."""
        logger = get_current_logger()
        await self.engine.dispose()
        logger.info("✅ PostgreSQL async engine disposed")


db_connection = PostgresConnection(database=config.POSTGRES_DB)
