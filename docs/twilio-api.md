# Twilio API Reference — SIP Trunking & Programmable Voice

## Overview

Twilio Programmable Voice routes phone calls via SIP trunk to your LiveKit server. Calls flow:

```
Customer PSTN → Twilio Phone Number → SIP Trunk → LiveKit Server → Telephony Agent
```

Two integration patterns:
1. **Phone Number → TwiML Bin → SIP** (traditional TwiML routing)
2. **Phone Number → SIP Trunk → LiveKit** (direct SIP trunking)

---

## 1. Incoming Phone Number Resource

**API:** `GET/PUT /2010-04-01/Accounts/{AccountSid}/PhoneNumbers/{PhoneNumberSid}.json`
**Python Client:** `client.incoming_phone_numbers.get(phone_number)` then `.update()`

### Key Attributes for Voice Calls

| Attribute | Description | Default |
|-----------|-------------|---------|
| `voice_url` | TwiML URL Twilio calls on inbound voice | — |
| `voice_method` | HTTP method for voice_url | `POST` |
| `voice_status_callback` | Callback URL for call status updates | — |
| `status_callback` | Alias for voice_status_callback | — |
| `trunk_sid` | SID of SIP Trunk (for SIP routing) | — |
| `sms_url` | TwiML URL for SMS | — |
| `fax_url` | URL for fax handling | — |
| `caller_id` | Default caller ID for outbound | — |

### Update Phone Number via REST API

```python
from twilio.rest import Client

client = Client(account_sid, auth_token)

# Option A: Route to TwiML Bin (then SIP)
client.incoming_phone_numbers(phone_number_sid).update(
    voice_url="https://your-server.com/twiml",
    voice_method="POST",
    voice_status_callback="https://your-server.com/webhooks/call-status"
)

# Option B: Route to SIP Trunk directly
client.incoming_phone_numbers(phone_number_sid).update(
    trunk_sid="TKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)
```

### Update via cURL

```bash
curl -X PUT "https://api.twilio.com/2010-04-01/Accounts/ACxxxx/PhoneNumbers/PHxxxx.json" \
  -u "ACxxxx:auth_token" \
  -d "VoiceUrl=https://your-server.com/twiml" \
  -d "VoiceMethod=POST" \
  -d "StatusCallback=https://your-server.com/webhooks/status"
```

---

## 2. SIP Trunking API

### Trunk Resource

**API:** `POST /2010-04-01/Accounts/{AccountSid}/Sip/Trunks.json`

#### Create Trunk

```python
trunk = client.trunking.v1.trunks.create(
    friendly_name="Call Center Trunk",
    domain_name="callcenter.pstn.twilio.com",
    enabled=True
)
print(f"Trunk SID: {trunk.sid}")
```

#### Create Domains (for the SIP domain)

```python
domain = client.trunking.v1.trunks(trunk_sid).domains.create(
    domain_name="callcenter.pstn.twilio.com",
    enabled=True
)
```

#### Create Credentials (SIP auth)

```python
creds = client.trunking.v1.trunks(trunk_sid).credentials_lists.create(
    credential_sid="CRxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)
```

#### Create IP ACLs (optional)

```python
ip_acl = client.trunking.v1.trunks(trunk_sid).ip_access_control_lists.create(
    ip_access_control_list_sid="IAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)
```

### Termination Settings

For inbound calls FROM your SIP server TO Twilio:
- `termination_credentials_list_sid` — SIP auth credentials
- `termination_ip_access_control_list_sid` — allowed IPs

### Origination Settings

For outbound calls FROM Twilio TO your SIP server:
- `origination_url` — HTTPS URL that returns TwiML
- `origination_phone_number` — phone number to display
- `origination_ip_access_control_list_sid` — allowed IPs

---

## 3. TwiML for Voice

**URL:** `https://www.twilio.com/docs/voice/twiml`

### Basic Inbound TwiML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>sip:agent@livekit-server:7881</Sip>
    </Dial>
</Response>
```

### TwiML with Recording

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial record="record-from-start" recording-status-callback="https://your-server.com/webhooks/recording">
        <Sip>sip:agent@livekit-server:7881</Sip>
    </Dial>
</Response>
```

### Key TwiML Nouns for Voice

| Noun | Purpose |
|------|---------|
| `<Response>` | Root element |
| `<Say>` | Text-to-speech (uses built-in TTS) |
| `<Gather>` | Collect DTMF or speech |
| `<Record>` | Record audio |
| `<Dial>` | Route call to another endpoint |
| `<Hangup>` | End the call |
| `<Redirect>` | Return new TwiML |
| `<Play>` | Play audio file |

### `<Sip>` Noun Parameters

| Attribute | Description |
|-----------|-------------|
| `url` | TwiML to execute on the called party's end |
| `method` | HTTP method for the url |
| `statusCallback` | URL notified on SIP call status |
| `statusCallbackMethod` | HTTP method for status callback |
| `sipHeaders` | Custom SIP headers to add |

---

## 4. Call Resource

**API:** `GET/POST /2010-04-01/Accounts/{AccountSid}/Calls.json`

### Create Outbound Call

```python
call = client.calls.create(
    to="+15551234567",
    from_="+18333841868",  # Your Twilio number
    url="https://your-server.com/twiml"
)
```

### Modify Call in Progress

```python
# Play a message
client.calls(call_sid).update(
    method="POST",
    url="https://your-server.com/twiml/message"
)

# Play audio
client.calls(call_sid).play(
    url="https://your-server.com/audio/hello.mp3"
)

# Hang up
client.calls(call_sid).update(status="completed")
```

### Key Call Attributes

| Attribute | Description |
|-----------|-------------|
| `sid` | Unique call ID |
| `status` | queued, ringing, in-progress, completed, failed, busy, no-answer |
| `direction` | inbound, outbound-api, outbound-dial |
| `from` | Caller phone number |
| `to` | Destination phone number |
| `duration` | Call duration in seconds |
| `start_time` | When call started |
| `end_time` | When call ended |
| `parent_call_sid` | For call transfers |
| `recording_sid` | If call was recorded |

---

## 5. Recording Resource

**API:** `GET /2010-04-01/Accounts/{AccountSid}/Recordings.json`

### Create Recording (from TwiML)

```xml
<Dial record="record-from-start" recording-status-callback="https://your-server.com/webhooks/recording">
    <Sip>...</Sip>
</Dial>
```

### Create Recording (from API)

```python
recording = client.calls(call_sid).recordings.create(
    reason="manual"
)
print(f"Recording SID: {recording.sid}")
```

### Key Recording Attributes

| Attribute | Description |
|-----------|-------------|
| `sid` | Unique recording ID |
| `duration` | Duration in seconds |
| `source` | call, conference, playback |
| `start_time` | When recording started |
| `end_time` | When recording ended |
| `status` | in-progress, completed, failed |
| `uri` | URI to fetch recording details |

---

## 6. Webhooks & Event Handling

Twilio sends HTTP callbacks to your server at key events:

| Event | Webhook Trigger |
|-------|-----------------|
| Call starts | `status_callback` on phone number or `<Dial>` |
| Call ends | `status_callback` |
| Recording complete | `recording_status_callback` |
| DTMF collected | `method` + `action` on `<Gather>` |
| SIP call status | `statusCallback` on `<Sip>` |

### Call Status Callback Parameters

```
CallSid=CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
From=%2B18333841868
To=%2B15551234567
CallStatus=in-progress|completed|failed|...
Direction=inbound|outbound-api|...
Duration=45
Called=%2B15551234567
Caller=%2B18333841868
```

---

## 7. Integration with LiveKit

### How It Works

1. **Customer calls** +18333841868
2. **Twilio receives** the call and checks the phone number config
3. **Twilio calls** your webhook (voice_url) or routes via SIP trunk
4. **Webhook returns TwiML** with `<Sip>` verb pointing to LiveKit
5. **LiveKit SIP trunk** accepts the SIP INVITE
6. **LiveKit creates room** and dispatches to your agent
7. **Agent processes** audio via STT → LLM → TTS
8. **Twilio receives SIP BYE** and call ends
9. **Twilio calls status_callback** to notify your server

### Configuration Steps

#### Step 1: Create TwiML Bin (optional, for custom logic)

```python
from twilio.rest import Client

client = Client(account_sid, auth_token)

bin = client.new_credentials.twiml_bins.create(
    friendly_name="Call Center TwiML",
    twiml='''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial record="record-from-start">
        <Sip>sip:your-domain@livekit-server:7881</Sip>
    </Dial>
</Response>'''
)
```

#### Step 2: Configure Phone Number

```python
client.incoming_phone_numbers(phone_number_sid).update(
    voice_url=bin.twiml_uri,  # or direct URL
    voice_status_callback="https://your-server.com/webhooks/call-status"
)
```

#### Step 3: Set Up LiveKit SIP Trunk

In LiveKit dashboard or API:
- Create SIP trunk with domain `callcenter.pstn.twilio.com`
- Configure SIP URI to point to your server
- Enable inbound calls

#### Step 4: Configure Twilio Trunk (optional)

If using direct SIP trunking (no TwiML):
- Create SIP trunk via Twilio REST API
- Set `domain_name` and authentication
- Link phone number to trunk via `trunk_sid`

---

## 8. Error Handling & Status Codes

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 200 + TwiML | Success | Twilio executes TwiML |
| 400/404/500 | Error | Twilio logs and may retry |
| Empty response | Error | Twilio hangs up |

### Common TwiML Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Missing `<Response>` | Malformed TwiML | Add root Response element |
| Unknown verb | Typo in noun | Check TwiML spec |
| Invalid SIP URI | Bad SIP format | Use `sip:user@host:port` |

---

## 9. Security Considerations

1. **Twilio Request Validation** — Verify signatures on incoming webhooks
2. **HTTPS Only** — Twilio requires HTTPS for all webhooks
3. **Auth Tokens** — Keep `TWILIO_AUTH_TOKEN` secret
4. **SIP Auth** — Use credentials lists, not IP-only ACLs
5. **Rate Limits** — Twilio API has rate limits (check docs)

### Verify Twilio Webhook Signature

```python
from twilio.request_validator import RequestValidator

validator = RequestValidator(TWILIO_AUTH_TOKEN)
valid = validator.validate(
    request.url,
    request.form,
    request.headers.get('X-Twilio-Signature', '')
)
if not valid:
    return "Invalid signature", 403
```

---

## 10. Pricing Overview

| Component | Cost |
|-----------|------|
| Phone Number | ~$1.00/mo |
| Inbound Call | $0.0085/min |
| Outbound Call | Varies by country |
| SIP Trunking | $0.0085/min (termination) |
| Recording | $0.006/min |
| TwiML Bin | Free |
| API Calls | Free (up to limits) |

---

## References

- [Twilio Voice API](https://www.twilio.com/docs/voice/api)
- [TwiML Voice](https://www.twilio.com/docs/voice/twiml)
- [SIP Trunking API](https://www.twilio.com/docs/sip-trunking/api)
- [Phone Numbers API](https://www.twilio.com/docs/phone-numbers/api)
- [LiveKit SIP Trunking](https://docs.livekit.io/telephony/start/providers/twilio/)
