import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.customer import LoyaltyCustomer


class CustomerOrder(Base):
    # "customer_orders" avoids the reserved word ORDER
    __tablename__ = "customer_orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_orders_total_non_negative"),
        CheckConstraint("loyalty_points_earned >= 0", name="ck_orders_points_non_negative"),
        CheckConstraint("order_status IN ('COMPLETED')", name="ck_orders_status_valid"),
        Index("ix_customer_orders_order_date_time", "order_date_time"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("loyalty_customers.customer_id", ondelete="RESTRICT"), index=True
    )
    order_date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    order_status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    loyalty_points_earned: Mapped[int]

    customer: Mapped[LoyaltyCustomer] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(  # noqa: F821
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.order_item_id"
    )
