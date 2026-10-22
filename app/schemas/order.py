from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from app.models import CustomerOrder
from app.schemas.common import CamelModel, Money


class CustomerDetails(CamelModel):
    full_name: str = Field(min_length=1, max_length=150)
    mobile_number: str = Field(min_length=1)  # normalised in the service layer
    email: EmailStr | None = None


class OrderItemRequest(CamelModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderCreate(CamelModel):
    customer: CustomerDetails
    items: list[OrderItemRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_duplicate_products(self):
        ids = [i.product_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate productId in items; each product may appear once per order")
        return self


class OrderCustomerResponse(CamelModel):
    customer_id: UUID
    mobile_number: str
    full_name: str
    email: str | None


class OrderItemResponse(CamelModel):
    product_id: UUID
    product_code: str
    product_name: str
    quantity: int
    unit_price: Money
    subtotal: Money


class OrderResponse(CamelModel):
    order_id: UUID
    order_date_time: datetime
    status: str
    customer: OrderCustomerResponse
    items: list[OrderItemResponse]
    total_amount: Money
    loyalty_points_earned: int
    loyalty_balance: int

    @classmethod
    def from_entity(cls, o: CustomerOrder) -> "OrderResponse":
        c = o.customer
        return cls(
            order_id=o.order_id,
            order_date_time=o.order_date_time,
            status=o.order_status,
            customer=OrderCustomerResponse(
                customer_id=c.customer_id, mobile_number=c.mobile_number, full_name=c.full_name, email=c.email
            ),
            items=[
                OrderItemResponse(
                    product_id=i.product_id,
                    product_code=i.product.product_code,
                    product_name=i.product.product_name,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    subtotal=i.subtotal,
                )
                for i in o.items
            ],
            total_amount=o.total_amount,
            loyalty_points_earned=o.loyalty_points_earned,
            loyalty_balance=c.loyalty_points,
        )
