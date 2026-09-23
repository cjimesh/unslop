Exponential backoff with jitter for webhook retries, replacing the fixed 5s interval.

## Changes
- `webhook/delivery.go`: exponential backoff (base 2s, cap 5 min) with ±20% jitter, replacing the fixed 5s retry
- `webhook/delivery_test.go`: 6 new test cases for backoff scenarios
- `config/webhook.yaml`: updated schema

**Testing:** All existing tests pass. Verified retry intervals grow as expected against a mock endpoint returning 503s.

**Risk:** Deliveries during extended outages take longer to eventually succeed. Max attempts stays at 10.
