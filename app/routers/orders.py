from fastapi import APIRouter, Depends

from app.dependencies import get_order_service
from app.schemas.common import ApiResponse
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=ApiResponse[OrderResponse], status_code=201)
async def place_order(body: OrderCreate, service: OrderService = Depends(get_order_service)):
    order = await service.place_order(body)
    return ApiResponse(message="Order completed", data=OrderResponse.from_entity(order))
