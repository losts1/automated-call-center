#!/usr/bin/env python3
"""
Twilio SIP Trunk Setup for LiveKit integration.
Creates SIP domain, credentials, and connects phone number.
"""

import json
import subprocess
from config.settings import settings


def check_twilio_account():
    """Verify Twilio account is accessible."""
    result = subprocess.run(
        ["curl", "-s", "-X", "GET",
         "-u", f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}",
         "https://api.twilio.com/2010-04-01/Accounts.json"],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)


def list_phone_numbers():
    """List all phone numbers in the account."""
    result = subprocess.run(
        ["curl", "-s", "-X", "GET",
         "-u", f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}",
         "https://api.twilio.com/2010-04-01/Accounts.json"],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)


def configure_phone_number(phone_number: str, sip_url: str):
    """Configure a Twilio phone number to use SIP trunk."""
    # This would use Twilio REST API to update the phone number
    # For now, this is a placeholder for manual configuration
    pass


if __name__ == "__main__":
    print("Twilio Account Information:")
    account = check_twilio_account()
    print(json.dumps(account, indent=2))
    
    print("\nPhone Numbers:")
    numbers = list_phone_numbers()
    print(json.dumps(numbers, indent=2))
