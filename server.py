from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import razorpay
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone
import httpx
import hmac
import hashlib
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends, Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'batatas2025')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_IDS = os.environ.get('TELEGRAM_CHAT_IDS', os.environ.get('TELEGRAM_CHAT_ID', ''))
TELEGRAM_CHAT_ID_WANDOOR = os.environ.get('TELEGRAM_CHAT_ID_WANDOOR', '')
TELEGRAM_CHAT_ID_MANJERI = os.environ.get('TELEGRAM_CHAT_ID_MANJERI', '')
TELEGRAM_CHAT_ID_MAMPAD = os.environ.get('TELEGRAM_CHAT_ID_MAMPAD', '')

BRANCH_CHAT_IDS = {
    'wandoor': TELEGRAM_CHAT_ID_WANDOOR,
    'manjeri': TELEGRAM_CHAT_ID_MANJERI,
    'mampad': TELEGRAM_CHAT_ID_MAMPAD,
}

async def send_telegram(message: str, branch: str = None):
    if not TELEGRAM_BOT_TOKEN:
        return
    
    # Build list of chat IDs to notify
    chat_ids = set()
    
    # Add main chat IDs (owner gets all notifications)
    for cid in TELEGRAM_CHAT_IDS.split(','):
        if cid.strip():
            chat_ids.add(cid.strip())
    
    # Add branch specific chat ID
    if branch and branch in BRANCH_CHAT_IDS:
        branch_cid = BRANCH_CHAT_IDS[branch]
        if branch_cid:
            chat_ids.add(branch_cid)
    
    if not chat_ids:
        return
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        logger.info(f"Sending Telegram to {chat_ids}")
        async with httpx.AsyncClient() as client:
            for chat_id in chat_ids:
                resp = await client.post(url, json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                })
                logger.info(f"Telegram response: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

app = FastAPI(title="Batatas API")
api_router = APIRouter(prefix="/api")


# ===== STATIC DATA =====
MENU = {
    "Signature": [
        {"id": "chicken-loaded", "name": "Chicken Loaded Fries", "price": 180, "desc": "Crispy fries smothered with spicy chicken, cheese and sauces.", "image": "https://bataatas.in/images/chicken loaded fries.jpg"},
        {"id": "sausage-loaded", "name": "Sausage Loaded Fries", "price": 200, "desc": "Loaded with juicy sausages, cheese, and smoky sauces.", "image": "https://bataatas.in/images/sausage loaded fries.jpeg"},
        {"id": "machos", "name": "Machos", "price": 210, "desc": "Nacho-style loaded fries — cheesy, crunchy, irresistible.", "image": "https://bataatas.in/images/machos.jpeg"},
        {"id": "beef-smash-loaded", "name": "Smash Beef Loaded Fries", "price": 230, "desc": "Smashed beef, melted cheese and signature sauce over fries.", "image": "https://bataatas.in/images/beef loaded fries.jpeg"},
    ],
    "Snacks": [
        {"id": "exotic-fries", "name": "Exotic French Fries", "price": 80, "desc": "Golden, crispy fries served with your favorite dipping sauce.", "image": "https://bataatas.in/images/exotic french.jpeg"},
        {"id": "cheesy-fries", "name": "Cheesy French Fries", "price": 135, "desc": "Crispy fries loaded with molten cheese and dipping sauce.", "image": "https://bataatas.in/images/cheesy fries.jpeg"},
        {"id": "peri-fries", "name": "Peri Peri French Fries", "price": 90, "desc": "Golden fries tossed in fiery peri peri seasoning.", "image": "https://bataatas.in/images/peri peri fries.jpg"},
    ],
    "Bites": [
        {"id": "nugget-bites", "name": "Nugget Bites", "price": 130, "desc": "Crispy chicken nuggets tossed in signature peri peri seasoning.", "image": "https://bataatas.in/images/nuggets.jpeg"},
        {"id": "peri-wings", "name": "Peri Wings", "price": 150, "desc": "Spicy peri peri wings — a fiery combo you can't resist.", "image": "https://bataatas.in/images/new peri wings.jpg"},
    ],
    "Fried Chicken": [
        {"id": "fc-2pc", "name": "2 Piece Fried Chicken", "price": 160, "desc": "Two pieces of golden, juicy hand-breaded fried chicken.", "image": "https://bataatas.in/images/2pcs.jpeg"},
        {"id": "fc-5pc", "name": "5 Piece Fried Chicken", "price": 270, "desc": "Five pieces of golden, crunchy fried chicken to share.", "image": "https://bataatas.in/images/5pcs fried chckn.jpeg"},
        {"id": "fc-10pc", "name": "10 Piece Fried Chicken", "price": 520, "desc": "A full bucket of crispy golden fried chicken.", "image": "https://bataatas.in/images/10ocs.jpeg"},
        {"id": "fc-20pc", "name": "20 Piece Fried Chicken", "price": 1020, "desc": "The ultimate feast — twenty pieces for the whole squad.", "image": "https://bataatas.in/images/20 piece fried chicken.jpg"},
    ],
    "Chicken Strips": [
        {"id": "cs-4pc", "name": "4 Piece Chicken Strips", "price": 160, "desc": "Tender, crispy chicken strips with dipping sauce.", "image": "https://bataatas.in/images/4pcs strips.jpeg"},
        {"id": "cs-8pc", "name": "8 Piece Chicken Strips", "price": 300, "desc": "Eight golden strips — crispy on the outside, juicy inside.", "image": "https://bataatas.in/images/8ps chick strips.jpeg"},
    ],
    "Burgers": [
        {"id": "zinger", "name": "Zinger Burger", "price": 150, "desc": "Crispy spiced chicken fillet with fresh lettuce and creamy mayo.", "image": "https://bataatas.in/images/zinger burger.jpg"},
        {"id": "beef-smash", "name": "Beef Smash Burger", "price": 170, "desc": "Smashed beef patty, melted cheese and our signature sauce.", "image": "https://bataatas.in/images/new beef burger.jpg"},
    ],
    "Drinks": [
        {"id": "lime-juice", "name": "Lime Juice", "price": 25, "desc": "Freshly squeezed lime juice — zesty and refreshing.", "image": "https://bataatas.in/images/lime juice.jpg"},
        {"id": "mint-lime", "name": "Mint Lime Juice", "price": 30, "desc": "Cool mint meets zesty lime.", "image": "https://bataatas.in/images/new mint lime.jpg"},
        {"id": "mango-juice", "name": "Mango Juice", "price": 70, "desc": "Thick, sweet, sun-ripened mango.", "image": "https://bataatas.in/images/mango juice.jpg"},
        {"id": "strawberry-juice", "name": "Strawberry Juice", "price": 70, "desc": "Fresh strawberries blended smooth.", "image": "https://bataatas.in/images/new stawberry.jpg"},
        {"id": "chikku-juice", "name": "Chikku Juice", "price": 70, "desc": "Creamy sapodilla shake — a tropical classic.", "image": "https://bataatas.in/images/chikku juice.jpg"},
        {"id": "passion-mojito", "name": "Passion Fruit Mojito", "price": 90, "desc": "Passion fruit, mint, lime — the ultimate refresher.", "image": "https://bataatas.in/images/passion fruit mojito.jpg"},
        {"id": "mint-mojito", "name": "Mint Lime Mojito", "price": 90, "desc": "Classic minty-lime mojito — cool, crisp, iconic.", "image": "https://bataatas.in/images/new mint mojito.jpg"},
        {"id": "blue-mojito", "name": "Blue Curaçao Mojito", "price": 90, "desc": "Tropical blue curaçao swirled with mint and lime.", "image": "https://bataatas.in/images/blue mojito new.png"},
        {"id": "cold-coffee", "name": "Cold Coffee", "price": 90, "desc": "Rich, creamy and ice-cold — the perfect pick-me-up.", "image": "https://bataatas.in/images/cold coffee new.jpg"},
    ],
    "Soft Drinks": [
        {"id": "pepsi", "name": "Pepsi", "price": 20, "desc": "Chilled Pepsi — the classic fizz.", "image": "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?auto=format&fit=crop&w=900&q=80"},
        {"id": "7up", "name": "7UP", "price": 20, "desc": "Crisp, lemony 7UP — ice cold.", "image": "https://bataatas.in/images/7 up.jpg"},
    ],
    "Add-ons": [
        {"id": "peri-seasoning", "name": "Peri Peri Seasoning", "price": 10, "desc": "Extra peri peri punch for your fries.", "image": "https://bataatas.in/images/peri peri seasoning.jpg"},
        {"id": "cheese-slice", "name": "Cheese Slice", "price": 20, "desc": "Add a layer of melty cheese.", "image": "https://bataatas.in/images/cheese slice.jpg"},
        {"id": "extra-wings", "name": "Extra Wings", "price": 35, "desc": "Two extra peri peri wings on the side.", "image": "https://bataatas.in/images/wings.jpeg"},
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
    handling_charge: Optional[int] = 0


class OrderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    short_id: str
    amount_paise: int
    amount: int
    currency: str
    payment_method: str
    payment_link: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_key_id: Optional[str] = None
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
    return {"razorpay_key_id": RAZORPAY_KEY_ID}


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
    handling = payload.handling_charge or 0
    total_paise = (total_rupees + handling) * 100

    razorpay_order_id = None
    if payload.payment_method == "online":
        try:
            rz_order = razorpay_client.order.create({
                "amount": total_paise,
                "currency": "INR",
                "receipt": short_id,
                "notes": {
                    "order_id": order_id,
                    "customer_name": payload.customer_name,
                    "branch": payload.branch,
                }
            })
            razorpay_order_id = rz_order["id"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Payment gateway error: {str(e)}")

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
        "amount": total_rupees + handling,
        "amount_paise": total_paise,
        "handling_charge": handling,
        "currency": "INR",
        "razorpay_order_id": razorpay_order_id,
        "payment_link": None,
        "status": "pending",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.orders.insert_one(doc.copy())


    # Send Telegram notification
    items_text = "\n".join([f"  • {i['name']} x{i['qty']} = ₹{i['line_total']}" for i in resolved])
    tg_message = (
        f"🔔 <b>New Order #{short_id}</b>\n\n"
        f"👤 {payload.customer_name} · {payload.customer_phone}\n"
        f"🏪 Branch: {payload.branch.title()}\n"
        f"🛵 Type: {payload.order_type.title()}\n"
        f"💳 Payment: {payload.payment_method.upper()}\n\n"
        f"🛒 Items:\n{items_text}\n\n"
        f"💰 Subtotal: ₹{total_rupees}" + (f"\n📦 Handling: ₹{handling}" if handling > 0 else "\n📦 Handling: FREE") + f"\n💰 Total: ₹{total_rupees + handling}"
    )
    if payload.customer_address:
        tg_message += f"\n📍 Address: {payload.customer_address}"
    if payload.notes:
        tg_message += f"\n📝 Notes: {payload.notes}"
    if payload.payment_method != "online":
        await send_telegram(tg_message, branch=payload.branch)

    

    return OrderResponse(
        id=order_id,
        short_id=short_id,
        amount_paise=total_paise,
        amount=total_rupees,
        currency="INR",
        payment_method=payload.payment_method,
        payment_link=None,
        razorpay_order_id=razorpay_order_id,
        razorpay_key_id=RAZORPAY_KEY_ID if payload.payment_method == "online" else None,
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
@api_router.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    data = await request.json()
    event = data.get("event")
    
    if event == "payment.captured":
        payment = data["payload"]["payment"]["entity"]
        razorpay_order_id = payment.get("order_id")
        
        if razorpay_order_id:
            order = await db.orders.find_one({"razorpay_order_id": razorpay_order_id}, {"_id": 0})
            if order:
                await db.orders.update_one(
                    {"razorpay_order_id": razorpay_order_id},
                    {"$set": {
                        "payment_status": "received",
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                items_text = "\n".join([f"  • {i['name']} x{i['qty']} = ₹{i['line_total']}" for i in order['items']])
                tg_message = (
                    f"💰 <b>Payment Received! #{order['short_id']}</b>\n\n"
                    f"👤 {order['customer_name']} · {order['customer_phone']}\n"
                    f"🏪 Branch: {order['branch'].title()}\n"
                    f"✅ Payment: ONLINE · RECEIVED\n\n"
                    f"🛒 Items:\n{items_text}\n\n"
                    f"💰 Total: ₹{order['amount']}"
                )
                await send_telegram(tg_message, branch=order['branch'])
    
    return {"ok": True}

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
    return {"ok": True, "token": ADMIN_PASSWORD}


@api_router.get("/admin/orders")
async def admin_list_orders(_: bool = __import__("fastapi").Depends(require_admin)):
    cursor = db.orders.find({}, {"_id": 0}).sort("created_at", -1).limit(500)
    return {"orders": await cursor.to_list(length=500)}

@api_router.patch("/admin/orders/{order_id}")
async def admin_update_order(order_id: str, payload: OrderStatusUpdate, _: bool = __import__("fastapi").Depends(require_admin)):
    res = await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"ok": True, "status": payload.status}

@api_router.patch("/admin/orders/{order_id}/payment")
async def admin_mark_payment(order_id: str, _: bool = __import__("fastapi").Depends(require_admin)):
    res = await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "payment_status": "received",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"ok": True, "payment_status": "received"}

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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()