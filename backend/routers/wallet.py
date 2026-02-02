from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import uuid

from core.database import db
from core.config import TOKEN_BURN_RATE
from core.auth import get_current_user
from models.user import WalletConnect, Transfer
from services.token_service import burn_tokens, create_transaction, get_token_stats

router = APIRouter(prefix="/wallet", tags=["Wallet"])

@router.get("")
async def get_wallet(current_user: dict = Depends(get_current_user)):
    transactions = await db.transactions.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("timestamp", -1).limit(50).to_list(50)
    
    return {
        "balance": current_user["realum_balance"],
        "wallet_address": current_user.get("wallet_address"),
        "transactions": transactions
    }

@router.get("/transactions")
async def get_transactions(current_user: dict = Depends(get_current_user)):
    transactions = await db.transactions.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    return {"transactions": transactions}

@router.post("/connect")
async def connect_wallet(data: WalletConnect, current_user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"wallet_address": data.wallet_address}}
    )
    return {"status": "connected", "wallet_address": data.wallet_address}

@router.post("/transfer")
async def transfer_tokens(data: Transfer, current_user: dict = Depends(get_current_user)):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if current_user["realum_balance"] < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    recipient = await db.users.find_one({"id": data.to_user_id}, {"_id": 0})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if recipient["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
    
    burn_amount = data.amount * TOKEN_BURN_RATE
    net_amount = data.amount - burn_amount
    
    # Deduct from sender
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Add to recipient
    await db.users.update_one(
        {"id": recipient["id"]},
        {"$inc": {"realum_balance": net_amount}}
    )
    
    # Record burn
    await burn_tokens(burn_amount, f"Transfer tax: {current_user['username']} -> {recipient['username']}")
    
    # Record transactions
    reason = data.reason or "Transfer"
    await create_transaction(current_user["id"], "debit", data.amount, f"Sent to {recipient['username']}: {reason}", burn_amount)
    await create_transaction(recipient["id"], "credit", net_amount, f"Received from {current_user['username']}: {reason}")
    
    return {
        "status": "success",
        "amount_sent": data.amount,
        "amount_received": net_amount,
        "amount_burned": burn_amount
    }

# Token stats router
token_router = APIRouter(prefix="/token", tags=["Token Economy"])

@token_router.get("/stats")
async def get_stats():
    return await get_token_stats()

@token_router.get("/burns")
async def get_burn_history():
    burns = await db.burns.find({}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)
    return {"burns": burns}
