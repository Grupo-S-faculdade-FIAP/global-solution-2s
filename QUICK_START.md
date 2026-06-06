# SNS Alerts System - Quick Start Guide

## 1️⃣ Setup Infrastructure (5 minutes)

```bash
# Navigate to project root
cd global-solutions

# Run automated setup script
./scripts/setup-sns.sh --environment development

# This will:
# ✅ Create SNS topic
# ✅ Create SQS DLQ
# ✅ Bind DLQ to topic
# ✅ Create CloudWatch alarm
# ✅ Update .env with SNS_TOPIC_ARN
```

## 2️⃣ Install Dependencies

```bash
# Install Python packages
pip install -r src/requirements.txt

# Key new package: tenacity (for retry logic)
```

## 3️⃣ Verify Configuration

```bash
# Check SNS configuration
python -c "
from app.core.sns_config import validate_sns_setup
is_valid, issues = validate_sns_setup()
print('Valid:', is_valid)
if issues:
    for issue in issues:
        print(f'  ⚠️ {issue}')
"
```

## 4️⃣ Run Tests

```bash
# Run all SNS E2E tests
pytest tests/test_sns_e2e.py -v

# Run specific test
pytest tests/test_sns_e2e.py::test_publish_storm_alert_success -v
```

## 5️⃣ Start Application

```bash
# Start FastAPI development server
python -m uvicorn app.main:app --reload

# API will be available at: http://localhost:8000
```

## 6️⃣ Test the System

### Via HTTP:

```bash
# Check alert system status
curl http://localhost:8000/alerts/status

# Send test alert
curl "http://localhost:8000/alerts/test?lat=-23.5505&lon=-46.6333&confidence=0.85"

# View CloudWatch metrics
curl http://localhost:8000/alerts/metrics

# Check DLQ
curl http://localhost:8000/alerts/dlq

# Reprocess DLQ messages
curl -X POST http://localhost:8000/alerts/retry-dlq
```

### Via Python:

```python
from app.services import sns_alerts

# Publish alert
message_id = sns_alerts.publish_storm_alert(
    bucket="satellite-images-gs2",
    key="screenshots/test.jpg",
    detections=[
        {"class": "storm", "confidence": 0.92},
    ]
)
print(f"Published: {message_id}")

# Check status
status = sns_alerts.sns_status()
print(status)
```

## 📊 Key Features

### Automatic Retries
- Transient errors (Throttling, ServiceUnavailable) retry automatically
- Exponential backoff: 1-10 seconds with jitter
- Permanent errors (AuthorizationError, InvalidParameter) fail immediately

### CloudWatch Metrics
- `StormAlertsSent` - Successful publications
- `StormAlertsFailed` - Failed publications
- `AlertsSkipped` - Unconfigured alerts
- Namespace: `GlobalSolutions`

### DLQ Management
```python
from app.infrastructure.aws.sns_dlq import SNSDLQManager

dlq = SNSDLQManager()
dlq.get_dlq_url_from_topic("arn:aws:sns:us-east-1:123456789012:storm-alerts")

# Read messages
messages = dlq.read_messages(max_messages=10)

# Reprocess all
results = dlq.reprocess_all(max_attempts=10)
print(f"Success: {results['Succeeded']}, Failed: {results['Failed']}")

# Get stats
stats = dlq.get_dlq_stats()
print(f"Queue has {stats['MessageCount']} messages")
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
SNS_ENABLED=true
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:storm-alerts-development

# Optional
SNS_ALERT_SUBJECT=Rain Alert — Storm Detected
AWS_REGION=us-east-1
```

### Configuration Validation

```python
from app.core.sns_config import validate_sns_setup

# Check all SNS settings
is_valid, issues = validate_sns_setup()

if not is_valid:
    print("Configuration issues found:")
    for issue in issues:
        print(f"  • {issue}")
```

## 📡 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/alerts/status` | GET | System status |
| `/alerts/metrics` | GET | CloudWatch metrics |
| `/alerts/dlq` | GET | DLQ messages |
| `/alerts/retry-dlq` | POST | Reprocess DLQ |
| `/alerts/test` | GET | Send test alert |
| `/alerts/history` | GET | Alert history |

## 🧪 Testing

```bash
# All SNS tests
pytest tests/test_sns_e2e.py -v

# Specific test
pytest tests/test_sns_e2e.py::test_publish_with_retry_on_transient_error -v

# With coverage
pytest tests/test_sns_e2e.py --cov=app.services.sns_alerts

# Watch mode (on file changes)
pytest tests/test_sns_e2e.py -v --tb=short -s --watch
```

## 🚀 Deployment

### Development
```bash
./scripts/setup-sns.sh --environment development
```

### Staging
```bash
./scripts/setup-sns.sh --environment staging --region us-east-1
```

### Production (CloudFormation)
```bash
aws cloudformation create-stack \
  --stack-name global-solutions-sns-prod \
  --template-body file://cloudformation/sns-setup.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
  --region us-east-1
```

## 📝 Logging

All operations are logged with detailed context:

```python
import logging

logger = logging.getLogger("app.services.sns_alerts")
logger.setLevel(logging.DEBUG)  # See retry attempts

# Or view logs from command line
tail -f logs/app.log
```

## 🆘 Troubleshooting

### SNS Topic Not Found
```bash
# Check topic configuration
./scripts/setup-sns.sh --environment development

# Or manually validate
python -c "from app.core.sns_config import validate_sns_setup; print(validate_sns_setup())"
```

### DLQ Has Messages
```bash
# View messages
curl http://localhost:8000/alerts/dlq

# Reprocess all
curl -X POST http://localhost:8000/alerts/retry-dlq
```

### Metrics Not Appearing
```bash
# Check CloudWatch
aws cloudwatch list-metrics --namespace GlobalSolutions --region us-east-1

# View metrics via API
curl http://localhost:8000/alerts/metrics
```

### Tests Fail
```bash
# Reinstall dependencies
pip install --upgrade -r src/requirements.txt

# Run with verbose output
pytest tests/test_sns_e2e.py -vv --tb=long
```

## 📚 Documentation

- **Full Implementation Guide:** `SNS_IMPLEMENTATION_SUMMARY.md`
- **Implementation Checklist:** `IMPLEMENTATION_CHECKLIST.txt`
- **API Documentation:** FastAPI docs at `/docs` (when running locally)

## 💡 Common Tasks

### Subscribe Email to Alerts
```python
from app.services import sns_alerts

result = sns_alerts.subscribe_email("user@example.com")
print(result)
# Returns: subscription ARN and confirmation instructions
```

### Create Topic Programmatically
```python
from app.core.sns_config import create_sns_topic, create_sqs_dlq, bind_dlq_to_topic

topic_arn = create_sns_topic("my-alerts")
dlq_url = create_sqs_dlq("my-alerts-dlq")
dlq_arn = f"arn:aws:sqs:us-east-1:123456789012:my-alerts-dlq"
bind_dlq_to_topic(topic_arn, dlq_arn)
```

### Check Current Metrics
```bash
curl http://localhost:8000/alerts/metrics | python -m json.tool
```

## ✅ Health Check

```bash
# Quick health check
curl http://localhost:8000/health

# SNS-specific check
curl http://localhost:8000/alerts/status
```

## 🎯 Next Steps

1. ✅ Run `./scripts/setup-sns.sh`
2. ✅ Install dependencies
3. ✅ Run tests: `pytest tests/test_sns_e2e.py -v`
4. ✅ Start app: `python -m uvicorn app.main:app --reload`
5. ✅ Test API: `curl http://localhost:8000/alerts/status`
6. ✅ Send test alert: `curl http://localhost:8000/alerts/test`

---

**Questions?** Check `SNS_IMPLEMENTATION_SUMMARY.md` for detailed documentation.

**Issues?** Check CloudWatch logs or use the troubleshooting section above.
