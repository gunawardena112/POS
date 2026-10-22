# POS Orders & Loyalty API

FastAPI · async SQLAlchemy 2.x · PostgreSQL · Pydantic v2 · Alembic

Exactly the five required endpoints:

| Method | Endpoint |
|---|---|
| POST | `/api/v1/products` |
| GET | `/api/v1/products?name=&minPrice=&maxPrice=&categoryId=` |
| POST | `/api/v1/orders` |
| GET | `/api/v1/loyalty-customers?mobileNumber=` |
| GET | `/api/v1/sales/summary?date=YYYY-MM-DD` |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # edit DATABASE_URL
createdb pos_loyalty                                    # or create the DB in Neon / pgAdmin
alembic upgrade head                                    # creates tables AND seeds categories 1-4
uvicorn app.main:app --reload
```

Docs: http://localhost:8000/docs

`DATABASE_URL` must use the asyncpg driver. For **Neon** use `?ssl=require` (not `sslmode=`):
`postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require`

The seed is part of migration `0001` (`INSERT ... ON CONFLICT DO NOTHING`, then the category
sequence is advanced past the fixed IDs), so re-running `alembic upgrade head` never duplicates rows.

## Architecture

```
routers  ->  services  ->  repositories  ->  models / DB
(HTTP)       (rules,        (queries,         (SQLAlchemy)
             transactions)   flush only)
schemas = Pydantic in/out · db/session.py = session dependency · core/exceptions.py + main.py = centralized errors
```

* Routers only call services; services own `commit()/rollback()`; repositories never commit.
* ORM entities are never returned: every response goes through a schema's `from_entity`.
* Every response uses one envelope — success `{"success": true, "message": "...", "data": ...}`,
  error `{"success": false, "error": {"code": "...", "message": "...", "details": [...]}}`.

## Request / response shapes

`POST /api/v1/products`
```json
{"productName": "Blue Pen", "productCode": "PRD002", "unitPrice": 80.00,
 "availableQuantity": 200, "active": true, "categoryId": 1}
```

`POST /api/v1/orders` (prices, totals, points, timestamp, status are server-side only)
```json
{"customer": {"fullName": "Nimal Perera", "mobileNumber": "0771234567", "email": "nimal@example.com"},
 "items": [{"productId": "<uuid>", "quantity": 2}, {"productId": "<uuid>", "quantity": 3}]}
```
Response `data`: `orderId, orderDateTime, status, customer{customerId, mobileNumber, fullName, email},
items[{productId, productCode, productName, quantity, unitPrice, subtotal}], totalAmount,
loyaltyPointsEarned, loyaltyBalance`.

Encode a leading `+` as `%2B` in URLs: `/api/v1/loyalty-customers?mobileNumber=%2B94771234567`.

## Status codes

| Situation | Code |
|---|---|
| Created product / completed order | 201 |
| Validation (bad body/query, bad mobile, minPrice > maxPrice, categoryId ≤ 0, inactive category, inactive product) | 422 |
| Unknown category / product / loyalty customer | 404 |
| Duplicate product code, insufficient stock | 409 |

## How concurrency and atomicity are handled

One request = one DB transaction, committed only at the very end of `OrderService.place_order`;
any exception triggers `rollback()`, so no partial order, stock change, enrolment or points survive.

* **Stock / overselling** – products are locked with `SELECT ... FOR UPDATE`, ordered by ID
  (consistent order ⇒ no deadlocks). Stock is validated *after* the lock, so a second order waits,
  then sees the reduced stock. A `CHECK (available_quantity >= 0)` is the last line of defence.
* **Duplicate customers** – `INSERT ... ON CONFLICT (mobile_number) DO NOTHING` on a unique
  constraint; a concurrent insert blocks until the first transaction ends, then inserts nothing.
* **Lost point updates** – the customer row is read `FOR UPDATE` before `points += earned`,
  so concurrent orders for one customer serialise. `CHECK (loyalty_points >= 0)` backs it up.
* **Existing profile** – never updated by an order; only new customers take the submitted name/email.
* **Snapshots** – `order_items.unit_price/subtotal`, `customer_orders.total_amount` and
  `loyalty_points_earned` are stored, so later price/balance changes never alter history.
* **Daily summary** – order-level sums and item-level sums are separate queries, so a multi-item
  order is counted once. Business day = `[00:00, next 00:00)` in Asia/Colombo.

## Verification

```bash
python -m scripts.verify_scenarios --reset   # DROPS the public schema of DATABASE_URL: use a throw-away DB
```
Runs 56 checks end to end against real PostgreSQL: ordering, rollback, repeat customer, points
(99.99 / 100 / 250 / 1250.75), combined filters, validation errors, Colombo day boundary, and
concurrent scenarios (12 buyers for 5 units → exactly 5 succeed; 10 simultaneous orders for a new
mobile → 1 customer, 10 points; 10 more for the existing one → exactly 20).

**Postman:** import `postman/POS_Loyalty.postman_collection.json`, set `baseUrl` (and `today`), run
folders 0 → 4 in order (it saves generated product IDs into variables and asserts status/values).
