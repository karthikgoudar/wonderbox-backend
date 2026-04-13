# API Key Architecture for Multi-Device IoT System

## The Question: One API Key Per Device vs. Centralized?

**Answer: ALWAYS use centralized API keys on the backend. Never give devices direct API access.**

---

## ❌ WRONG Approach: One API Key Per Device

```
Device 1 → has Replicate API key → calls Replicate directly
Device 2 → has Replicate API key → calls Replicate directly
Device 3 → has Replicate API key → calls Replicate directly
...
Device 1000 → has Replicate API key → calls Replicate directly
```

### Why This is Bad:

1. **Security nightmare** - 1000 API keys = 1000 attack surfaces
2. **Can't revoke one device** without affecting API key
3. **Can't enforce limits** - devices can bypass quotas
4. **Management hell** - rotating 1000 keys is impossible
5. **Cost tracking** - can't attribute costs per device properly
6. **Provider limits** - most APIs limit # of keys per account
7. **Device compromise** - attacker extracts key from one device → unlimited API access
8. **No fair queuing** - one device can starve others

---

## ✅ CORRECT Approach: Backend Gateway with Device Authentication

```
Device 1 ─┐
Device 2 ─┤
Device 3 ─┼─> Backend (has ONE API key) ──> Replicate/Stability AI
Device 4 ─┤      ↓
...       ─┤    Validates device_token
Device N ─┘    Checks quotas
              Tracks usage
              Makes API call
```

### How WonderBox Already Implements This:

#### 1. **Device Authentication** (Not API Access)
```python
# Device sends:
POST /sticker/submit
Headers:
  x-device-token: abc123...  # Device's auth token (NOT Replicate API key!)
Body:
  device_id: WONDERBOX_12345
  child_id: child_789
  audio: [audio bytes]
```

#### 2. **Backend Validates & Enforces**
```python
# dependencies.py
def get_current_device(
    device_id: str = Form(...),
    x_device_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    # 1. Validate device exists and token is correct
    device = auth_service.validate_device(db, device_id, x_device_token)
    
    # 2. Check rate limits (4 requests/60s)
    rate_limit_service.check_rate_limit(device.device_id)
    
    return device
```

#### 3. **Backend Checks Quotas**
```python
# limits_service.py
def check_limits(db, device):
    # Device paused?
    if device.paused:
        raise HTTPException(403, "Device is paused")
    
    # Device daily limit (e.g., 10 stickers/day on free tier)
    if usage >= device.daily_limit:
        raise HTTPException(429, "Device daily limit reached")
    
    # Company-wide limit (protects your API costs)
    if total_usage >= COMPANY_DAILY_LIMIT:
        raise HTTPException(503, "System capacity reached")
```

#### 4. **Backend Makes API Call**
```python
# image_service.py
async def generate_from_prompt(prompt: str) -> bytes:
    # Backend uses ITS OWN API key (from settings.REPLICATE_API_TOKEN)
    # Device NEVER sees this key!
    client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
    output = await client.run(...)
    return image_bytes
```

#### 5. **Backend Tracks Usage**
```python
# After successful generation:
limits_service.increment_usage(db, device)
```

---

## Architecture Benefits

### 🔒 **Security**
- ✅ Devices never have API keys
- ✅ One compromised device ≠ compromised API
- ✅ Can blacklist devices without rotating API keys
- ✅ Device firmware can't extract sensitive keys

### 💰 **Cost Control**
- ✅ Enforce quotas per device (10/day for free, 50/day for premium)
- ✅ Enforce company-wide limits (prevent cost spikes)
- ✅ Track exact usage per device/parent account
- ✅ Implement subscription tiers easily

### 🔄 **Flexibility**
- ✅ Switch API providers without updating devices
- ✅ A/B test different models (Flux vs SDXL)
- ✅ Add fallback providers transparently
- ✅ Change pricing/limits without firmware updates

### 📊 **Observability**
- ✅ See which devices use the most API calls
- ✅ Track costs per parent account
- ✅ Detect abuse patterns
- ✅ Business intelligence (usage analytics)

---

## Quota Management Strategy

### Hierarchy of Limits (All Enforced at Backend)

```
1. Device Paused (manual override by admin/parent)
   └─> 403 Forbidden
   
2. Rate Limiting (4 requests per 60 seconds)
   └─> 429 Too Many Requests (temporary block)
   
3. Device Daily Quota (e.g., 10 stickers/day)
   └─> 429 Quota Exceeded (resets at midnight)
   
4. Parent Account Quota (subscription-based)
   └─> 429 Subscription Limit Reached
   
5. Company-Wide Daily Limit (cost protection)
   └─> 503 Service Unavailable (system-wide)
```

### Example Quotas

| Tier | Daily Limit | Cost/Month (1000 images) |
|------|-------------|--------------------------|
| Free | 10/device | $0 (Flux Schnell free tier) |
| Basic | 25/device | $3 (Flux Dev) |
| Premium | 50/device | $3 |
| Enterprise | Unlimited* | Custom |

\* Subject to company-wide limit

---

## Configuration (Backend Only)

### `.env` file:
```bash
# Backend's API keys (devices NEVER see these)
REPLICATE_API_TOKEN="r8_your_secret_token_here"
STABILITY_API_KEY="sk_your_secret_key_here"

# Quota limits (enforced by backend)
DEFAULT_DAILY_STICKER_LIMIT=10      # Free tier
SUBSCRIPTION_OVERRIDE_LIMIT=50      # Premium tier
COMPANY_DAILY_LIMIT=1000            # Total system capacity
```

### Database: `devices` table
```sql
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR UNIQUE,
    token VARCHAR,              -- Device's auth token (hashed)
    parent_id INTEGER,          -- Linked to user account
    daily_limit INTEGER,        -- Override default limit
    paused BOOLEAN DEFAULT false,
    created_at TIMESTAMP
);
```

### Database: `daily_usage` table
```sql
CREATE TABLE daily_usage (
    device_id INTEGER,
    date DATE,
    count INTEGER,              -- Number of stickers generated
    PRIMARY KEY (device_id, date)
);
```

---

## Security Deep Dive

### What Devices Have:
- ✅ `device_id` (identifier, public)
- ✅ `device_token` (auth credential, secret)
- ❌ NO API keys
- ❌ NO sensitive backend credentials

### If Device is Compromised:
- Attacker can make requests AS THAT DEVICE only
- Rate limits still apply (4/minute)
- Daily quotas still apply (10/day)
- You can pause the device remotely
- Attacker CANNOT access other devices
- Attacker CANNOT bypass quotas
- Attacker CANNOT rack up unlimited API costs

### If Backend is Compromised:
- Attacker has API keys → serious, but affects ALL systems equally
- Solution: Rotate API keys, implement API key rotation policy
- Devices don't need updates (they don't have the keys)

---

## Subscription Tiers (Future Enhancement)

### Database Schema Enhancement:
```sql
CREATE TABLE subscriptions (
    user_id INTEGER,
    tier VARCHAR,               -- free, basic, premium, enterprise
    daily_limit INTEGER,        -- Tier-specific limit
    valid_until TIMESTAMP
);
```

### Backend Logic Enhancement:
```python
def check_limits(db, device):
    # Get device's parent account
    parent = user_repository.get_by_id(db, device.parent_id)
    
    # Get subscription tier
    subscription = subscription_repository.get_active(db, parent.id)
    
    if subscription and subscription.tier == "premium":
        daily_limit = SUBSCRIPTION_PREMIUM_LIMIT  # 50
    else:
        daily_limit = DEFAULT_DAILY_STICKER_LIMIT  # 10
    
    # Check against tier-appropriate limit
    if usage >= daily_limit:
        raise HTTPException(429, f"{subscription.tier} daily limit reached")
```

---

## Monitoring & Alerts

### Metrics to Track:
1. **Per-device usage** - identify heavy users
2. **Per-parent usage** - for billing/upsell
3. **Company-wide usage** - cost forecasting
4. **API success rate** - provider reliability
5. **Failed requests** - quota exceeded vs API errors

### Alerts to Set:
- Company usage > 80% of daily limit
- Any device hitting limits repeatedly (abuse detection)
- API error rate > 5%
- Cost spike detection

### Example Monitoring:
```python
# analytics_service.py
def track_sticker_generated(device_id, parent_id, provider, cost_estimate):
    log_event({
        "event": "sticker_generated",
        "device_id": device_id,
        "parent_id": parent_id,
        "provider": provider,
        "cost": cost_estimate,
        "timestamp": datetime.now(),
    })
```

---

## Cost Estimation

### Replicate (Flux Schnell - FREE tier):
- **Cost:** $0
- **Best for:** Development, low-volume production
- **Caveat:** Rate limited (but generous)

### Replicate (Flux Dev) or Stability SDXL:
- **Cost:** ~$0.003 per image
- **At scale:**
  - 1,000 images/month = $3
  - 10,000 images/month = $30
  - 100,000 images/month = $300

### Budget Planning:
```
Scenario: 100 devices, 10 stickers/device/day

Daily usage: 100 × 10 = 1,000 stickers
Monthly usage: 1,000 × 30 = 30,000 stickers
Monthly cost: 30,000 × $0.003 = $90

Your COMPANY_DAILY_LIMIT should be set to control this:
COMPANY_DAILY_LIMIT=1000  # Caps costs at ~$90/month
```

---

## Summary

### ✅ DO:
- Store API keys on backend only
- Authenticate devices with device tokens
- Enforce all quotas at backend level
- Track usage per device in your database
- Implement tiered limits based on subscriptions
- Monitor costs and set alerts

### ❌ DON'T:
- Give API keys to devices
- Trust devices to enforce their own limits
- Skip usage tracking
- Allow unlimited requests
- Expose backend configuration to devices

### The Rule:
**"Never trust the client, always validate on the server"**

Your current architecture already does this perfectly! Just enhance the quota management and you're golden. 🎯
