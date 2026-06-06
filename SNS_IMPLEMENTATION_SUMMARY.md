# SNS Alerts System - Implementation Summary

**Date:** June 6, 2025  
**Project:** Global Solutions - Environmental Intelligence  
**Status:** IMPLEMENTED ✅

## Overview

Complete implementation of production-grade SNS (Simple Notification Service) alert system with retry logic, CloudWatch metrics, Dead Letter Queue (DLQ) management, and monitoring dashboard.

---

## Implemented Features

### 1. ✅ Retry Logic with Tenacity (CRITICAL)

**File:** `src/app/services/sns_alerts.py`

- **Decorator:** `@retry` with 3 attempts max
- **Backoff Strategy:** Exponential backoff (1-10 seconds)
- **Transient Errors:** Automatically retries on:
  - `Throttling`
  - `ServiceUnavailable`
  - `RequestLimitExceeded`
- **Permanent Errors:** Does NOT retry on:
  - `AuthorizationError`
  - `InvalidParameter`
  - `NotFound`
  - `InvalidParameterException`

**Functions Affected:**
- `publish_storm_alert()` - Now with automatic retries
- `publish_simulated_alert()` - Now with automatic retries
- `_publish_to_sns_with_retry()` - Internal helper with retry decorator

**Dependencies Added:**
- `tenacity==9.0.0` in `src/requirements.txt`

### 2. ✅ CloudWatch Metrics (CRITICAL)

**File:** `src/app/services/sns_alerts.py`

**Metrics Tracked:**
- `StormAlertsSent` - Count of successfully published alerts
- `StormAlertsFailed` - Count of failed alert publications
- `AlertsSkipped` - Count of alerts skipped (SNS not configured)

**Properties:**
- **Namespace:** `GlobalSolutions`
- **Unit:** `Count`
- **Integration:** Automatic metric recording in all publish operations

**Function:** `_put_cloudwatch_metric(metric_name, value, unit)`

### 3. ✅ Dead Letter Queue (DLQ) Manager (IMPORTANT)

**File:** `src/app/infrastructure/aws/sns_dlq.py` (NEW)

**Class:** `SNSDLQManager`

**Key Methods:**
- `set_dlq_url(dlq_url)` - Configure DLQ URL
- `get_dlq_url_from_topic(topic_arn)` - Auto-discover DLQ from topic
- `read_messages(max_messages, wait_time)` - Read DLQ messages
- `get_dlq_stats()` - Get queue statistics
- `delete_message(receipt_handle)` - Delete processed message
- `reprocess_message(message)` - Republish failed message
- `reprocess_all(max_attempts)` - Batch reprocessing
- `purge_dlq()` - Purge all messages (destructive)

**CloudWatch Integration:**
- `DLQMessagesReprocessed` - Count of successfully reprocessed messages
- `DLQReprocessingFailed` - Count of reprocessing failures
- `DLQPurged` - Purge event count

### 4. ✅ E2E Tests for SNS (CRITICAL)

**File:** `tests/test_sns_e2e.py` (NEW)

**Test Coverage:** 15+ end-to-end tests

**Key Tests:**
1. `test_publish_storm_alert_success` - Successful SNS publish
2. `test_publish_storm_alert_with_cloudwatch_metrics` - Metric recording
3. `test_publish_storm_alert_failure_records_metric` - Failure metrics
4. `test_publish_with_retry_on_transient_error` - Retry logic
5. `test_publish_with_no_retry_on_permanent_error` - No-retry logic
6. `test_publish_empty_detections_skipped` - Empty detection handling
7. `test_publish_simulated_alert_success` - Simulated alerts
8. `test_error_classification` - Error type classification (parameterized)
9. `test_email_validation` - Email subscription validation
10. `test_sns_status_when_configured` - Status reporting
11. `test_sns_status_when_not_configured` - Unconfigured status
12. `test_message_format_contains_required_info` - Message format validation

**Mocking:**
- `@mock_sns` - SNS service mocking
- `@mock_cloudwatch` - CloudWatch service mocking
- Fixtures for AWS credentials and SNS configuration

### 5. ✅ Alerts Dashboard (IMPORTANT)

**File:** `src/app/routers/dashboard_alerts.py` (NEW)

**REST API Endpoints:**

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/alerts/status` | GET | System status | Enabled, configured, issues |
| `/alerts/metrics` | GET | CloudWatch metrics | 24h metrics with datapoints |
| `/alerts/dlq` | GET | DLQ messages | Queue stats + messages |
| `/alerts/retry-dlq` | POST | Reprocess DLQ | Reprocessing results |
| `/alerts/history` | GET | Alert history | Recent alerts (future) |
| `/alerts/test` | GET | Test alert send | MessageId + status |

**Query Parameters:**
- `max_messages` (1-10) - DLQ messages to retrieve
- `max_attempts` (1-100) - Messages to reprocess
- `lat`, `lon`, `confidence` - Test alert parameters
- `limit` (1-1000) - History limit

**Error Handling:**
- 400 Bad Request - SNS not configured
- 404 Not Found - DLQ not found
- 500 Internal Server Error - CloudWatch/AWS errors

### 6. ✅ Configuration Helpers (IMPORTANT)

**File:** `src/app/core/sns_config.py` (NEW)

**Functions:**

| Function | Purpose |
|----------|---------|
| `validate_sns_setup()` | Validate SNS configuration |
| `create_sns_topic()` | Create SNS topic |
| `create_sqs_dlq()` | Create SQS DLQ queue |
| `bind_dlq_to_topic()` | Link DLQ to topic |
| `setup_sns_dlq()` | Complete setup in one call |
| `get_topic_arn_from_env()` | Get topic ARN from env |
| `validate_topic_arn()` | Validate topic accessibility |

**Validation Checks:**
- SNS enabled in config
- Topic ARN defined
- Topic exists and accessible
- DLQ configured (via RedrivePolicy)

### 7. ✅ CloudFormation Template (NICE-TO-HAVE)

**File:** `cloudformation/sns-setup.yaml` (NEW)

**Resources Created:**
- `StormAlertsTopic` - SNS topic
- `StormAlertsDLQ` - SQS DLQ queue
- `StormAlertsTopicDLQPolicy` - SNS publish policy
- `StormAlertsDLQPolicy` - SQS receive policy
- `StormAlertsLogGroup` - CloudWatch log group
- `DLQMessagesAlarm` - CloudWatch alarm for DLQ backlog

**Parameters:**
- `Environment` - deployment environment (dev/staging/prod)
- `TopicName` - topic name prefix
- `DLQName` - DLQ name prefix
- `MessageRetentionDays` - DLQ retention (default 14 days)

**Outputs:**
- Topic ARN
- DLQ URL & ARN
- Log Group name

**Features:**
- Auto-bind DLQ to topic
- CloudWatch alarms for monitoring
- Environment-specific naming
- Detailed documentation

### 8. ✅ Setup Script (NICE-TO-HAVE)

**File:** `scripts/setup-sns.sh` (NEW)

**Features:**
- Complete automated setup
- AWS CLI integration
- Environment validation
- .env file updates
- CloudWatch alarm creation
- Color-coded output
- Comprehensive error handling

**Usage:**
```bash
./scripts/setup-sns.sh                              # Default (development)
./scripts/setup-sns.sh --environment staging        # Staging setup
./scripts/setup-sns.sh --environment production     # Production setup
./scripts/setup-sns.sh --region us-west-2          # Custom region
./scripts/setup-sns.sh --help                       # Show help
```

**Steps Performed:**
1. Validate AWS CLI & credentials
2. Check/create .env file
3. Create SNS topic
4. Create SQS DLQ
5. Bind DLQ to topic
6. Create CloudWatch alarms
7. Update .env with SNS_TOPIC_ARN

---

## File Structure

```
global-solutions/
├── src/requirements.txt (UPDATED)
│   └── Added: tenacity==9.0.0
│
├── src/app/
│   ├── services/
│   │   └── sns_alerts.py (UPDATED)
│   │       ├── Retry logic with @retry decorator
│   │       ├── CloudWatch metrics
│   │       └── Error classification
│   │
│   ├── infrastructure/aws/
│   │   └── sns_dlq.py (NEW)
│   │       └── SNSDLQManager class
│   │
│   ├── core/
│   │   └── sns_config.py (NEW)
│   │       └── Setup & validation helpers
│   │
│   └── routers/
│       └── dashboard_alerts.py (NEW)
│           └── Alert monitoring REST API
│
├── tests/
│   └── test_sns_e2e.py (NEW)
│       └── 15+ E2E tests with moto
│
├── cloudformation/
│   └── sns-setup.yaml (NEW)
│       └── CloudFormation template
│
└── scripts/
    └── setup-sns.sh (NEW)
        └── Automated setup script (executable)
```

---

## Integration Points

### FastAPI Router Registration

**File:** `src/app/main.py` (UPDATED)

```python
from app.routers import dashboard_alerts

# Register alerts router
app.include_router(dashboard_alerts.router, tags=["Alerts"])
```

All `/alerts/*` endpoints automatically available.

---

## Environment Configuration

### Required Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
SNS_ENABLED=true
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:storm-alerts-development

# Optional
SNS_ALERT_SUBJECT=Rain Alert — Storm Detected
```

### Automated Setup

Use the provided script:
```bash
./scripts/setup-sns.sh --environment development
```

This will:
1. Create SNS topic
2. Create SQS DLQ
3. Bind them together
4. Update .env file automatically

---

## Usage Examples

### Publish Storm Alert (with automatic retries)

```python
from app.services import sns_alerts

message_id = sns_alerts.publish_storm_alert(
    bucket="satellite-images-gs2",
    key="screenshots/storm_20250606.jpg",
    detections=[
        {"class": "storm", "confidence": 0.92},
        {"class": "cloud", "confidence": 0.87},
    ]
)

if message_id:
    print(f"Alert sent: {message_id}")
```

### Monitor DLQ

```python
from app.infrastructure.aws.sns_dlq import SNSDLQManager

dlq = SNSDLQManager()
dlq.set_dlq_url("https://queue.amazonaws.com/123456789012/storm-alerts-dlq")

# Read messages
messages = dlq.read_messages(max_messages=10)

# Reprocess all
results = dlq.reprocess_all(max_attempts=10)
print(f"Reprocessed: {results['Succeeded']} succeeded, {results['Failed']} failed")

# Get stats
stats = dlq.get_dlq_stats()
print(f"DLQ has {stats['MessageCount']} messages")
```

### Check SNS Configuration

```python
from app.core.sns_config import validate_sns_setup

is_valid, issues = validate_sns_setup()
if is_valid:
    print("SNS setup is valid!")
else:
    print("Issues found:")
    for issue in issues:
        print(f"  - {issue}")
```

### API Endpoints

```bash
# Check system status
curl http://localhost:8000/alerts/status

# Get CloudWatch metrics
curl http://localhost:8000/alerts/metrics

# View DLQ messages
curl http://localhost:8000/alerts/dlq?max_messages=5

# Reprocess DLQ
curl -X POST http://localhost:8000/alerts/retry-dlq?max_attempts=10

# Send test alert
curl "http://localhost:8000/alerts/test?lat=-23.5505&lon=-46.6333&confidence=0.85"
```

---

## Testing

### Run E2E Tests

```bash
# Install test dependencies
pip install -r src/requirements.txt

# Run all SNS tests
pytest tests/test_sns_e2e.py -v

# Run specific test
pytest tests/test_sns_e2e.py::test_publish_storm_alert_success -v

# With coverage
pytest tests/test_sns_e2e.py --cov=app.services.sns_alerts --cov-report=html
```

### Test Coverage

- ✅ Successful message publishing
- ✅ Retry logic on transient errors
- ✅ No-retry on permanent errors
- ✅ CloudWatch metric recording
- ✅ DLQ message handling
- ✅ Email validation
- ✅ Configuration validation
- ✅ Error classification

---

## Deployment

### Development

```bash
# Setup SNS infrastructure
./scripts/setup-sns.sh --environment development

# Start application
python -m uvicorn app.main:app --reload

# Test alerts
curl "http://localhost:8000/alerts/test"
```

### Staging/Production

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name global-solutions-sns-staging \
  --template-body file://cloudformation/sns-setup.yaml \
  --parameters ParameterKey=Environment,ParameterValue=staging \
  --region us-east-1

# Or use the setup script
./scripts/setup-sns.sh --environment staging --region us-east-1
```

---

## Monitoring

### CloudWatch Metrics

**Namespace:** `GlobalSolutions`

**Metrics:**
- `StormAlertsSent` - Successful publications
- `StormAlertsFailed` - Failed publications
- `AlertsSkipped` - Unconfigured alerts
- `DLQMessagesReprocessed` - Recovered messages
- `DLQReprocessingFailed` - Recovery failures
- `DLQPurged` - Manual purges

### CloudWatch Alarms

- `StormAlerts-DLQ-HasMessages-{env}` - Triggers when DLQ has messages

### Logs

- SNS logs: `/aws/sns/global-solutions/{env}`
- Application logs: Standard FastAPI logging

---

## Error Handling & Recovery

### Retry Logic

Transient errors automatically retry with exponential backoff:

```
Attempt 1: Immediate (wait 1s)
Attempt 2: After ~1-3s (wait 2-6s)
Attempt 3: After ~3-10s
All delays have random jitter to prevent thundering herd
```

### DLQ Recovery

Failed messages automatically go to DLQ where they can be:
1. Viewed: `GET /alerts/dlq`
2. Reprocessed: `POST /alerts/retry-dlq`
3. Investigated: CloudWatch Logs & Metrics

### Permanent Errors

Authorization and configuration errors are NOT retried and logged immediately.

---

## Performance & Scalability

- **Async Ready:** Compatible with FastAPI async/await
- **Rate Limiting:** Works with existing slowapi rate limiter
- **CloudWatch Integration:** Automatic metrics without extra latency
- **DLQ Processing:** Batch operations (up to 100 messages at a time)
- **Exponential Backoff:** Prevents API throttling and thundering herd

---

## Security Considerations

- **No Credentials in Code:** Uses AWS IAM roles in Lambda
- **Environment Isolation:** Environment-specific topic names
- **Error Messages:** Sensitive details logged but not exposed to API clients
- **DLQ Access:** Requires SQS permissions (restricted by IAM)

---

## Future Enhancements

1. **Alert History:** Integration with DynamoDB for persistent alert storage
2. **Subscriptions Management:** UI for managing email subscriptions
3. **Webhooks:** Support for HTTP-based alert delivery
4. **SMS Alerts:** Integration with SNS SMS topic
5. **Alert Filtering:** Fine-grained alert rules per location/risk level
6. **Batch Publishing:** Support for bulk alert operations

---

## Troubleshooting

### SNS Topic Not Found

```python
from app.core.sns_config import validate_sns_setup
is_valid, issues = validate_sns_setup()
print(issues)  # See specific problems
```

### DLQ Has Messages

```bash
# Check queue
curl http://localhost:8000/alerts/dlq

# Reprocess
curl -X POST http://localhost:8000/alerts/retry-dlq
```

### Metrics Not Appearing

```bash
# Check CloudWatch
aws cloudwatch list-metrics --namespace GlobalSolutions --region us-east-1

# Check logs
aws logs tail /aws/sns/global-solutions/development --follow
```

---

## Dependencies

### Production Dependencies

- `boto3>=1.35.74` - AWS SDK
- `tenacity>=9.0.0` - Retry logic (NEW)
- `fastapi>=0.115.5` - Web framework
- `pydantic>=2.10.3` - Data validation

### Test Dependencies

- `pytest>=8.3.3` - Testing framework
- `pytest-asyncio>=0.24.0` - Async test support
- `moto[s3,dynamodb,sns]>=5.0.28` - AWS mocking

---

## Implementation Checklist

- ✅ Retry logic with Tenacity (3 attempts, exponential backoff)
- ✅ Transient error detection (Throttling, ServiceUnavailable)
- ✅ Permanent error handling (AuthorizationError, InvalidParameter)
- ✅ CloudWatch metrics (StormAlertsSent, StormAlertsFailed, AlertsSkipped)
- ✅ SNS DLQ Manager (read, reprocess, stats)
- ✅ DLQ message recovery
- ✅ E2E tests with moto (15+ tests)
- ✅ Alerts dashboard API (6 endpoints)
- ✅ Configuration helpers & validation
- ✅ CloudFormation template
- ✅ Automated setup script
- ✅ FastAPI router integration
- ✅ Comprehensive documentation
- ✅ Error handling & logging
- ✅ Type hints & docstrings

---

## Summary

This implementation provides a **production-grade SNS alert system** with:

1. **Reliability:** Automatic retries on transient failures, DLQ for recovery
2. **Observability:** CloudWatch metrics, logs, and monitoring dashboard
3. **Manageability:** Configuration helpers, setup automation, REST API
4. **Testing:** Comprehensive E2E tests with moto mocking
5. **Documentation:** Clear setup instructions, API docs, examples

The system is ready for deployment to AWS Lambda with full monitoring and recovery capabilities.

---

**Implementation Date:** June 6, 2025  
**Status:** COMPLETE ✅  
**Ready for:** Development, Staging, Production
