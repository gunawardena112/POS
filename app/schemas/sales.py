import datetime as dt

from app.schemas.common import CamelModel, Money


class SalesSummaryResponse(CamelModel):
    date: dt.date
    completed_order_count: int
    total_units_sold: int
    total_sales_revenue: Money
    total_loyalty_points_earned: int
