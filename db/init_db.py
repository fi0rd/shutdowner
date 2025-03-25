from sqlmodel import SQLModel
from db.session import engine


__all__ = ("init_db",
           )


async def init_db():
    async with engine.begin() as conn:
        # TODO: don't use drop_all, create_all in prod, use alembic
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
