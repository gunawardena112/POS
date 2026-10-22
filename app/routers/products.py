from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_product_service
from app.schemas.common import ApiResponse
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ApiResponse[ProductResponse], status_code=201)
async def create_product(body: ProductCreate, service: ProductService = Depends(get_product_service)):
    product = await service.create_product(body)
    return ApiResponse(message="Product created", data=ProductResponse.from_entity(product))


@router.get("", response_model=ApiResponse[list[ProductResponse]])
async def search_products(
    name: str | None = Query(None, description="Case-insensitive partial match (trimmed)"),
    min_price: Decimal | None = Query(None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(None, alias="maxPrice", ge=0),
    category_id: int | None = Query(None, alias="categoryId", gt=0),
    service: ProductService = Depends(get_product_service),
):
    products = await service.search(name, min_price, max_price, category_id)
    return ApiResponse(data=[ProductResponse.from_entity(p) for p in products])
