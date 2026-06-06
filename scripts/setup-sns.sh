#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SNS Setup Script for Global Solutions Storm Alerts
#
# This script sets up the complete SNS + DLQ infrastructure for storm alerts.
# It creates:
# 1. SNS topic for publishing alerts
# 2. SQS DLQ for failed messages
# 3. Binds DLQ to SNS topic
# 4. Configures CloudWatch metrics and alarms
# 5. Updates environment variables
#
# Usage:
#   ./setup-sns.sh [--environment dev|staging|prod]
#   ./setup-sns.sh --help
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env"
CLOUDFORMATION_TEMPLATE="${PROJECT_ROOT}/cloudformation/sns-setup.yaml"

ENVIRONMENT="${ENVIRONMENT:-development}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TOPIC_NAME="${TOPIC_NAME:-storm-alerts}"
DLQ_NAME="${DLQ_NAME:-storm-alerts-dlq}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────────────────────────────
# Functions
# ─────────────────────────────────────────────────────────────────────────────

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

print_usage() {
    cat <<EOF
Usage: ./setup-sns.sh [OPTIONS]

Options:
    --environment ENV      Deployment environment (development|staging|production)
                          Default: development
    --region REGION       AWS region
                          Default: us-east-1
    --topic-name NAME     SNS topic name (without environment suffix)
                          Default: storm-alerts
    --dlq-name NAME       SQS DLQ name (without environment suffix)
                          Default: storm-alerts-dlq
    --help               Show this help message

Examples:
    ./setup-sns.sh
    ./setup-sns.sh --environment staging --region us-west-2
    ./setup-sns.sh --environment production
EOF
}

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        echo "Install AWS CLI: https://aws.amazon.com/cli/"
        exit 1
    fi
    log_success "AWS CLI found: $(aws --version)"
}

check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        echo "Configure credentials: aws configure"
        exit 1
    fi

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS credentials valid (Account: $ACCOUNT_ID)"
}

check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "No .env file found. Creating template..."
        cat > "$ENV_FILE" <<'ENVTEMPLATE'
# AWS Configuration
AWS_REGION=us-east-1
SNS_ENABLED=true
SNS_TOPIC_ARN=

# Application Configuration
PROJECT_NAME=Global Solutions
ENVIRONMENT=development
ENVTEMPLATE
        log_success "Created .env template at $ENV_FILE"
        return 1
    fi
    return 0
}

create_sns_topic() {
    local full_topic_name="${TOPIC_NAME}-${ENVIRONMENT}"

    log_info "Creating SNS topic: $full_topic_name"

    if TOPIC_ARN=$(aws sns create-topic \
        --name "$full_topic_name" \
        --region "$AWS_REGION" \
        --query 'TopicArn' \
        --output text 2>/dev/null); then

        log_success "SNS topic created: $TOPIC_ARN"
        echo "$TOPIC_ARN"
        return 0
    else
        # Topic might already exist
        log_warning "Failed to create topic (may already exist), attempting to get existing..."
        if TOPIC_ARN=$(aws sns list-topics \
            --region "$AWS_REGION" \
            --query "Topics[?contains(TopicArn, '$full_topic_name')].TopicArn" \
            --output text); then

            if [ -n "$TOPIC_ARN" ]; then
                log_success "Using existing SNS topic: $TOPIC_ARN"
                echo "$TOPIC_ARN"
                return 0
            fi
        fi
        return 1
    fi
}

create_sqs_dlq() {
    local full_dlq_name="${DLQ_NAME}-${ENVIRONMENT}"

    log_info "Creating SQS DLQ: $full_dlq_name"

    if QUEUE_URL=$(aws sqs create-queue \
        --queue-name "$full_dlq_name" \
        --attributes "MessageRetentionPeriod=1209600,VisibilityTimeout=300" \
        --region "$AWS_REGION" \
        --query 'QueueUrl' \
        --output text 2>/dev/null); then

        log_success "SQS DLQ created: $QUEUE_URL"
        echo "$QUEUE_URL"
        return 0
    else
        # Queue might already exist
        log_warning "Failed to create queue (may already exist), attempting to get existing..."
        if QUEUE_URL=$(aws sqs get-queue-url \
            --queue-name "$full_dlq_name" \
            --region "$AWS_REGION" \
            --query 'QueueUrl' \
            --output text); then

            log_success "Using existing SQS DLQ: $QUEUE_URL"
            echo "$QUEUE_URL"
            return 0
        fi
        return 1
    fi
}

get_queue_arn_from_url() {
    local queue_url="$1"
    local queue_arn

    queue_arn=$(aws sqs get-queue-attributes \
        --queue-url "$queue_url" \
        --attribute-names QueueArn \
        --region "$AWS_REGION" \
        --query 'Attributes.QueueArn' \
        --output text)

    echo "$queue_arn"
}

bind_dlq_to_topic() {
    local topic_arn="$1"
    local queue_arn="$2"

    log_info "Binding DLQ to SNS topic..."

    local redrive_policy="{\"deadLetterTargetArn\": \"$queue_arn\"}"

    if aws sns set-topic-attributes \
        --topic-arn "$topic_arn" \
        --attribute-name RedrivePolicy \
        --attribute-value "$redrive_policy" \
        --region "$AWS_REGION"; then

        log_success "DLQ bound to SNS topic"
        return 0
    else
        log_error "Failed to bind DLQ to topic"
        return 1
    fi
}

update_env_file() {
    local topic_arn="$1"

    log_info "Updating .env file with SNS_TOPIC_ARN..."

    if grep -q "^SNS_TOPIC_ARN=" "$ENV_FILE"; then
        # Update existing line
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^SNS_TOPIC_ARN=.*|SNS_TOPIC_ARN=$topic_arn|" "$ENV_FILE"
        else
            # Linux
            sed -i "s|^SNS_TOPIC_ARN=.*|SNS_TOPIC_ARN=$topic_arn|" "$ENV_FILE"
        fi
    else
        # Add new line
        echo "SNS_TOPIC_ARN=$topic_arn" >> "$ENV_FILE"
    fi

    log_success "Updated .env file: SNS_TOPIC_ARN=$topic_arn"
}

create_cloudwatch_alarms() {
    local dlq_queue_name="${DLQ_NAME}-${ENVIRONMENT}"

    log_info "Creating CloudWatch alarms..."

    if aws cloudwatch put-metric-alarm \
        --alarm-name "StormAlerts-DLQ-HasMessages-${ENVIRONMENT}" \
        --alarm-description "Alert when DLQ has failed messages" \
        --metric-name ApproximateNumberOfMessagesVisible \
        --namespace AWS/SQS \
        --statistic Maximum \
        --period 300 \
        --evaluation-periods 1 \
        --threshold 1 \
        --comparison-operator GreaterThanOrEqualToThreshold \
        --dimensions Name=QueueName,Value="$dlq_queue_name" \
        --region "$AWS_REGION"; then

        log_success "CloudWatch alarm created"
        return 0
    else
        log_warning "Failed to create CloudWatch alarm (may already exist)"
        return 1
    fi
}

print_summary() {
    local topic_arn="$1"
    local queue_url="$2"
    local queue_arn="$3"

    cat <<EOF

${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}
${GREEN}SNS Setup Complete!${NC}
${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}

Environment:        $ENVIRONMENT
AWS Region:         $AWS_REGION

Resources Created:
  SNS Topic ARN:    $topic_arn
  SQS DLQ URL:      $queue_url
  SQS DLQ ARN:      $queue_arn

Next Steps:

1. Verify the resources were created:
   aws sns list-topics --region $AWS_REGION
   aws sqs list-queues --region $AWS_REGION

2. Deploy the Lambda function with environment variables:
   export SNS_TOPIC_ARN=$topic_arn
   export AWS_REGION=$AWS_REGION

3. Test the alert system:
   curl -X GET "http://localhost:8000/alerts/test?confidence=0.85"

4. Monitor alerts:
   aws sqs receive-message --queue-url $queue_url --region $AWS_REGION

5. View CloudWatch metrics:
   aws cloudwatch list-metrics --namespace GlobalSolutions --region $AWS_REGION

Documentation:
  - SNS Configuration: src/app/core/sns_config.py
  - DLQ Manager: src/app/infrastructure/aws/sns_dlq.py
  - Alert Router: src/app/routers/dashboard_alerts.py
  - Alert Service: src/app/services/sns_alerts.py

${YELLOW}Important:${NC}
  - SNS_TOPIC_ARN has been saved to $ENV_FILE
  - Restart your application to pick up the new environment variable
  - Test alerts before deploying to production

${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}

EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Parse Arguments
# ─────────────────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --topic-name)
            TOPIC_NAME="$2"
            shift 2
            ;;
        --dlq-name)
            DLQ_NAME="$2"
            shift 2
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Main Execution
# ─────────────────────────────────────────────────────────────────────────────

main() {
    log_info "Global Solutions SNS Setup Script"
    log_info "Environment: $ENVIRONMENT, Region: $AWS_REGION"
    echo

    # Check prerequisites
    check_aws_cli
    check_aws_credentials
    check_env_file || log_warning "Starting with new .env file"
    echo

    # Create resources
    TOPIC_ARN=$(create_sns_topic) || exit 1
    echo
    QUEUE_URL=$(create_sqs_dlq) || exit 1
    echo
    QUEUE_ARN=$(get_queue_arn_from_url "$QUEUE_URL")
    log_success "Queue ARN: $QUEUE_ARN"
    echo

    # Bind DLQ to topic
    bind_dlq_to_topic "$TOPIC_ARN" "$QUEUE_ARN" || exit 1
    echo

    # Create alarms
    create_cloudwatch_alarms
    echo

    # Update environment file
    update_env_file "$TOPIC_ARN"
    echo

    # Print summary
    print_summary "$TOPIC_ARN" "$QUEUE_URL" "$QUEUE_ARN"
}

main "$@"
