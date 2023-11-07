from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy import Enum
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
from sqlalchemy.orm import relationship


class Database():

    def __init__(self, app_config):
        self.app_config = app_config
        # setup db engine and session maker
        self.db_url = app_config["library"]["db_url"]
        self.engine = create_async_engine(self.db_url, echo=True)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def begin(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()

    # ********** Generic Actions **********

    async def insert_object(self, new_object):
        async with self.async_session() as session:
            async with session.begin():
                session.add(new_object)
            session.refresh(new_object)

    async def select_object(self, object_class, object_uuid):
        async with self.async_session() as session:
            result = await session.execute(
                select(object_class)
                .where(object_class.id == object_uuid)
            )
            return result.scalar()

    async def select_all_objects(self, object_class):
        async with self.async_session() as session:
            result = await session.execute(
                select(object_class)
            )
            return result.scalars()


class Base(AsyncAttrs, DeclarativeBase):
    pass


# Media <---> Tag associations
assoc_media_tag_table = Table(
    "assoc_media_tag",
    Base.metadata,
    Column("media_id", ForeignKey("media.id"), primary_key=True),
    Column("tag_name", ForeignKey("tags.name"), primary_key=True),
)


class MediaType(enum.Enum):
    video = 1
    image = 2
    audio = 3


@dataclass
class Media(Base):
    __tablename__ = "media"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    description: Mapped[Optional[str]]
    duration: Mapped[Optional[int]]
    urls: Mapped[Optional[str]]
    type: Mapped[enum.Enum] = mapped_column(Enum(MediaType))

    tags: Mapped[list[Tag]] = relationship(
        secondary=assoc_media_tag_table, back_populates="media"
    )

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

    name: Mapped[str] = mapped_column(primary_key=True)

    media: Mapped[list[Media]] = relationship(
        secondary=assoc_media_tag_table, back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"{self.name}"
