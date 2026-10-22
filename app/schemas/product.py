from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models import Product
from app.schemas.common import CamelModel, Money


class ProductCreate(CamelModel):
    product_name: str = Field(min_length=1, max_length=150)
    product_code: str = Field(min_length=1, max_length=50)
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    available_quantity: int = Field(ge=0)
    active: bool = True
    category_id: int = Field(gt=0)


class ProductResponse(CamelModel):
    product_id: UUID
    product_name: str
    product_code: str
    unit_price: Money
    available_quantity: int
    active: bool
    category_id: int
    category_name: str

    @classmethod
    def from_entity(cls, p: Product) -> "ProductResponse":
        return cls(
            product_id=p.product_id,
            product_name=p.product_name,
            product_code=p.product_code,
            unit_price=p.unit_price,
            available_quantity=p.available_quantity,
            active=p.active,
            category_id=p.category_id,
            category_name=p.category.category_name,
        )
