from datetime import date

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_sales_service
from app.schemas.common import ApiResponse
from app.schemas.sales import SalesSummaryResponse
from app.services.sales_service import SalesService

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/summary", response_model=ApiResponse[SalesSummaryResponse])
async def sales_summary(
    day: date = Query(..., alias="date", description="ISO date YYYY-MM-DD (Asia/Colombo business day)"),
    service: SalesService = Depends(get_sales_service),
):
    return ApiResponse(data=await service.daily_summary(day))
