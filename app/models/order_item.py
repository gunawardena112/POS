import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.order import CustomerOrder
from app.models.product import Product


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_items_quantity_positive"),
        CheckConstraint("unit_price > 0", name="ck_items_unit_price_positive"),
        CheckConstraint("subtotal >= 0", name="ck_items_subtotal_non_negative"),
        UniqueConstraint("order_id", "product_id", name="uq_items_order_product"),
    )

    order_item_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_orders.order_id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.product_id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # snapshot at order time
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))  # snapshot at order time

    order: Mapped[CustomerOrder] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
