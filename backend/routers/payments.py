"""
REALUM Payment System
Purchase RLM tokens with Stripe (card) or simulated crypto
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, timezone
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/payments", tags=["Payments"])

from core.database import db
from core.auth import get_current_user

# Import Stripe checkout from emergentintegrations
try:
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, 
        CheckoutSessionResponse, 
        CheckoutStatusResponse, 
        CheckoutSessionRequest
    )
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("Warning: Stripe integration not available")


# ============== RLM PACKAGES ==============
# Fixed packages - amounts defined server-side only for security
RLM_PACKAGES = {
    "starter": {
        "id": "starter",
        "name": "Starter Pack",
        "rlm_amount": 100,
        "price_usd": 9.99,
        "bonus": 0,
        "popular": False
    },
    "explorer": {
        "id": "explorer", 
        "name": "Explorer Pack",
        "rlm_amount": 500,
        "price_usd": 39.99,
        "bonus": 50,  # 10% bonus
        "popular": True
    },
    "adventurer": {
        "id": "adventurer",
        "name": "Adventurer Pack",
        "rlm_amount": 1000,
        "price_usd": 69.99,
        "bonus": 150,  # 15% bonus
        "popular": False
    },
    "pioneer": {
        "id": "pioneer",
        "name": "Pioneer Pack",
        "rlm_amount": 5000,
        "price_usd": 299.99,
        "bonus": 1000,  # 20% bonus
        "popular": False
    }
}

# Simulated crypto rates
CRYPTO_RATES = {
    "ETH": 2500.00,  # 1 ETH = $2500
    "USDT": 1.00,    # 1 USDT = $1
    "BTC": 45000.00  # 1 BTC = $45000
}


# ============== MODELS ==============

class PurchaseRequest(BaseModel):
    package_id: str
    origin_url: str
    payment_method: str = "card"  # "card" or "crypto"

class CryptoPurchaseRequest(BaseModel):
    package_id: str
    crypto_type: str  # ETH, USDT, BTC
    wallet_address: str

class CryptoSimulatePayment(BaseModel):
    transaction_id: str
    tx_hash: str  # Simulated transaction hash


# ============== ENDPOINTS ==============

@router.get("/packages")
async def get_rlm_packages():
    """Get available RLM purchase packages"""
    return {
        "packages": list(RLM_PACKAGES.values()),
        "crypto_rates": CRYPTO_RATES,
        "currency": "USD"
    }


@router.post("/checkout/create")
async def create_checkout_session(
    request: Request,
    data: PurchaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe checkout session for RLM purchase"""
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Payment system not available")
    
    # Validate package
    if data.package_id not in RLM_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    package = RLM_PACKAGES[data.package_id]
    
    # Get Stripe API key
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Payment system not configured")
    
    # Build URLs from frontend origin
    success_url = f"{data.origin_url}/wallet?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{data.origin_url}/wallet?payment=cancelled"
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=float(package["price_usd"]),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user["id"],
            "package_id": data.package_id,
            "rlm_amount": str(package["rlm_amount"]),
            "bonus_amount": str(package["bonus"]),
            "type": "rlm_purchase"
        }
    )
    
    try:
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        transaction = {
            "id": str(uuid.uuid4()),
            "session_id": session.session_id,
            "user_id": current_user["id"],
            "user_email": current_user["email"],
            "package_id": data.package_id,
            "rlm_amount": package["rlm_amount"],
            "bonus_amount": package["bonus"],
            "amount_usd": package["price_usd"],
            "currency": "usd",
            "payment_method": "stripe",
            "status": "pending",
            "payment_status": "initiated",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.payment_transactions.insert_one(transaction)
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id,
            "package": package
        }
        
    except Exception as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/checkout/status/{session_id}")
async def get_checkout_status(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check payment status and credit RLM if successful"""
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Payment system not available")
    
    # Get transaction record
    transaction = await db.payment_transactions.find_one({
        "session_id": session_id,
        "user_id": current_user["id"]
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already processed, return cached status
    if transaction.get("payment_status") == "paid":
        return {
            "status": "complete",
            "payment_status": "paid",
            "rlm_credited": transaction["rlm_amount"] + transaction["bonus_amount"],
            "already_processed": True
        }
    
    # Check with Stripe
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
    
    try:
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": status.status,
                "payment_status": status.payment_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # If paid, credit RLM to user
        if status.payment_status == "paid" and transaction.get("payment_status") != "paid":
            total_rlm = transaction["rlm_amount"] + transaction["bonus_amount"]
            
            # Credit to user wallet
            await db.users.update_one(
                {"id": current_user["id"]},
                {"$inc": {"realum_balance": total_rlm}}
            )
            
            # Record the credit
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "rlm_credited": True,
                    "credited_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            return {
                "status": status.status,
                "payment_status": status.payment_status,
                "rlm_credited": total_rlm,
                "message": f"Successfully added {total_rlm} RLM to your wallet!"
            }
        
        return {
            "status": status.status,
            "payment_status": status.payment_status
        }
        
    except Exception as e:
        print(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check payment status")


# ============== SIMULATED CRYPTO ==============

@router.post("/crypto/initiate")
async def initiate_crypto_purchase(
    data: CryptoPurchaseRequest,
    current_user: dict = Depends(get_current_user)
):
    """Initiate a simulated crypto purchase"""
    if data.package_id not in RLM_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    if data.crypto_type not in CRYPTO_RATES:
        raise HTTPException(status_code=400, detail="Unsupported cryptocurrency")
    
    package = RLM_PACKAGES[data.package_id]
    crypto_rate = CRYPTO_RATES[data.crypto_type]
    crypto_amount = package["price_usd"] / crypto_rate
    
    # Create pending transaction
    transaction_id = str(uuid.uuid4())
    transaction = {
        "id": transaction_id,
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "package_id": data.package_id,
        "rlm_amount": package["rlm_amount"],
        "bonus_amount": package["bonus"],
        "amount_usd": package["price_usd"],
        "crypto_type": data.crypto_type,
        "crypto_amount": crypto_amount,
        "wallet_address": data.wallet_address,
        "payment_method": "crypto_simulated",
        "status": "awaiting_payment",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        # Simulated deposit address
        "deposit_address": f"0x{uuid.uuid4().hex[:40]}"
    }
    await db.payment_transactions.insert_one(transaction)
    
    return {
        "transaction_id": transaction_id,
        "crypto_type": data.crypto_type,
        "crypto_amount": round(crypto_amount, 8),
        "deposit_address": transaction["deposit_address"],
        "package": package,
        "expires_in_minutes": 30,
        "message": f"Send {round(crypto_amount, 8)} {data.crypto_type} to the deposit address"
    }


@router.post("/crypto/simulate-payment")
async def simulate_crypto_payment(
    data: CryptoSimulatePayment,
    current_user: dict = Depends(get_current_user)
):
    """Simulate completing a crypto payment (for testing)"""
    transaction = await db.payment_transactions.find_one({
        "id": data.transaction_id,
        "user_id": current_user["id"],
        "payment_method": "crypto_simulated"
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.get("payment_status") == "paid":
        return {"status": "already_processed", "message": "Payment already completed"}
    
    # Simulate successful payment
    total_rlm = transaction["rlm_amount"] + transaction["bonus_amount"]
    
    # Update transaction
    await db.payment_transactions.update_one(
        {"id": data.transaction_id},
        {"$set": {
            "status": "complete",
            "payment_status": "paid",
            "tx_hash": data.tx_hash,
            "rlm_credited": True,
            "credited_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Credit RLM to user
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": total_rlm}}
    )
    
    return {
        "status": "success",
        "payment_status": "paid",
        "rlm_credited": total_rlm,
        "tx_hash": data.tx_hash,
        "message": f"Successfully added {total_rlm} RLM to your wallet!"
    }


@router.get("/history")
async def get_payment_history(
    current_user: dict = Depends(get_current_user)
):
    """Get user's payment history"""
    transactions = await db.payment_transactions.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    return {"transactions": transactions}


# ============== WEBHOOK ==============

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    if not STRIPE_AVAILABLE:
        return {"status": "ignored"}
    
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        api_key = os.environ.get("STRIPE_API_KEY")
        stripe_checkout = StripeCheckout(api_key=api_key, webhook_url="")
        
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Process webhook event
        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            
            # Find and update transaction
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            
            if transaction and not transaction.get("rlm_credited"):
                total_rlm = transaction["rlm_amount"] + transaction["bonus_amount"]
                
                # Credit RLM
                await db.users.update_one(
                    {"id": transaction["user_id"]},
                    {"$inc": {"realum_balance": total_rlm}}
                )
                
                # Update transaction
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": "complete",
                        "payment_status": "paid",
                        "rlm_credited": True,
                        "credited_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
        
        return {"status": "processed"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}
