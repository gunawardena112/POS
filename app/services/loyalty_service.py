from decimal import Decimal

from app.core.exceptions import NotFoundError
from app.core.mobile import normalize_mobile
from app.models import LoyaltyCustomer
from app.repositories.customer_repository import CustomerRepository

POINT_UNIT = Decimal("100")


def calculate_points(total: Decimal) -> int:
    """floor(total / 100) on the whole bill; the remainder is discarded, never carried over."""
    return int(total // POINT_UNIT)


class LoyaltyService:
    def __init__(self, customers: CustomerRepository):
        self.customers = customers

    async def find_by_mobile(self, mobile: str) -> LoyaltyCustomer:
        canonical = normalize_mobile(mobile)
        customer = await self.customers.get_by_mobile(canonical)
        if customer is None:
            raise NotFoundError(f"No loyalty customer found for {canonical}")
        return customer

    async def resolve_or_enroll_locked(
        self, *, mobile: str, full_name: str, email: str | None
    ) -> LoyaltyCustomer:
        """Return the customer row-locked (FOR UPDATE). Enrols with 0 points if new.
        An existing customer's name/email are never overwritten."""
        customer = await self.customers.get_by_mobile(mobile, for_update=True)
        if customer is None:
            await self.customers.insert_if_absent(mobile=mobile, full_name=full_name, email=email)
            customer = await self.customers.get_by_mobile(mobile, for_update=True)
        return customer

    @staticmethod
    def credit(customer: LoyaltyCustomer, points: int) -> None:
        # Safe read-modify-write: the row is locked by resolve_or_enroll_locked until commit.
        customer.loyalty_points += points
