import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        return product

    async def get_by_code(self, code: str) -> Product | None:
        stmt = select(Product).where(Product.product_code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        name: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        category_id: int | None,
    ) -> list[Product]:
        stmt = select(Product).options(selectinload(Product.category)).order_by(Product.product_code)
        if name:
            escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Product.product_name.ilike(f"%{escaped}%", escape="\\"))
        if min_price is not None:
            stmt = stmt.where(Product.unit_price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.unit_price <= max_price)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_many_for_update(self, ids: list[uuid.UUID]) -> list[Product]:
        """SELECT ... FOR UPDATE in a deterministic order: serialises concurrent orders per product
        (no overselling) and avoids deadlocks between orders touching the same products."""
        stmt = (
            select(Product)
            .where(Product.product_id.in_(ids))
            .order_by(Product.product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list((await self.session.execute(stmt)).scalars().all())
