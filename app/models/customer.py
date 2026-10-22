import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoyaltyCustomer(Base):
    __tablename__ = "loyalty_customers"
    __table_args__ = (
        CheckConstraint("loyalty_points >= 0", name="ck_customers_points_non_negative"),
        CheckConstraint(r"mobile_number ~ '^\+947[0-9]{8}$'", name="ck_customers_mobile_canonical"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mobile_number: Mapped[str] = mapped_column(String(13), unique=True)  # text, never numeric
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(254))
    loyalty_points: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
