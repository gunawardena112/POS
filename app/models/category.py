from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    # Integer PK => SERIAL. Seed rows use fixed IDs 1-4; setup script realigns the sequence.
    category_id: Mapped[int] = mapped_column(primary_key=True)
    category_code: Mapped[str] = mapped_column(String(50), unique=True)
    category_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    products = relationship("Product", back_populates="category")
