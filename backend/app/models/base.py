import enum
from datetime import datetime

from sqlalchemy import Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Feste Namen für Schlüssel und Regeln, damit Migrationen sie gezielt ändern können
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


def enum_type(enum_class: type[enum.Enum], name: str) -> Enum:
    """Speichert die Werteliste als Text, die Datenbank lehnt unbekannte Werte ab."""
    return Enum(enum_class, name=name, native_enum=False, length=40, create_constraint=True)
