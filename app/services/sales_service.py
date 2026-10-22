from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.repositories.sales_repository import SalesRepository
from app.schemas.sales import SalesSummaryResponse

CENT = Decimal("0.01")


class SalesService:
    def __init__(self, sales: SalesRepository):
        self.sales = sales

    async def daily_summary(self, day: date) -> SalesSummaryResponse:
        tz = ZoneInfo(settings.business_timezone)  # Asia/Colombo business day
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)  # exclusive
        count, revenue, points, units = await self.sales.totals(start, end)
        return SalesSummaryResponse(
            date=day,
            completed_order_count=count,
            total_units_sold=units,
            total_sales_revenue=revenue.quantize(CENT),
            total_loyalty_points_earned=points,
        )
