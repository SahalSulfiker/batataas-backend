from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

RAZORPAY_PAYMENT_LINK = os.environ.get('RAZORPAY_PAYMENT_LINK', 'https://razorpay.me/@inthishamusman')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'batatas2025')

app = FastAPI(title="Batatas API")
api_router = APIRouter(prefix="/api")


# ===== STATIC DATA =====
MENU = {
    "Signature": [
        {"id": "chicken-loaded", "name": "Chicken Loaded Fries", "price": 180, "desc": "Crispy fries smothered with spicy chicken, cheese and sauces.", "image": "https://images.pexels.com/photos/20535803/pexels-photo-20535803.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"},
        {"id": "sausage-loaded", "name": "Sausage Loaded Fries", "price": 200, "desc": "Loaded with juicy sausages, cheese, and smoky sauces.", "image": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?auto=format&fit=crop&w=900&q=80"},
        {"id": "machos", "name": "Machos", "price": 210, "desc": "Nacho-style loaded fries — cheesy, crunchy, irresistible.", "image": "https://images.unsplash.com/photo-1582169296194-e4d644c48063?auto=format&fit=crop&w=900&q=80"},
        {"id": "beef-smash-loaded", "name": "Smash Beef Loaded Fries", "price": 230, "desc": "Smashed beef, melted cheese and signature sauce over fries.", "image": "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?auto=format&fit=crop&w=900&q=80"},
    ],
    "Snacks": [
        {"id": "exotic-fries", "name": "Exotic French Fries", "price": 80, "desc": "Golden, crispy fries served with your favorite dipping sauce.", "image": "https://images.pexels.com/photos/19264378/pexels-photo-19264378.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"},
        {"id": "cheesy-fries", "name": "Cheesy French Fries", "price": 135, "desc": "Crispy fries loaded with molten cheese and dipping sauce.", "image": "https://images.unsplash.com/photo-1585109649139-366815a0d713?auto=format&fit=crop&w=900&q=80"},
        {"id": "peri-fries", "name": "Peri Peri French Fries", "price": 90, "desc": "Golden fries tossed in fiery peri peri seasoning.", "image": "https://images.pexels.com/photos/1583884/pexels-photo-1583884.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"},
    ],
    "Bites": [
        {"id": "nugget-bites", "name": "Nugget Bites", "price": 130, "desc": "Crispy chicken nuggets tossed in signature peri peri seasoning.", "image": "https://images.unsplash.com/photo-1562967914-608f82629710?auto=format&fit=crop&w=900&q=80"},
        {"id": "peri-wings", "name": "Peri Wings", "price": 150, "desc": "Spicy peri peri wings — a fiery combo you can't resist.", "image": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&w=900&q=80"},
    ],
    "Fried Chicken": [
        {"id": "fc-2pc", "name": "2 Piece Fried Chicken", "price": 160, "desc": "Two pieces of golden, juicy hand-breaded fried chicken.", "image": "https://images.pexels.com/photos/33037756/pexels-photo-33037756.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"},
        {"id": "fc-5pc", "name": "5 Piece Fried Chicken", "price": 270, "desc": "Five pieces of golden, crunchy fried chicken to share.", "image": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?auto=format&fit=crop&w=900&q=80"},
        {"id": "fc-10pc", "name": "10 Piece Fried Chicken", "price": 520, "desc": "A full bucket of crispy golden fried chicken.", "image": "https://images.unsplash.com/photo-1513185041617-8ab03f83d6c5?auto=format&fit=crop&w=900&q=80"},
        {"id": "fc-20pc", "name": "20 Piece Fried Chicken", "price": 1020, "desc": "The ultimate feast — twenty pieces for the whole squad.", "image": "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=900&q=80"},
    ],
    "Chicken Strips": [
        {"id": "cs-4pc", "name": "4 Piece Chicken Strips", "price": 160, "desc": "Tender, crispy chicken strips with dipping sauce.", "image": "https://images.unsplash.com/photo-1606755962773-d324e0a13086?auto=format&fit=crop&w=900&q=80"},
        {"id": "cs-8pc", "name": "8 Piece Chicken Strips", "price": 300, "desc": "Eight golden strips — crispy on the outside, juicy inside.", "image": "https://images.unsplash.com/photo-1644095116287-90acc27ea58a?auto=format&fit=crop&w=900&q=80"},
    ],
    "Burgers": [
        {"id": "zinger", "name": "Zinger Burger", "price": 150, "desc": "Crispy spiced chicken fillet with fresh lettuce and creamy mayo.", "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=80"},
        {"id": "beef-smash", "name": "Beef Smash Burger", "price": 170, "desc": "Smashed beef patty, melted cheese and our signature sauce.", "image": "https://images.pexels.com/photos/36741809/pexels-photo-36741809.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"},
    ],
    "Drinks": [
        {"id": "lime-juice", "name": "Lime Juice", "price": 25, "desc": "Freshly squeezed lime juice — zesty and refreshing.", "image": "https://images.unsplash.com/photo-1621263764928-df1444c5e859?auto=format&fit=crop&w=900&q=80"},
        {"id": "mint-lime", "name": "Mint Lime Juice", "price": 30, "desc": "Cool mint meets zesty lime.", "image": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=900&q=80"},
        {"id": "mango-juice", "name": "Mango Juice", "price": 70, "desc": "Thick, sweet, sun-ripened mango.", "image": "https://images.unsplash.com/photo-1546171753-97d7676e4602?auto=format&fit=crop&w=900&q=80"},
        {"id": "strawberry-juice", "name": "Strawberry Juice", "price": 70, "desc": "Fresh strawberries blended smooth.", "image": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?auto=format&fit=crop&w=900&q=80"},
        {"id": "chikku-juice", "name": "Chikku Juice", "price": 70, "desc": "Creamy sapodilla shake — a tropical classic.", "image": "https://images.unsplash.com/photo-1623065422902-30a2d299bbe4?auto=format&fit=crop&w=900&q=80"},
        {"id": "passion-mojito", "name": "Passion Fruit Mojito", "price": 90, "desc": "Passion fruit, mint, lime — the ultimate refresher.", "image": "https://images.pexels.com/photos/7491891/pexels-photo-7491891.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"},
        {"id": "mint-mojito", "name": "Mint Lime Mojito", "price": 90, "desc": "Classic minty-lime mojito — cool, crisp, iconic.", "image": "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=900&q=80"},
        {"id": "blue-mojito", "name": "Blue Curaçao Mojito", "price": 90, "desc": "Tropical blue curaçao swirled with mint and lime.", "image": "https://images.unsplash.com/photo-1595981234058-a9302fb97229?auto=format&fit=crop&w=900&q=80"},
        {"id": "cold-coffee", "name": "Cold Coffee", "price": 90, "desc": "Rich, creamy and ice-cold — the perfect pick-me-up.", "image": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=80"},
    ],
    "Soft Drinks": [
        {"id": "pepsi", "name": "Pepsi", "price": 40, "desc": "Chilled Pepsi — the classic fizz.", "image": "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?auto=format&fit=crop&w=900&q=80"},
        {"id": "7up", "name": "7UP", "price": 40, "desc": "Crisp, lemony 7UP — ice cold.", "image": "https://images.unsplash.com/photo-1624552184280-9e9631bbeee9?auto=format&fit=crop&w=900&q=80"},
    ],
    "Add-ons": [
        {"id": "peri-seasoning", "name": "Peri Peri Seasoning", "price": 10, "desc": "Extra peri peri punch for your fries.", "image": "https://images.unsplash.com/photo-1599050751795-6cdaafbc2319?auto=format&fit=crop&w=900&q=80"},
        {"id": "cheese-slice", "name": "Cheese Slice", "price": 20, "desc": "Add a layer of melty cheese.", "image": "https://images.unsplash.com/photo-1552767059-ce182ead6c1b?auto=format&fit=crop&w=900&q=80"},
        {"id": "extra-wings", "name": "Extra Wings", "price": 35, "desc": "Two extra peri peri wings on the side.", "image": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&w=900&q=80"},
    ],
}

BRANCHES = [
    {"id": "wandoor", "name": "Wandoor", "address": "Opp CH Button House, Wandoor", "phone": "+919061160269", "map": "https://www.google.com/maps/search/?api=1&query=Bataatas+Wandoor", "status": "open"},
    {"id": "manjeri", "name": "Manjeri", "address": "KP Tower, Thurakkal Bypass, Manjeri", "phone": "+918111980269", "map": "https://www.google.com/maps/search/?api=1&query=Bataatas+Manjeri", "status": "open"},
    {"id": "mampad", "name": "Mampad", "address": "Mampad, Kerala", "phone": "", "map": "https://maps.app.goo.gl/jUpvhTXLrgJT8Vpq5", "status": "open"},
    {"id": "dubai", "name": "Dubai", "address": "Coming Soon", "phone": "", "map": "", "status": "coming_soon"},
]


def build_menu_lookup():
    lookup = {}
    for cat, items in MENU.items():
        for it in items:
            lookup[it["id"]] = {**it, "category": cat}
    return lookup


MENU_LOOKUP = build_menu_lookup()
OPEN_BRANCH_IDS = {b["id"] for b in BRANCHES if b["status"] == "open"}


# ===== MODELS =====
class CartItem(BaseModel):
    id: str
    qty: int = Field(gt=0, le=99)


class OrderCreate(BaseModel):
    items: List[CartItem]
    order_type: Literal["delivery", "dine-in"] = "delivery"
    payment_method: Literal["online", "cod", "counter"]
    branch: str
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = ""
    notes: Optional[str] = ""


class OrderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    short_id: str
    amount_paise: int
    amount: int
    currency: str
    payment_method: str
    payment_link: Optional[str] = None
    status: str
    items: list
    order_type: str
    branch: str


class FranchiseEnquiry(BaseModel):
    name: str
    phone: str
    city: str
    message: Optional[str] = ""


class AdminLogin(BaseModel):
    password: str


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]


def require_admin(x_admin_password: Optional[str] = Header(default=None)):
    if not x_admin_password or x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ===== ROUTES =====
@api_router.get("/")
async def root():
    return {"message": "Batatas API", "ok": True}


@api_router.get("/config")
async def get_config():
    return {"payment_link": RAZORPAY_PAYMENT_LINK}


@api_router.get("/menu")
async def get_menu():
    return {"categories": list(MENU.keys()), "items": MENU}


@api_router.get("/branches")
async def get_branches():
    return {"branches": BRANCHES}


@api_router.post("/orders/create", response_model=OrderResponse)
async def create_order(payload: OrderCreate):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    if payload.branch not in OPEN_BRANCH_IDS:
        raise HTTPException(status_code=400, detail="Please select a valid branch")
    if payload.order_type == "delivery" and not payload.customer_address:
        raise HTTPException(status_code=400, detail="Address required for delivery orders")
    if payload.payment_method == "cod" and payload.order_type != "delivery":
        raise HTTPException(status_code=400, detail="Cash on delivery is only available for delivery orders")
    if payload.payment_method == "counter" and payload.order_type != "dine-in":
        raise HTTPException(status_code=400, detail="Pay at counter is only available for dine-in orders")

    resolved = []
    total_rupees = 0
    for ci in payload.items:
        item = MENU_LOOKUP.get(ci.id)
        if not item:
            raise HTTPException(status_code=400, detail=f"Unknown item: {ci.id}")
        line_total = item["price"] * ci.qty
        total_rupees += line_total
        resolved.append({
            "id": item["id"],
            "name": item["name"],
            "price": item["price"],
            "qty": ci.qty,
            "line_total": line_total,
            "category": item["category"],
        })

    order_id = str(uuid.uuid4())
    short_id = order_id.split("-")[0].upper()
    total_paise = total_rupees * 100
    payment_link = f"{RAZORPAY_PAYMENT_LINK}?amount={total_paise}" if payload.payment_method == "online" else None

    doc = {
        "id": order_id,
        "short_id": short_id,
        "items": resolved,
        "order_type": payload.order_type,
        "payment_method": payload.payment_method,
        "branch": payload.branch,
        "customer_name": payload.customer_name,
        "customer_phone": payload.customer_phone,
        "customer_address": payload.customer_address or "",
        "notes": payload.notes or "",
        "amount": total_rupees,
        "amount_paise": total_paise,
        "currency": "INR",
        "payment_link": payment_link,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.orders.insert_one(doc.copy())

    return OrderResponse(
        id=order_id,
        short_id=short_id,
        amount_paise=total_paise,
        amount=total_rupees,
        currency="INR",
        payment_method=payload.payment_method,
        payment_link=payment_link,
        status="pending",
        items=resolved,
        order_type=payload.order_type,
        branch=payload.branch,
    )


@api_router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@api_router.post("/franchise-enquiry")
async def create_enquiry(payload: FranchiseEnquiry):
    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "phone": payload.phone,
        "city": payload.city,
        "message": payload.message or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.franchise_enquiries.insert_one(doc.copy())
    return {"ok": True, "id": doc["id"]}


# ===== ADMIN =====
@api_router.post("/admin/login")
async def admin_login(payload: AdminLogin):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")
    return {"ok": True, "token": ADMIN_PASSWORD}  # simple token = password


@api_router.get("/admin/orders")
async def admin_list_orders(_: bool = __import__("fastapi").Depends(require_admin)):
    cursor = db.orders.find({}, {"_id": 0}).sort("created_at", -1).limit(500)
    return {"orders": await cursor.to_list(length=500)}


@api_router.patch("/admin/orders/{order_id}")
async def admin_update_order(order_id: str, payload: OrderStatusUpdate, _: bool = __import__("fastapi").Depends(require_admin)):
    res = await db.orders.update_one({"id": order_id}, {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"ok": True, "status": payload.status}


@api_router.get("/admin/stats")
async def admin_stats(_: bool = __import__("fastapi").Depends(require_admin)):
    total = await db.orders.count_documents({})
    pending = await db.orders.count_documents({"status": "pending"})
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today = await db.orders.count_documents({"created_at": {"$gte": today_start}})
    return {"total_orders": total, "pending_orders": pending, "today_orders": today}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
