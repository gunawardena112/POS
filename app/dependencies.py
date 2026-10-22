from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.category_repository import CategoryRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.sales_repository import SalesRepository
from app.services.loyalty_service import LoyaltyService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.sales_service import SalesService


def get_product_service(session: AsyncSession = Depends(get_session)) -> ProductService:
    return ProductService(session, ProductRepository(session), CategoryRepository(session))


def get_loyalty_service(session: AsyncSession = Depends(get_session)) -> LoyaltyService:
    return LoyaltyService(CustomerRepository(session))


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(
        session,
        ProductRepository(session),
        OrderRepository(session),
        LoyaltyService(CustomerRepository(session)),
    )


def get_sales_service(session: AsyncSession = Depends(get_session)) -> SalesService:
    return SalesService(SalesRepository(session))
