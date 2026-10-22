from fastapi import APIRouter, Depends, Query

from app.dependencies import get_loyalty_service
from app.schemas.common import ApiResponse
from app.schemas.customer import CustomerResponse
from app.services.loyalty_service import LoyaltyService

router = APIRouter(prefix="/loyalty-customers", tags=["Loyalty Customers"])


@router.get("", response_model=ApiResponse[CustomerResponse])
async def find_loyalty_customer(
    mobile_number: str = Query(..., alias="mobileNumber", description="07XXXXXXXX or +947XXXXXXXX (encode + as %2B)"),
    service: LoyaltyService = Depends(get_loyalty_service),
):
    customer = await service.find_by_mobile(mobile_number)
    return ApiResponse(data=CustomerResponse.from_entity(customer))
