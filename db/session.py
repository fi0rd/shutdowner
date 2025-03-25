from sqlmodel import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import CONFIG

__all__ = ("engine",
           "engine_sync",
           "async_session")


engine_sync = create_engine(CONFIG['db']['url_sync'], echo=True)
engine = create_async_engine(CONFIG['db']['url'], echo=True)

async_session = async_sessionmaker(bind=engine,
                                   autoflush=False,
                                   autocommit=False,
                                   expire_on_commit=False,
                                   )
