#!/bin/bash
set -e

FUNCTIONS=(
    "ingestor-fuel"
    "ingestor-freight"
    "ingestor-traffic"
    "ingestor-weather"
    "aggregator"
    "email-sender"
)

PROJECT_NAME=${1:-logistix}
ENVIRONMENT=${2:-dev}

echo "Deploying Lambda functions for $PROJECT_NAME-$ENVIRONMENT..."

for func in "${FUNCTIONS[@]}"; do
    echo "Packaging $func..."
    cd "$func"
    
    # Create deployment package
    zip -q -r "../${func}.zip" index.py
    
    # Update Lambda function
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-${func}-${ENVIRONMENT}" \
        --zip-file "fileb://../${func}.zip" \
        > /dev/null
    
    echo "✓ Deployed $func"
    cd ..
done

echo "All functions deployed successfully!"
