import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LoyaltyCustomer


class CustomerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_mobile(self, mobile: str, *, for_update: bool = False) -> LoyaltyCustomer | None:
        stmt = select(LoyaltyCustomer).where(LoyaltyCustomer.mobile_number == mobile)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def insert_if_absent(self, *, mobile: str, full_name: str, email: str | None) -> None:
        """INSERT ... ON CONFLICT DO NOTHING on the unique mobile_number. A concurrent duplicate
        blocks until the first transaction finishes, then inserts nothing -> never two customers."""
        stmt = (
            pg_insert(LoyaltyCustomer)
            .values(
                customer_id=uuid.uuid4(),
                mobile_number=mobile,
                full_name=full_name,
                email=email,
                loyalty_points=0,
            )
            .on_conflict_do_nothing(index_elements=["mobile_number"])
        )
        await self.session.execute(stmt)
