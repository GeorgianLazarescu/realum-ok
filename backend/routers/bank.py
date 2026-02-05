"""
REALUM Bank System
Savings accounts, loans, deposits, and banking services
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import math

router = APIRouter(prefix="/api/bank", tags=["Bank System"])

from core.database import db
from core.auth import get_current_user


# ============== BANK CONSTANTS ==============

BANK_NAME = "REALUM Central Bank"

# Interest rates (daily)
SAVINGS_INTEREST_RATE = 0.001  # 0.1% daily (36.5% APY)
LOAN_INTEREST_RATE = 0.002  # 0.2% daily (73% APY)

# Deposit terms and bonuses
DEPOSIT_TERMS = {
    "7_days": {"days": 7, "rate": 0.015, "bonus_percent": 1.5},
    "30_days": {"days": 30, "rate": 0.07, "bonus_percent": 7},
    "90_days": {"days": 90, "rate": 0.25, "bonus_percent": 25},
    "180_days": {"days": 180, "rate": 0.60, "bonus_percent": 60},
    "365_days": {"days": 365, "rate": 1.50, "bonus_percent": 150},
}

# Loan limits
MIN_LOAN = 100
MAX_LOAN_MULTIPLIER = 5  # Can borrow up to 5x their current balance
MAX_LOAN = 10000
LOAN_DURATION_DAYS = 30

# Bank fees
TRANSFER_FEE_PERCENT = 0.5  # 0.5% fee on transfers
EARLY_WITHDRAWAL_PENALTY = 0.10  # 10% penalty for early withdrawal


# ============== MODELS ==============

class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    term: str  # 7_days, 30_days, etc.

class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0)

class LoanRequest(BaseModel):
    amount: float = Field(..., gt=0)
    purpose: Optional[str] = "General"

class LoanPaymentRequest(BaseModel):
    loan_id: str
    amount: float = Field(..., gt=0)

class TransferRequest(BaseModel):
    to_user_id: str
    amount: float = Field(..., gt=0)
    note: Optional[str] = ""


# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    """Remove MongoDB _id"""
    if doc and "_id" in doc:
        del doc["_id"]
    return doc

def calculate_interest(principal: float, rate: float, days: int) -> float:
    """Calculate compound interest"""
    return principal * ((1 + rate) ** days - 1)

async def get_or_create_bank_account(user_id: str, username: str):
    """Get or create user's bank account"""
    account = await db.bank_accounts.find_one({"user_id": user_id})
    
    if not account:
        account = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "username": username,
            "checking_balance": 0.0,
            "savings_balance": 0.0,
            "total_deposited": 0.0,
            "total_withdrawn": 0.0,
            "total_interest_earned": 0.0,
            "credit_score": 700,  # Starting credit score
            "account_tier": "standard",  # standard, silver, gold, platinum
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_interest_calculation": datetime.now(timezone.utc).isoformat()
        }
        await db.bank_accounts.insert_one(account)
    
    return account

async def calculate_and_apply_savings_interest(account):
    """Calculate and apply daily interest to savings"""
    last_calc = datetime.fromisoformat(account.get("last_interest_calculation", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    days_passed = (now - last_calc).days
    
    if days_passed > 0 and account.get("savings_balance", 0) > 0:
        interest = calculate_interest(account["savings_balance"], SAVINGS_INTEREST_RATE, days_passed)
        
        await db.bank_accounts.update_one(
            {"id": account["id"]},
            {
                "$inc": {"savings_balance": interest, "total_interest_earned": interest},
                "$set": {"last_interest_calculation": now.isoformat()}
            }
        )
        
        # Record interest transaction
        await db.bank_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": account["user_id"],
            "type": "interest",
            "amount": interest,
            "description": f"Savings interest ({days_passed} days)",
            "balance_after": account["savings_balance"] + interest,
            "created_at": now.isoformat()
        })
        
        return interest
    return 0


# ============== BANK ENDPOINTS ==============

@router.get("/info")
async def get_bank_info():
    """Get bank information and rates"""
    return {
        "name": BANK_NAME,
        "rates": {
            "savings_daily": SAVINGS_INTEREST_RATE * 100,
            "savings_apy": ((1 + SAVINGS_INTEREST_RATE) ** 365 - 1) * 100,
            "loan_daily": LOAN_INTEREST_RATE * 100,
            "loan_apr": ((1 + LOAN_INTEREST_RATE) ** 365 - 1) * 100,
        },
        "deposit_terms": DEPOSIT_TERMS,
        "loan_limits": {
            "min": MIN_LOAN,
            "max": MAX_LOAN,
            "duration_days": LOAN_DURATION_DAYS
        },
        "fees": {
            "transfer_percent": TRANSFER_FEE_PERCENT,
            "early_withdrawal_penalty": EARLY_WITHDRAWAL_PENALTY * 100
        }
    }


@router.get("/account")
async def get_bank_account(current_user: dict = Depends(get_current_user)):
    """Get user's bank account details"""
    account = await get_or_create_bank_account(current_user["id"], current_user["username"])
    
    # Calculate any pending interest
    interest_earned = await calculate_and_apply_savings_interest(account)
    
    # Refresh account data
    account = await db.bank_accounts.find_one({"user_id": current_user["id"]})
    
    # Get active deposits
    deposits = await db.bank_deposits.find({
        "user_id": current_user["id"],
        "status": "active"
    }, {"_id": 0}).to_list(20)
    
    # Get active loans
    loans = await db.bank_loans.find({
        "user_id": current_user["id"],
        "status": "active"
    }, {"_id": 0}).to_list(10)
    
    # Calculate total loan debt
    total_debt = sum(loan.get("remaining_amount", 0) for loan in loans)
    
    return {
        "account": serialize_doc(account),
        "wallet_balance": current_user.get("realum_balance", 0),
        "deposits": deposits,
        "active_deposits_count": len(deposits),
        "total_in_deposits": sum(d.get("amount", 0) for d in deposits),
        "loans": loans,
        "active_loans_count": len(loans),
        "total_debt": total_debt,
        "interest_earned_today": interest_earned
    }


@router.post("/deposit/wallet")
async def deposit_from_wallet(
    data: WithdrawRequest,
    account_type: str = "savings",
    current_user: dict = Depends(get_current_user)
):
    """Deposit RLM from wallet to bank account"""
    # Check wallet balance
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    account = await get_or_create_bank_account(current_user["id"], current_user["username"])
    
    # Deduct from wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Add to bank account
    balance_field = "savings_balance" if account_type == "savings" else "checking_balance"
    await db.bank_accounts.update_one(
        {"id": account["id"]},
        {"$inc": {balance_field: data.amount, "total_deposited": data.amount}}
    )
    
    # Record transaction
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "deposit",
        "amount": data.amount,
        "from": "wallet",
        "to": account_type,
        "description": f"Deposit to {account_type} account",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "success",
        "deposited": data.amount,
        "account_type": account_type,
        "message": f"Deposited {data.amount} RLM to your {account_type} account"
    }


@router.post("/withdraw/wallet")
async def withdraw_to_wallet(
    data: WithdrawRequest,
    account_type: str = "savings",
    current_user: dict = Depends(get_current_user)
):
    """Withdraw RLM from bank account to wallet"""
    account = await get_or_create_bank_account(current_user["id"], current_user["username"])
    
    balance_field = "savings_balance" if account_type == "savings" else "checking_balance"
    
    if account.get(balance_field, 0) < data.amount:
        raise HTTPException(status_code=400, detail=f"Insufficient {account_type} balance")
    
    # Deduct from bank account
    await db.bank_accounts.update_one(
        {"id": account["id"]},
        {"$inc": {balance_field: -data.amount, "total_withdrawn": data.amount}}
    )
    
    # Add to wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": data.amount}}
    )
    
    # Record transaction
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "withdrawal",
        "amount": data.amount,
        "from": account_type,
        "to": "wallet",
        "description": f"Withdrawal from {account_type} account",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "success",
        "withdrawn": data.amount,
        "account_type": account_type,
        "message": f"Withdrew {data.amount} RLM to your wallet"
    }


# ============== TERM DEPOSITS ==============

@router.post("/deposit/term")
async def create_term_deposit(
    data: DepositRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a term deposit for higher interest"""
    if data.term not in DEPOSIT_TERMS:
        raise HTTPException(status_code=400, detail="Invalid deposit term")
    
    term_info = DEPOSIT_TERMS[data.term]
    
    # Check wallet balance
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    # Calculate maturity
    now = datetime.now(timezone.utc)
    maturity_date = now + timedelta(days=term_info["days"])
    expected_return = data.amount * (1 + term_info["rate"])
    
    # Deduct from wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -data.amount}}
    )
    
    # Create deposit
    deposit = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "username": current_user["username"],
        "amount": data.amount,
        "term": data.term,
        "term_days": term_info["days"],
        "interest_rate": term_info["rate"],
        "bonus_percent": term_info["bonus_percent"],
        "expected_return": expected_return,
        "status": "active",
        "created_at": now.isoformat(),
        "maturity_date": maturity_date.isoformat()
    }
    await db.bank_deposits.insert_one(deposit)
    
    # Record transaction
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "term_deposit",
        "amount": data.amount,
        "description": f"Term deposit ({term_info['days']} days at {term_info['bonus_percent']}%)",
        "deposit_id": deposit["id"],
        "created_at": now.isoformat()
    })
    
    return {
        "deposit": serialize_doc(deposit),
        "message": f"Created {term_info['days']}-day deposit for {data.amount} RLM",
        "expected_return": round(expected_return, 2),
        "maturity_date": maturity_date.isoformat()
    }


@router.post("/deposit/{deposit_id}/withdraw")
async def withdraw_term_deposit(
    deposit_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Withdraw a term deposit (early withdrawal has penalty)"""
    deposit = await db.bank_deposits.find_one({
        "id": deposit_id,
        "user_id": current_user["id"],
        "status": "active"
    })
    
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    now = datetime.now(timezone.utc)
    maturity = datetime.fromisoformat(deposit["maturity_date"].replace("Z", "+00:00"))
    
    is_early = now < maturity
    
    if is_early:
        # Early withdrawal - apply penalty
        return_amount = deposit["amount"] * (1 - EARLY_WITHDRAWAL_PENALTY)
        penalty = deposit["amount"] * EARLY_WITHDRAWAL_PENALTY
        message = f"Early withdrawal with {EARLY_WITHDRAWAL_PENALTY * 100}% penalty"
    else:
        # Mature deposit - full return with interest
        return_amount = deposit["expected_return"]
        penalty = 0
        message = "Deposit matured! Full interest earned"
    
    # Update deposit status
    await db.bank_deposits.update_one(
        {"id": deposit_id},
        {"$set": {
            "status": "withdrawn",
            "withdrawn_at": now.isoformat(),
            "actual_return": return_amount,
            "early_withdrawal": is_early,
            "penalty": penalty
        }}
    )
    
    # Add to wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": return_amount}}
    )
    
    # Record transaction
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "deposit_withdrawal",
        "amount": return_amount,
        "description": message,
        "deposit_id": deposit_id,
        "penalty": penalty,
        "created_at": now.isoformat()
    })
    
    return {
        "status": "success",
        "amount_returned": round(return_amount, 2),
        "original_amount": deposit["amount"],
        "interest_earned": round(return_amount - deposit["amount"], 2) if not is_early else 0,
        "penalty": round(penalty, 2),
        "early_withdrawal": is_early,
        "message": message
    }


# ============== LOANS ==============

@router.get("/loan/eligibility")
async def check_loan_eligibility(current_user: dict = Depends(get_current_user)):
    """Check how much the user can borrow"""
    account = await get_or_create_bank_account(current_user["id"], current_user["username"])
    
    # Get existing loans
    active_loans = await db.bank_loans.find({
        "user_id": current_user["id"],
        "status": "active"
    }).to_list(10)
    
    total_debt = sum(loan.get("remaining_amount", 0) for loan in active_loans)
    
    # Calculate max loan based on balance and credit score
    wallet_balance = current_user.get("realum_balance", 0)
    savings_balance = account.get("savings_balance", 0)
    total_assets = wallet_balance + savings_balance
    
    # Credit score affects max loan
    credit_multiplier = account.get("credit_score", 700) / 700
    max_eligible = min(
        total_assets * MAX_LOAN_MULTIPLIER * credit_multiplier,
        MAX_LOAN
    ) - total_debt
    
    return {
        "eligible": max_eligible > MIN_LOAN,
        "max_loan_amount": max(0, round(max_eligible, 2)),
        "min_loan_amount": MIN_LOAN,
        "current_debt": total_debt,
        "credit_score": account.get("credit_score", 700),
        "interest_rate_daily": LOAN_INTEREST_RATE * 100,
        "loan_duration_days": LOAN_DURATION_DAYS
    }


@router.post("/loan/apply")
async def apply_for_loan(
    data: LoanRequest,
    current_user: dict = Depends(get_current_user)
):
    """Apply for a loan"""
    eligibility = await check_loan_eligibility(current_user)
    
    if not eligibility["eligible"]:
        raise HTTPException(status_code=400, detail="Not eligible for a loan")
    
    if data.amount < MIN_LOAN:
        raise HTTPException(status_code=400, detail=f"Minimum loan amount is {MIN_LOAN} RLM")
    
    if data.amount > eligibility["max_loan_amount"]:
        raise HTTPException(status_code=400, detail=f"Maximum loan amount is {eligibility['max_loan_amount']} RLM")
    
    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=LOAN_DURATION_DAYS)
    
    # Calculate total repayment with interest
    total_interest = calculate_interest(data.amount, LOAN_INTEREST_RATE, LOAN_DURATION_DAYS)
    total_repayment = data.amount + total_interest
    
    # Create loan
    loan = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "username": current_user["username"],
        "principal": data.amount,
        "interest_rate": LOAN_INTEREST_RATE,
        "total_interest": total_interest,
        "total_repayment": total_repayment,
        "remaining_amount": total_repayment,
        "duration_days": LOAN_DURATION_DAYS,
        "purpose": data.purpose,
        "status": "active",
        "created_at": now.isoformat(),
        "due_date": due_date.isoformat()
    }
    await db.bank_loans.insert_one(loan)
    
    # Add loan amount to wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": data.amount}}
    )
    
    # Record transaction
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "loan_disbursement",
        "amount": data.amount,
        "description": f"Loan approved: {data.purpose}",
        "loan_id": loan["id"],
        "created_at": now.isoformat()
    })
    
    return {
        "loan": serialize_doc(loan),
        "message": f"Loan of {data.amount} RLM approved!",
        "total_repayment": round(total_repayment, 2),
        "due_date": due_date.isoformat(),
        "daily_interest": round(data.amount * LOAN_INTEREST_RATE, 2)
    }


@router.post("/loan/repay")
async def repay_loan(
    data: LoanPaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Repay a loan (partial or full)"""
    loan = await db.bank_loans.find_one({
        "id": data.loan_id,
        "user_id": current_user["id"],
        "status": "active"
    })
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if current_user.get("realum_balance", 0) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    payment = min(data.amount, loan["remaining_amount"])
    
    # Deduct from wallet
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"realum_balance": -payment}}
    )
    
    new_remaining = loan["remaining_amount"] - payment
    
    # Update loan
    update_data = {"remaining_amount": new_remaining}
    if new_remaining <= 0:
        update_data["status"] = "paid"
        update_data["paid_at"] = datetime.now(timezone.utc).isoformat()
        
        # Improve credit score for paying off loan
        account = await db.bank_accounts.find_one({"user_id": current_user["id"]})
        if account:
            new_credit = min(850, account.get("credit_score", 700) + 10)
            await db.bank_accounts.update_one(
                {"id": account["id"]},
                {"$set": {"credit_score": new_credit}}
            )
    
    await db.bank_loans.update_one({"id": data.loan_id}, {"$set": update_data})
    
    # Record transaction
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "loan_payment",
        "amount": payment,
        "description": f"Loan payment ({new_remaining:.2f} remaining)" if new_remaining > 0 else "Loan fully paid!",
        "loan_id": data.loan_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "success",
        "payment_amount": round(payment, 2),
        "remaining_amount": round(max(0, new_remaining), 2),
        "loan_paid_off": new_remaining <= 0,
        "message": "Loan fully paid! Credit score improved." if new_remaining <= 0 else f"Payment received. {new_remaining:.2f} RLM remaining."
    }


# ============== BANK TRANSFERS ==============

@router.post("/transfer")
async def bank_transfer(
    data: TransferRequest,
    current_user: dict = Depends(get_current_user)
):
    """Transfer RLM to another user's bank account"""
    if data.to_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")
    
    # Check recipient exists
    recipient = await db.users.find_one({"id": data.to_user_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Get sender's account
    sender_account = await get_or_create_bank_account(current_user["id"], current_user["username"])
    
    # Calculate fee
    fee = data.amount * (TRANSFER_FEE_PERCENT / 100)
    total_deduction = data.amount + fee
    
    # Check balance (from savings)
    if sender_account.get("savings_balance", 0) < total_deduction:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Need {total_deduction:.2f} RLM (including {fee:.2f} fee)")
    
    # Deduct from sender
    await db.bank_accounts.update_one(
        {"id": sender_account["id"]},
        {"$inc": {"savings_balance": -total_deduction}}
    )
    
    # Get or create recipient account and add funds
    recipient_account = await get_or_create_bank_account(data.to_user_id, recipient["username"])
    await db.bank_accounts.update_one(
        {"id": recipient_account["id"]},
        {"$inc": {"savings_balance": data.amount}}
    )
    
    now = datetime.now(timezone.utc)
    
    # Record transactions for both parties
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "type": "transfer_out",
        "amount": -data.amount,
        "fee": fee,
        "to_user_id": data.to_user_id,
        "to_username": recipient["username"],
        "description": f"Transfer to {recipient['username']}" + (f": {data.note}" if data.note else ""),
        "created_at": now.isoformat()
    })
    
    await db.bank_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": data.to_user_id,
        "type": "transfer_in",
        "amount": data.amount,
        "from_user_id": current_user["id"],
        "from_username": current_user["username"],
        "description": f"Transfer from {current_user['username']}" + (f": {data.note}" if data.note else ""),
        "created_at": now.isoformat()
    })
    
    # Notify recipient
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": data.to_user_id,
        "type": "bank_transfer",
        "title": "Bank Transfer Received 🏦",
        "message": f"{current_user['username']} sent you {data.amount} RLM",
        "read": False,
        "created_at": now.isoformat()
    })
    
    return {
        "status": "success",
        "amount_sent": data.amount,
        "fee": round(fee, 2),
        "total_deducted": round(total_deduction, 2),
        "recipient": recipient["username"],
        "message": f"Sent {data.amount} RLM to {recipient['username']}"
    }


# ============== TRANSACTION HISTORY ==============

@router.get("/transactions")
async def get_transaction_history(
    limit: int = 50,
    transaction_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get bank transaction history"""
    query = {"user_id": current_user["id"]}
    if transaction_type:
        query["type"] = transaction_type
    
    transactions = await db.bank_transactions.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"transactions": transactions}


# ============== LEADERBOARD ==============

@router.get("/leaderboard")
async def get_bank_leaderboard(limit: int = 10):
    """Get richest bank account holders"""
    # Aggregate total bank wealth
    pipeline = [
        {
            "$project": {
                "user_id": 1,
                "username": 1,
                "total_wealth": {"$add": ["$checking_balance", "$savings_balance"]},
                "credit_score": 1,
                "account_tier": 1
            }
        },
        {"$sort": {"total_wealth": -1}},
        {"$limit": limit}
    ]
    
    results = await db.bank_accounts.aggregate(pipeline).to_list(limit)
    
    leaderboard = []
    for i, r in enumerate(results):
        leaderboard.append({
            "rank": i + 1,
            "username": r.get("username", "Unknown"),
            "total_wealth": round(r.get("total_wealth", 0), 2),
            "credit_score": r.get("credit_score", 700),
            "tier": r.get("account_tier", "standard")
        })
    
    return {"leaderboard": leaderboard}
