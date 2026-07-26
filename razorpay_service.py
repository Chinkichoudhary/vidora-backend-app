"""
razorpay_service.py
Handles Razorpay subscription creation, signature verification,
and webhook signature checking.
"""

import os
import hmac
import hashlib
import razorpay
from dotenv import load_dotenv

load_dotenv()

client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

PLAN_ID_MAP = {
    "basic": os.getenv("RAZORPAY_BASIC_PLAN_ID"),
    "premium": os.getenv("RAZORPAY_PREMIUM_PLAN_ID"),
}


def get_or_create_customer(name: str, email: str) -> str:
    """Returns existing Razorpay customer or creates a new one."""

    try:
        # Search existing customers
        customers = client.customer.all({"count": 100})

        for customer in customers["items"]:
            if customer.get("email", "").lower() == email.lower():
                print("Existing Razorpay customer:", customer["id"])
                return customer["id"]

        # Create new customer
        customer = client.customer.create({
            "name": name,
            "email": email,
        })

        print("Created Razorpay customer:", customer["id"])
        return customer["id"]

    except Exception as e:
        raise Exception(f"Failed to create Razorpay customer: {e}")

def create_subscription(plan_key: str, customer_id: str) -> dict:
    """
    Creates a Razorpay subscription for the given plan.
    plan_key: 'basic' or 'premium'
    """
    plan_id = PLAN_ID_MAP.get(plan_key)
    if not plan_id:
        raise ValueError(f"Unknown plan: {plan_key}")

    subscription = client.subscription.create({
        "plan_id": plan_id,
        "customer_notify": 1,
        "total_count": 12,  # bills for 12 months, then auto-renews unless cancelled
        "notes": {"vidora_plan": plan_key},
    })
    return subscription


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Used for one-time order payments (not used for subscriptions)."""
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def verify_subscription_signature(subscription_id: str, payment_id: str, signature: str) -> bool:
    """Verifies the signature returned by Razorpay Checkout after a subscription payment."""
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    payload = f"{payment_id}|{subscription_id}"
    expected_signature = hmac.new(
        key_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


def verify_webhook_signature(payload_body: bytes, received_signature: str) -> bool:
    """Verifies a webhook came genuinely from Razorpay."""
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    expected_signature = hmac.new(
        webhook_secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, received_signature)


def cancel_subscription(subscription_id: str):
    return client.subscription.cancel(subscription_id)