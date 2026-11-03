from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppMeta(Base):
    """Small key/value table used for application metadata.

    Its main purpose in Phase 0 is to prove the MySQL + Alembic wiring works
    end to end without introducing any domain feature ahead of schedule.
    """

    __tablename__ = "app_meta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meta_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    meta_value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
