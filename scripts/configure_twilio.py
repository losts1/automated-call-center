#!/usr/bin/env python3
"""
Configure Twilio phone number to route to LiveKit SIP.
"""

import os
import sys
import requests

# ─── Configuration ───
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "YOUR_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1-555-555-5555")
TWILIO_WEBHOOK_URL = os.getenv("TWILIO_WEBHOOK_URL", "http://localhost:8000/webhooks/twilio")
TWILIO_STATUS_URL = os.getenv("TWILIO_STATUS_URL", "http://localhost:8000/webhooks/status")
TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

def get_http_client():
    return requests.auth.HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def list_phone_numbers():
    """List all phone numbers."""
    auth = get_http_client()
    resp = requests.get(
        f"{TWILIO_API_BASE}/Accounts/{TWILIO_ACCOUNT_SID}/IncomingPhoneNumbers.json",
        auth=auth
    )

    if resp.status_code == 200:
        numbers = resp.json()['incoming_phone_numbers']
        print(f"📞 Phone Numbers ({len(numbers)}):")
        for pn in numbers:
            print(f"  {pn['phone_number']}")
            print(f"    Voice URL: {pn.get('voice_url', 'none')}")
        return True
    else:
        print(f"❌ Failed: {resp.status_code}")
        return False

def configure_phone_number():
    """Update phone number to use webhook."""
    auth = get_http_client()
    resp = requests.post(
        f"{TWILIO_API_BASE}/Accounts/{TWILIO_ACCOUNT_SID}/IncomingPhoneNumbers.json",
        auth=auth,
        data={
            "PhoneNumber": TWILIO_PHONE_NUMBER,
            "VoiceUrl": TWILIO_WEBHOOK_URL,
            "VoiceMethod": "POST",
            "StatusCallback": TWILIO_STATUS_URL
        }
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"\n📞 Phone number configured:")
        print(f"   Voice URL: {data['voice_url']}")
        print(f"   Status Callback: {data.get('status_callback', 'none')}")
        return True
    else:
        print(f"❌ Failed: {resp.status_code} {resp.text}")
        return False

def main():
    print("=" * 60)
    print("Twilio Configuration Tool")
    print("=" * 60)

    # List current state
    if not list_phone_numbers():
        sys.exit(1)

    # Update phone number
    if configure_phone_number():
        print("\n✅ Configuration complete!")
        print(f"\nNext steps:")
        print(f"1. Start webhook server: python3 webhooks/twilio.py")
        print(f"2. Test call to {TWILIO_PHONE_NUMBER}")
        print(f"3. Monitor logs for call status updates")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
