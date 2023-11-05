import uuid
from dataclasses import dataclass
from typing import Optional

# Column types
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import Text
from sqlalchemy import Uuid
# SQL commands
from sqlalchemy import insert
from sqlalchemy import select
# SQLAlchemy AsyncIO requirements
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
# SQLAlchemy ORM requirements
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Database():

    def __init__(self, db_url, library_path):
        self.library_path = library_path
        self.engine = create_async_engine(db_url, echo=True)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def begin(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        for i in range(10):
            await self.insert_object(Media(filename=f"test{i}.mp4", title=f"test{i}"))

    async def close(self) -> None:
        await self.engine.dispose()

    # ********** Generic Actions **********

    async def insert_object(self, new_object):
        async with self.async_session() as session:
            async with session.begin():
                session.add(new_object)

    async def select_object(self, object_class, object_uuid):
        async with self.async_session() as session:
            result = await session.execute(
                select(object_class)
                # .where(object_class.id == object_uuid)
            )
            return result.scalar()

    async def select_all_objects(self, object_class):
        async with self.async_session() as session:
            result = await session.execute(
                select(object_class)
            )
            return result.scalars()

    # ********** Media Actions **********

    async def import_media(self):
        pass


class Base(AsyncAttrs, DeclarativeBase):
    pass


@dataclass
class Media(Base):
    __tablename__ = "media"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    description: Mapped[Optional[str]]
    duration: Mapped[Optional[int]]
    urls: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"{self.title} [{self.filename}]"


@dataclass
class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str]

    def __repr__(self) -> str:
        return f"{self.name}"


@dataclass
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str]

    def __repr__(self) -> str:
        return f"{self.name}"


@dataclass
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str]

    def __repr__(self) -> str:
        return f"{self.name}"
