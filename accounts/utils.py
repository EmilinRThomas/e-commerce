# accounts/utils.py
import random
from datetime import timedelta
from django.utils import timezone
from .models import OTP

def generate_otp_code():
    return f"{random.randint(100000, 999999)}"

def create_and_send_otp(user, purpose='signup', expiry_minutes=10):
    otp = generate_otp_code()
    now = timezone.now()
    otp = OTP.objects.create(user=user, otp=otp, purpose=purpose, expires_at=now + timedelta(minutes=expiry_minutes))
    # TODO: replace with SMS provider in prod (Twilio, Fast2SMS, etc.)
    print(f"[DEBUG] OTP for user {user} purpose {purpose}: {otp}")
    return otp
