from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationFailed
from app.models import Product
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate


class ProductService:
    def __init__(self, session: AsyncSession, products: ProductRepository, categories: CategoryRepository):
        self.session = session
        self.products = products
        self.categories = categories

    async def create_product(self, data: ProductCreate) -> Product:
        category = await self.categories.get(data.category_id)
        if category is None:
            raise NotFoundError(f"Category {data.category_id} does not exist")
        if not category.active:
            raise BusinessRuleError(f"Category '{category.category_code}' is inactive")
        if await self.products.get_by_code(data.product_code):
            raise ConflictError(f"Product code '{data.product_code}' already exists")

        product = Product(
            product_code=data.product_code,
            product_name=data.product_name,
            unit_price=data.unit_price,
            available_quantity=data.available_quantity,
            active=data.active,
            category=category,
        )
        try:
            await self.products.add(product)
            await self.session.commit()
        except IntegrityError:  # lost a race on the unique constraint
            await self.session.rollback()
            raise ConflictError(f"Product code '{data.product_code}' already exists")
        return product

    async def search(
        self,
        name: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        category_id: int | None,
    ) -> list[Product]:
        name = name.strip() if name else None  # blank name == omitted filter
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ValidationFailed("minPrice must not be greater than maxPrice")
        return await self.products.search(name or None, min_price, max_price, category_id)
