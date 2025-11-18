#!/bin/bash

# Script to add a new secret to an existing service principal

echo "=========================================="
echo "Add Secret to Service Principal"
echo "=========================================="
echo ""

# Check if service principal name/ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <service-principal-name-or-app-id>"
    echo ""
    echo "Example: $0 mdc-agent-api-sp"
    echo "     or: $0 12345678-1234-1234-1234-123456789012"
    exit 1
fi

SP_NAME_OR_ID="$1"

# Get service principal details
echo "Looking up service principal: $SP_NAME_OR_ID"
SP_INFO=$(az ad sp list --display-name "$SP_NAME_OR_ID" --query "[0]" 2>/dev/null)

if [ -z "$SP_INFO" ] || [ "$SP_INFO" = "null" ]; then
    # Try by app ID
    SP_INFO=$(az ad sp show --id "$SP_NAME_OR_ID" 2>/dev/null)
fi

if [ -z "$SP_INFO" ] || [ "$SP_INFO" = "null" ]; then
    echo "❌ Service principal not found: $SP_NAME_OR_ID"
    exit 1
fi

APP_ID=$(echo "$SP_INFO" | jq -r '.appId')
DISPLAY_NAME=$(echo "$SP_INFO" | jq -r '.displayName')

echo "✅ Found service principal: $DISPLAY_NAME"
echo "   App ID: $APP_ID"
echo ""

# Add new credential (password/secret)
echo "Generating new secret..."
CREDENTIAL_OUTPUT=$(az ad sp credential reset \
    --id "$APP_ID" \
    --append \
    --years 1 \
    --output json)

# Extract values
PASSWORD=$(echo "$CREDENTIAL_OUTPUT" | jq -r '.password')
TENANT_ID=$(echo "$CREDENTIAL_OUTPUT" | jq -r '.tenant')

echo ""
echo "=========================================="
echo "✅ NEW SECRET GENERATED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "Service Principal: $DISPLAY_NAME"
echo "App ID: $APP_ID"
echo "Tenant ID: $TENANT_ID"
echo ""
echo "⚠️  SAVE THIS SECRET NOW - IT WON'T BE SHOWN AGAIN:"
echo ""
echo "AZURE_CLIENT_SECRET=$PASSWORD"
echo ""
echo "=========================================="
echo "Complete Environment Variables:"
echo "=========================================="
echo ""
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_CLIENT_SECRET=$PASSWORD"
echo "AZURE_TENANT_ID=$TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID=<your-subscription-id>"
echo ""

# Optionally create/update .env file
read -p "Do you want to update .env file? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f .env ]; then
        echo "⚠️  .env file exists. Creating backup..."
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    cat > .env << ENVEOF
# Azure Service Principal Credentials (Generated: $(date))
AZURE_CLIENT_ID=$APP_ID
AZURE_CLIENT_SECRET=$PASSWORD
AZURE_TENANT_ID=$TENANT_ID
AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Feature Flags
ENABLE_ACTIVE_USER=true
ENVEOF
    
    echo "✅ Created/updated .env file"
    echo "⚠️  Don't forget to update AZURE_SUBSCRIPTION_ID in .env!"
fi

echo ""
echo "=========================================="
echo "Test the credentials:"
echo "=========================================="
echo ""
echo "az login --service-principal \\"
echo "  -u $APP_ID \\"
echo "  -p <the-password-above> \\"
echo "  --tenant $TENANT_ID"
echo ""

