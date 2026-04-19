from __future__ import annotations
from datetime import datetime
from typing import List

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

# Pure-Python password hashing (no bcrypt builds needed)
from passlib.hash import pbkdf2_sha256 as _pwd

from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    @staticmethod
    def make(username: str, password: str, role: str = "user") -> "User":
        return User(username=username, password_hash=_pwd.hash(password), role=role)

    def verify(self, password: str) -> bool:
        return _pwd.verify(password, self.password_hash)

class Map(Base):
    __tablename__ = "maps"
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    geojson: Mapped[str] = mapped_column(Text, nullable=True)
    areaData: Mapped[str] = mapped_column(Text, nullable=True)
    imgSrc: Mapped[str] = mapped_column(Text, nullable=True)
    imgW: Mapped[int] = mapped_column(Integer, nullable=True)
    imgH: Mapped[int] = mapped_column(Integer, nullable=True)

    versions: Mapped[List["MapVersion"]] = relationship(
        back_populates="map", cascade="all, delete-orphan"
    )

class MapVersion(Base):
    __tablename__ = "map_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mapName: Mapped[str] = mapped_column(
        String(100), ForeignKey("maps.name", ondelete="CASCADE")
    )
    geojson: Mapped[str] = mapped_column(Text, nullable=True)
    areaData: Mapped[str] = mapped_column(Text, nullable=True)
    imgSrc: Mapped[str] = mapped_column(Text, nullable=True)
    imgW: Mapped[int] = mapped_column(Integer, nullable=True)
    imgH: Mapped[int] = mapped_column(Integer, nullable=True)
    savedAt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    map: Mapped["Map"] = relationship(back_populates="versions")

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mapName: Mapped[str] = mapped_column(String(100), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    geojson: Mapped[str] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
