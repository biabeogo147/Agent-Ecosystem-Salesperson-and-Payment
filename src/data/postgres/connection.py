from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import src.config as config


class PostgresConnection:
    """
    PostgreSQL connection manager using SQLAlchemy.

    Provides connection pooling and session management for database operations.
    """

    def __init__(self, database: str):
        """
        Initialize PostgreSQL connection.

        Args:
            database: Database name to connect to
        """
        user = config.POSTGRES_USER
        password = config.POSTGRES_PASSWORD
        host = config.POSTGRES_HOST
        port = config.POSTGRES_PORT

        self.engine = create_engine(
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
            pool_size=20,
            max_overflow=10
        )
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        """
        Get a new database session.

        Returns:
            SQLAlchemy Session object
        """
        return self.Session()


db_connection = PostgresConnection(database=config.POSTGRES_DB)
