from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)
