from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import event
# Metadata
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

    async def insert_object(self, session, new_object):
        session.add(new_object)

    async def select_object(self, session, object_class, object_uuid):
        result = await session.execute(
            select(object_class)
            .where(object_class.id == object_uuid)
        )
        return result.scalar()

    async def select_all_objects(self, session, object_class):
        result = await session.execute(
            select(object_class)
        )
        return result.scalars()

    # ********** Access Helpers **********

    async def get_or_create_tag(self, session, tag_name):
        # try obtaining
        result = await session.execute(
            select(Tag)
            .where(Tag.name == tag_name)
        )
        result = result.scalar()
        if result is not None:
            return result
        # create and insert
        new_tag = Tag(name=tag_name)
        session.add(new_tag)
        return new_tag


class Base(AsyncAttrs, DeclarativeBase):
    pass


# Media <---> Collection associations
assoc_media_collection_table = Table(
    "assoc_media_collection",
    Base.metadata,
    Column("media_id", ForeignKey("media.id"), primary_key=True),
    Column("collection_id", ForeignKey("collections.id"), primary_key=True),
)

# Media <---> Person associations
assoc_media_person_table = Table(
    "assoc_media_person",
    Base.metadata,
    Column("media_id", ForeignKey("media.id"), primary_key=True),
    Column("person_id", ForeignKey("people.id"), primary_key=True),
)

# Media <---> Organization associations
assoc_media_organization_table = Table(
    "assoc_media_organization",
    Base.metadata,
    Column("media_id", ForeignKey("media.id"), primary_key=True),
    Column("organization_id", ForeignKey("organizations.id"), primary_key=True),
)

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

    id: Mapped[str] = mapped_column(Uuid, primary_key=True)
    filename: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    description: Mapped[Optional[str]]
    duration: Mapped[Optional[int]]
    urls: Mapped[Optional[str]]
    type: Mapped[enum.Enum] = mapped_column(Enum(MediaType))

    collections: Mapped[set[Collection]] = relationship(
        secondary=assoc_media_collection_table, back_populates="media"
    )
    people: Mapped[set[Person]] = relationship(
        secondary=assoc_media_person_table, back_populates="media"
    )
    organizations: Mapped[set[Organization]] = relationship(
        secondary=assoc_media_organization_table, back_populates="media"
    )
    tags: Mapped[set[Tag]] = relationship(
        secondary=assoc_media_tag_table, back_populates="media"
    )

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return 0 if self.id is None else self.id.int

    def __repr__(self) -> str:
        return f"{self.title} [{self.filename}]"


@dataclass
class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(primary_key=True)
    password_hash: Mapped[str]
    display_name: Mapped[str]
    description: Mapped[Optional[str]]


class CollectionType(enum.Enum):
    playlist = 1
    series = 2
    album = 3


@dataclass
class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str]
    description: Mapped[Optional[str]]
    type: Mapped[enum.Enum] = mapped_column(Enum(CollectionType))

    media: Mapped[set[Media]] = relationship(
        secondary=assoc_media_collection_table, back_populates="collections"
    )

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return 0 if self.id is None else self.id.int

    def __repr__(self) -> str:
        return f"{self.name}"


@dataclass
class Person(Base):
    __tablename__ = "people"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str]

    media: Mapped[set[Media]] = relationship(
        secondary=assoc_media_person_table, back_populates="people"
    )

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return 0 if self.id is None else self.id.int

    def __repr__(self) -> str:
        return f"{self.name}"


@dataclass
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str]

    media: Mapped[set[Media]] = relationship(
        secondary=assoc_media_organization_table, back_populates="organizations"
    )

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return 0 if self.id is None else self.id.int

    def __repr__(self) -> str:
        return f"{self.name}"


@dataclass
class Tag(Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(primary_key=True)

    media: Mapped[set[Media]] = relationship(
        secondary=assoc_media_tag_table, back_populates="tags"
    )

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self) -> str:
        return f"{self.name}"
