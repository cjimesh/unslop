## Overview
This PR introduces a comprehensive refactoring of the retry logic within the webhook delivery service. Previously, the service utilized a fixed-interval retry mechanism, which could lead to thundering-herd issues when downstream endpoints experienced outages. In order to address this, I have implemented an exponential backoff strategy with jitter.

## Changes Made
- Modified `webhook/delivery.go` to replace the fixed 5s interval with exponential backoff (base 2s, cap 5 min)
- Added jitter of ±20% to prevent synchronized retries
- Updated `webhook/delivery_test.go` with new test cases
- Updated the configuration schema in `config/webhook.yaml`

## Testing
I have thoroughly tested these changes. All existing unit tests pass, and I've added 6 new test cases covering various backoff scenarios. Additionally, I ran the service locally against a mock endpoint that returns 503 errors and verified that the retry intervals grow as expected.

## Considerations
It's worth noting that this change means some webhooks will now take longer to eventually deliver during extended outages. However, I believe this is an acceptable trade-off given the improved stability. Max attempts remains at 10.

Let me know if you have any questions or feedback!
