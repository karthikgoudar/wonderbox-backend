# WonderBox API Key & Quota Management - Quick Reference

## ✅ Your Current Architecture (CORRECT!)

```
┌─────────────────────────────────────────────────────────────┐
│                     IoT Devices                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Device 1 │  │ Device 2 │  │ Device 3 │  │ Device N │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│    device_id     device_id    device_id     device_id     │
│       +              +             +             +          │
│  device_token   device_token  device_token  device_token  │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │      WonderBox Backend (FastAPI)        │
        │─────────────────────────────────────────│
        │  1. Validate device_token               │
        │  2. Check rate limits (4/min)           │
        │  3. Check daily quotas                  │
        │  4. Make API call with BACKEND'S key    │
        │  5. Track usage in database             │
        │  6. Return result to device             │
        └────────────┬────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│  Replicate API   │    │ Stability AI API │
│  (ONE key)       │    │  (ONE key)       │
│  Flux Schnell    │    │  SDXL line-art   │
│  FREE tier       │    │  ~$0.003/image   │
└──────────────────┘    └──────────────────┘
```

## 🔑 API Key Storage

### ❌ NEVER Store in Devices:
- Replicate API token
- Stability AI API key
- Any external service credentials

### ✅ ONLY Store in Backend (.env):
```bash
# Backend API keys (ONE per service, used for ALL devices)
REPLICATE_API_TOKEN="r8_your_secret_here"
STABILITY_API_KEY="sk_your_secret_here"

# Quota limits
DEFAULT_DAILY_STICKER_LIMIT=10        # Per device (free tier)
COMPANY_DAILY_LIMIT=1000              # Total system capacity
SUBSCRIPTION_OVERRIDE_LIMIT=50        # Premium users
```

### ✅ Devices Have:
- `device_id` (identifier)
- `x-device-token` (SHA256 hashed in DB, authenticates device)

## 🛡️ Protection Layers

### Layer 1: Device Authentication
```python
# dependencies.py
device = auth_service.validate_device(db, device_id, x_device_token)
# → 401 if invalid
```

### Layer 2: Rate Limiting
```python
# rate_limit_service.py
rate_limit_service.check_rate_limit(device_id)
# → 429 if >4 requests in 60 seconds
# → 403 if device in 5-minute penalty box
```

### Layer 3: Daily Quotas
```python
# limits_service.py
check_limits(db, device)
# → 403 if device paused
# → 429 if device daily limit reached (10/day free, 50/day premium)
# → 503 if company limit reached (1000/day)
```

### Layer 4: Usage Tracking
```python
# After successful generation:
increment_usage(db, device)
# Logged in database for billing/analytics
```

## 📊 Quota Examples

### Free Tier Device:
- Daily limit: 10 stickers
- Rate limit: 4 requests/minute
- Cost to you: $0 (if using Flux Schnell free tier)

### Premium Tier Device:
- Daily limit: 50 stickers
- Rate limit: 4 requests/minute
- Cost to you: ~$0.15/day (~$4.50/month per device)

### Company-Wide Protection:
- Total daily limit: 1,000 stickers
- Even if 100 premium devices (50 each = 5,000), system caps at 1,000
- Protects against cost spikes

## 🔒 Security Benefits

| Scenario | Impact |
|----------|--------|
| Device firmware extracted | Attacker gets device_token only → Can impersonate THAT device, but still limited by quotas |
| Device token compromised | Revoke/pause specific device in DB → API keys safe |
| Backend compromised | Rotate API keys → Devices don't need updates |
| Abuse detected | Lower device.daily_limit or set paused=true |

## 💰 Cost Control Formula

```
Daily API cost = (total_stickers_generated * cost_per_image)

Example with Replicate Flux Dev:
- 100 devices × 10 stickers/day = 1,000 stickers/day
- 1,000 × $0.003 = $3/day
- Monthly cost: ~$90

Your COMPANY_DAILY_LIMIT=1000 protects this!
```

## 📝 Key Files Updated

### Removed DALL-E Support:
- ✅ [settings.py](../app/config/settings.py) - Removed DALL-E config
- ✅ [image_service.py](../app/services/image_service.py) - Removed DALL-E provider
- ✅ [.env.example](../.env.example) - Removed DALL-E variables
- ✅ [requirements.txt](../requirements.txt) - Clarified openai is for STT only
- ✅ [README.md](../README.md) - Updated documentation
- ✅ [image_generation_guide.md](image_generation_guide.md) - Removed DALL-E

### Enhanced Quota Management:
- ✅ [limits_service.py](../app/services/limits_service.py) - Better error messages, logging
- ✅ [settings.py](../app/config/settings.py) - Added quota config options
- ✅ [.env.example](../.env.example) - Documented quota settings

### New Documentation:
- ✅ [api_key_architecture.md](api_key_architecture.md) - Complete architecture guide
- ✅ This file - Quick reference

## 🚀 Quick Start

1. **Get free Replicate token:**
   ```bash
   # Visit: https://replicate.com/account/api-tokens
   # Copy token to .env:
   REPLICATE_API_TOKEN="r8_your_token_here"
   ```

2. **Set quotas:**
   ```bash
   # In .env:
   DEFAULT_DAILY_STICKER_LIMIT=10    # Free users
   COMPANY_DAILY_LIMIT=1000          # System-wide cap
   ```

3. **Test:**
   ```bash
   python test_image_gen.py
   ```

4. **Monitor:**
   - Check database `daily_usage` table
   - Track API costs in Replicate dashboard
   - Set alerts at 80% of COMPANY_DAILY_LIMIT

## ❓ FAQ

**Q: Should I create one API key per device?**  
A: NO! Backend uses ONE key for all devices. Devices authenticate with device_token.

**Q: How do I limit a specific device?**  
A: Update `devices.daily_limit` in database OR set `devices.paused = true`

**Q: What if a device is hacked?**  
A: Pause it in DB. Attacker is still quota-limited and can't access your API keys.

**Q: Can devices bypass quotas?**  
A: NO! All quota checks happen on backend before API calls.

**Q: How do I implement subscription tiers?**  
A: Set different `device.daily_limit` values based on parent's subscription.

**Q: What's the failsafe against cost spikes?**  
A: `COMPANY_DAILY_LIMIT` caps total daily usage regardless of individual quotas.

---

**You're all set!** Your architecture is secure, scalable, and cost-controlled. 🎉
