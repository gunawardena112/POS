from datetime import datetime
from uuid import UUID

from app.models import LoyaltyCustomer
from app.schemas.common import CamelModel


class CustomerResponse(CamelModel):
    customer_id: UUID
    mobile_number: str
    full_name: str
    email: str | None
    registered_at: datetime
    loyalty_points: int

    @classmethod
    def from_entity(cls, c: LoyaltyCustomer) -> "CustomerResponse":
        return cls.model_validate(c)
