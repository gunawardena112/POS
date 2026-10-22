from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomerOrder


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, order: CustomerOrder) -> CustomerOrder:
        self.session.add(order)
        await self.session.flush()
        return order
