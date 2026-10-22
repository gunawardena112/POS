from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, InsufficientStockError, NotFoundError
from app.core.mobile import normalize_mobile
from app.models import CustomerOrder, OrderItem
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate
from app.services.loyalty_service import LoyaltyService, calculate_points

CENT = Decimal("0.01")


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        products: ProductRepository,
        orders: OrderRepository,
        loyalty: LoyaltyService,
    ):
        self.session = session
        self.products = products
        self.orders = orders
        self.loyalty = loyalty

    async def place_order(self, req: OrderCreate) -> CustomerOrder:
        mobile = normalize_mobile(req.customer.mobile_number)  # fail fast, before touching the DB
        try:
            order = await self._place_order(req, mobile)
            await self.session.commit()  # ONE transaction: order, items, stock, customer, points
            return order
        except Exception:
            await self.session.rollback()  # nothing partial survives
            raise

    async def _place_order(self, req: OrderCreate, mobile: str) -> CustomerOrder:
        # 1) Lock all requested products in a fixed order (prevents overselling and deadlocks)
        ids = [i.product_id for i in req.items]
        by_id = {p.product_id: p for p in await self.products.get_many_for_update(ids)}

        # 2) Validate everything before changing anything
        missing = [str(i) for i in ids if i not in by_id]
        if missing:
            raise NotFoundError(f"Product(s) not found: {', '.join(missing)}")

        total = Decimal("0.00")
        lines: list[OrderItem] = []
        for item in req.items:
            product = by_id[item.product_id]
            if not product.active:
                raise BusinessRuleError(f"Product '{product.product_code}' is inactive and cannot be sold")
            if product.available_quantity < item.quantity:
                raise InsufficientStockError(
                    f"Insufficient stock for '{product.product_code}': "
                    f"requested {item.quantity}, available {product.available_quantity}"
                )
            subtotal = (product.unit_price * item.quantity).quantize(CENT)  # server-side price
            total += subtotal
            lines.append(
                OrderItem(product=product, quantity=item.quantity, unit_price=product.unit_price, subtotal=subtotal)
            )

        # 3) Resolve / enrol the loyalty customer (row-locked)
        customer = await self.loyalty.resolve_or_enroll_locked(
            mobile=mobile, full_name=req.customer.full_name, email=req.customer.email
        )

        # 4) Apply changes
        for item in req.items:
            by_id[item.product_id].available_quantity -= item.quantity
        points = calculate_points(total)
        self.loyalty.credit(customer, points)

        order = CustomerOrder(
            customer=customer,
            order_status="COMPLETED",
            total_amount=total,
            loyalty_points_earned=points,
            items=lines,
        )
        return await self.orders.add(order)
