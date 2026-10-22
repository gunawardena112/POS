import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.category import Category


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="ck_products_unit_price_positive"),
        CheckConstraint("available_quantity >= 0", name="ck_products_stock_non_negative"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_code: Mapped[str] = mapped_column(String(50), unique=True)
    product_name: Mapped[str] = mapped_column(String(150))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    available_quantity: Mapped[int]
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), index=True
    )

    category: Mapped[Category] = relationship(back_populates="products")
