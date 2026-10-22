"""End-to-end verification of the exam scenarios + concurrency, against a REAL PostgreSQL DB.

    python -m scripts.verify_scenarios --reset

WARNING: --reset DROPS the whole public schema, then re-applies Alembic migrations.
Use a throw-away database.
"""
import asyncio
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, select, text, update

from app.core.config import settings
from app.db.session import SessionFactory, engine
from app.main import app
from app.models import Category, LoyaltyCustomer, Product

API = "/api/v1"
failures: list[str] = []


def D(x) -> Decimal:
    return Decimal(str(x))


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}{'  -> ' + detail if (detail and not ok) else ''}")
    if not ok:
        failures.append(label)


def migrate() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, capture_output=True)


async def main() -> None:
    if "--reset" not in sys.argv:
        sys.exit("Refusing to run without --reset (it drops the public schema). Use a throw-away DB.")
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    migrate()
    migrate()  # repeatability: second run must be a harmless no-op
    async with SessionFactory() as s:
        n = (await s.execute(select(func.count()).select_from(Category))).scalar_one()
    check("seed categories: exactly 4 after running migrations twice", n == 4)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:

        async def mk(code, name, price, stock, cat, active=True):
            return await c.post(f"{API}/products", json={
                "productName": name, "productCode": code, "unitPrice": price,
                "availableQuantity": stock, "active": active, "categoryId": cat})

        ids: dict[str, str] = {}
        for code, name, price, stock, cat, active in [
            ("PRD001", "Notebook A5", "350.00", 100, 1, True),
            ("PRD002", "Blue Pen", "80.00", 200, 1, True),
            ("PRD003", "Stapler", "1250.00", 25, 2, True),
            ("PRD004", "Paper Pack", "1800.00", 0, 2, True),
            ("PRD005", "Calculator", "2500.00", 10, 3, False),
        ]:
            r = await mk(code, name, price, stock, cat, active)
            check(f"create {code} -> 201 with category info",
                  r.status_code == 201 and r.json()["data"]["categoryName"] and r.json()["success"] is True, r.text)
            ids[code] = r.json()["data"]["productId"]

        # ---- product validation ----
        r = await mk("PRD001", "Dup", "10.00", 1, 1)
        check("duplicate product code -> 409", r.status_code == 409 and r.json()["success"] is False, r.text)
        check("inactive category 4 -> 422", (await mk("X1", "x", "1.00", 1, 4)).status_code == 422)
        check("missing category 999 -> 404", (await mk("X2", "x", "1.00", 1, 999)).status_code == 404)
        check("price 0 -> 422", (await mk("X3", "x", "0", 1, 1)).status_code == 422)
        check("negative stock -> 422", (await mk("X4", "x", "1.00", -1, 1)).status_code == 422)
        check("blank name -> 422", (await mk("X5", "   ", "1.00", 1, 1)).status_code == 422)

        # ---- search ----
        P = f"{API}/products"
        r = await c.get(P, params={"name": "pen", "minPrice": 50, "maxPrice": 200, "categoryId": 1})
        check("combined filters -> Blue Pen only", [p["productName"] for p in r.json()["data"]] == ["Blue Pen"], r.text)
        r = await c.get(P)
        check("no filters -> all 5 incl. inactive & out-of-stock", len(r.json()["data"]) == 5)
        r = await c.get(P, params={"name": "  NOTE  "})
        check("name is trimmed + case-insensitive", [p["productCode"] for p in r.json()["data"]] == ["PRD001"])
        r = await c.get(P, params={"name": "   "})
        check("blank name == omitted filter", len(r.json()["data"]) == 5)
        r = await c.get(P, params={"categoryId": 77})
        check("unknown positive categoryId -> empty list", r.status_code == 200 and r.json()["data"] == [])
        check("minPrice > maxPrice -> 422", (await c.get(P, params={"minPrice": 200, "maxPrice": 100})).status_code == 422)
        check("categoryId 0 -> 422", (await c.get(P, params={"categoryId": 0})).status_code == 422)
        check("malformed minPrice -> 422", (await c.get(P, params={"minPrice": "abc"})).status_code == 422)
        check("negative minPrice -> 422", (await c.get(P, params={"minPrice": -1})).status_code == 422)

        # ---- orders ----
        def order(mobile, items, name="Test Customer", email=None):
            cust = {"fullName": name, "mobileNumber": mobile}
            if email:
                cust["email"] = email
            return c.post(f"{API}/orders", json={
                "customer": cust, "items": [{"productId": ids[k], "quantity": q} for k, q in items]})

        r1 = await order("077 123-4567", [("PRD001", 2), ("PRD002", 3)], email="first@example.com")
        j1 = r1.json()["data"]
        check("order 1: 201, Rs 940.00, 9 pts, +94771234567, COMPLETED",
              r1.status_code == 201 and D(j1["totalAmount"]) == D("940.00") and j1["loyaltyPointsEarned"] == 9
              and j1["customer"]["mobileNumber"] == "+94771234567" and j1["status"] == "COMPLETED"
              and j1["loyaltyBalance"] == 9, r1.text)
        check("order 1 item snapshots", [(D(i["unitPrice"]), D(i["subtotal"])) for i in j1["items"]]
              == [(D("350.00"), D("700.00")), (D("80.00"), D("240.00"))] or
              sorted((D(i["unitPrice"]), D(i["subtotal"])) for i in j1["items"])
              == sorted([(D("350.00"), D("700.00")), (D("80.00"), D("240.00"))]))
        st = {p["productCode"]: p["availableQuantity"] for p in (await c.get(P)).json()["data"]}
        check("stock 98 / 197 after order 1", (st["PRD001"], st["PRD002"]) == (98, 197), str(st))

        r2 = await order("+94771234567", [("PRD003", 1)], name="Someone Else", email="other@example.com")
        j2 = r2.json()["data"]
        check("order 2 (repeat customer): Rs 1250.00, 12 pts, balance 21",
              D(j2["totalAmount"]) == D("1250.00") and j2["loyaltyPointsEarned"] == 12
              and j2["loyaltyBalance"] == 21 and j2["customer"]["customerId"] == j1["customer"]["customerId"], r2.text)
        check("existing profile NOT overwritten by later order",
              j2["customer"]["fullName"] == "Test Customer" and j2["customer"]["email"] == "first@example.com")

        L = f"{API}/loyalty-customers"
        r = await c.get(L, params={"mobileNumber": "0771234567"})
        d = r.json()["data"]
        check("lookup (local format) -> 21 points, same customer",
              d["loyaltyPoints"] == 21 and d["customerId"] == j1["customer"]["customerId"] and "registeredAt" in d, r.text)
        r = await c.get(f"{L}?mobileNumber=%2B94771234567")
        check("lookup (%2B encoded plus) works", r.status_code == 200 and r.json()["data"]["loyaltyPoints"] == 21)
        check("lookup unknown valid number -> 404", (await c.get(L, params={"mobileNumber": "0700000000"})).status_code == 404)
        check("lookup malformed -> 422", (await c.get(L, params={"mobileNumber": "12345"})).status_code == 422)
        check("lookup missing param -> 422", (await c.get(L)).status_code == 422)
        async with SessionFactory() as s:
            ncust = (await s.execute(select(func.count()).select_from(LoyaltyCustomer))).scalar_one()
        check("exactly one customer so far", ncust == 1)

        # ---- failures: full rollback ----
        r = await order("0779999999", [("PRD001", 1), ("PRD004", 1)], name="Ghost")
        check("notebook + out-of-stock Paper Pack -> 409", r.status_code == 409 and r.json()["error"]["code"] == "insufficient_stock", r.text)
        st = {p["productCode"]: p["availableQuantity"] for p in (await c.get(P)).json()["data"]}
        check("rollback: Notebook stock unchanged (98)", st["PRD001"] == 98)
        check("rollback: Ghost customer not enrolled", (await c.get(L, params={"mobileNumber": "0779999999"})).status_code == 404)
        check("inactive Calculator -> 422", (await order("0771234567", [("PRD005", 1)])).status_code == 422)
        check("unknown product id -> 404", (await c.post(f"{API}/orders", json={
            "customer": {"fullName": "A", "mobileNumber": "0771234567"},
            "items": [{"productId": "11111111-1111-1111-1111-111111111111", "quantity": 1}]})).status_code == 404)
        r = await c.post(f"{API}/orders", json={"customer": {"fullName": "A", "mobileNumber": "0771234567"},
                         "items": [{"productId": ids["PRD001"], "quantity": 1}, {"productId": ids["PRD001"], "quantity": 2}]})
        check("duplicate productId in request -> 422", r.status_code == 422)
        check("quantity 0 -> 422", (await order("0771234567", [("PRD001", 0)])).status_code == 422)
        check("bad mobile on order -> 422", (await order("0661234567", [("PRD001", 1)])).status_code == 422)
        check("missing full name -> 422", (await order("0771234567", [("PRD001", 1)], name="")).status_code == 422)
        check("empty items -> 422", (await c.post(f"{API}/orders", json={"customer": {"fullName": "A", "mobileNumber": "0771234567"}, "items": []})).status_code == 422)
        r = await c.get(L, params={"mobileNumber": "0771234567"})
        check("loyalty balance still 21 after all failed orders", r.json()["data"]["loyaltyPoints"] == 21)

        # ---- daily summary (Asia/Colombo) ----
        today = datetime.now(ZoneInfo(settings.business_timezone)).date().isoformat()
        S = f"{API}/sales/summary"
        r = await c.get(S, params={"date": today})
        s = r.json()["data"]
        check("summary: 2 orders, 6 units, Rs 2190.00, 21 pts (no multiplication by items)",
              (s["completedOrderCount"], s["totalUnitsSold"], D(s["totalSalesRevenue"]), s["totalLoyaltyPointsEarned"])
              == (2, 6, D("2190.00"), 21), r.text)
        s = (await c.get(S, params={"date": "2000-01-01"})).json()["data"]
        check("summary: empty day -> zeros", (s["completedOrderCount"], s["totalUnitsSold"], D(s["totalSalesRevenue"]), s["totalLoyaltyPointsEarned"]) == (0, 0, 0, 0))
        check("summary: missing date -> 422", (await c.get(S)).status_code == 422)
        check("summary: malformed date -> 422", (await c.get(S, params={"date": "18-10-2026"})).status_code == 422)

        # business-day boundary: an order stamped 23:30 Colombo belongs to that day, 00:00 to the next
        from app.models import CustomerOrder
        async with SessionFactory() as sess:
            o = (await sess.execute(select(CustomerOrder).limit(1))).scalar_one()
            o.order_date_time = datetime(2026, 1, 1, 23, 59, 59, tzinfo=ZoneInfo("Asia/Colombo"))
            await sess.commit()
        a = (await c.get(S, params={"date": "2026-01-01"})).json()["data"]["completedOrderCount"]
        b = (await c.get(S, params={"date": "2026-01-02"})).json()["data"]["completedOrderCount"]
        check("Colombo day boundary respected (23:59:59 -> Jan 1 only)", (a, b) == (1, 0), f"{a},{b}")

        # ---- points rounding incl. fractional ----
        for code, price in [("T9999", "99.99"), ("T100", "100.00"), ("T250", "250.00"), ("T1250", "1250.75")]:
            ids[code] = (await mk(code, code, price, 5, 1)).json()["data"]["productId"]
        got = [(await order("0788888888", [(code, 1)])).json()["data"]["loyaltyPointsEarned"] for code in ("T9999", "T100", "T250", "T1250")]
        check("99.99 / 100.00 / 250.00 / 1250.75 earn 0 / 1 / 2 / 12", got == [0, 1, 2, 12], str(got))

        # ---- historical snapshot ----
        async with SessionFactory() as sess:
            await sess.execute(update(Product).where(Product.product_code == "PRD002").values(unit_price=Decimal("999.00")))
            await sess.commit()
        async with SessionFactory() as sess:
            tot = (await sess.execute(text("select total_amount from customer_orders where order_id = :i"), {"i": j1["orderId"]})).scalar_one()
        check("later price change leaves historical order total at 940.00", tot == Decimal("940.00"))

        # ---- concurrency ----
        ids["CONC1"] = (await mk("CONC1", "Scarce", "10.00", 5, 1)).json()["data"]["productId"]
        res = await asyncio.gather(*[order(f"07700000{i:02d}", [("CONC1", 1)]) for i in range(12)])
        ok = sum(1 for x in res if x.status_code == 201)
        left = {p["productCode"]: p["availableQuantity"] for p in (await c.get(P)).json()["data"]}["CONC1"]
        check("12 concurrent buyers, stock 5: exactly 5 succeed, stock 0 (no oversell)", ok == 5 and left == 0, f"ok={ok} left={left}")
        check("losers got 409 (not 500)", all(x.status_code in (201, 409) for x in res))
        async with SessionFactory() as s:
            ghosts = (await s.execute(text("select count(*) from loyalty_customers where mobile_number like '+9477000%'"))).scalar_one()
        check("failed concurrent orders enrolled no customers (only 5 winners)", ghosts == 5, str(ghosts))

        ids["CONC2"] = (await mk("CONC2", "Plentiful", "100.00", 100, 1)).json()["data"]["productId"]
        res = await asyncio.gather(*[order("0712345678", [("CONC2", 1)]) for _ in range(10)])
        r = await c.get(L, params={"mobileNumber": "0712345678"})
        async with SessionFactory() as s:
            dup = (await s.execute(select(func.count()).where(LoyaltyCustomer.mobile_number == "+94712345678"))).scalar_one()
        check("10 concurrent orders, same NEW mobile: 1 customer, 10 points, no lost update",
              all(x.status_code == 201 for x in res) and dup == 1 and r.json()["data"]["loyaltyPoints"] == 10,
              f"dup={dup} pts={r.json()['data'].get('loyaltyPoints')}")
        res = await asyncio.gather(*[order("0712345678", [("CONC2", 1)]) for _ in range(10)])
        r = await c.get(L, params={"mobileNumber": "0712345678"})
        check("10 more concurrent orders, EXISTING customer: balance exactly 20", r.json()["data"]["loyaltyPoints"] == 20, str(r.json()))

        # ---- error format / unknown route ----
        r = await c.get(f"{API}/nope")
        check("unknown route -> consistent JSON 404", r.status_code == 404 and r.json()["success"] is False)

    await engine.dispose()
    print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: {failures}")
    sys.exit(1 if failures else 0)


asyncio.run(main())
