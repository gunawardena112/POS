from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomerOrder, OrderItem


class SalesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def totals(self, start: datetime, end: datetime) -> tuple[int, Decimal, int, int]:
        """Returns (order_count, revenue, points, units) for COMPLETED orders in [start, end).

        Order-level sums and item-level sums are separate queries on purpose: joining
        orders -> items and summing total_amount would multiply revenue/points by item count."""
        in_range = (
            CustomerOrder.order_date_time >= start,
            CustomerOrder.order_date_time < end,
            CustomerOrder.order_status == "COMPLETED",
        )
        count, revenue, points = (
            await self.session.execute(
                select(
                    func.count(CustomerOrder.order_id),
                    func.coalesce(func.sum(CustomerOrder.total_amount), 0),
                    func.coalesce(func.sum(CustomerOrder.loyalty_points_earned), 0),
                ).where(*in_range)
            )
        ).one()
        units = (
            await self.session.execute(
                select(func.coalesce(func.sum(OrderItem.quantity), 0))
                .join(CustomerOrder, CustomerOrder.order_id == OrderItem.order_id)
                .where(*in_range)
            )
        ).scalar_one()
        return int(count), Decimal(revenue), int(points), int(units)
