#!/bin/bash

# Script to create service principal with Security Reader role at tenant root level
# This gives read access to all subscriptions in the tenant

set -e

SP_NAME="mdc-agent-api-sp"
ROLE="Security Reader"

echo "=========================================="
echo "Service Principal Setup for MDC Agent API"
echo "=========================================="
echo ""

# Check if user is logged in
if ! az account show &>/dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

# Get current user info
CURRENT_USER=$(az account show --query user.name -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "Current user: $CURRENT_USER"
echo "Tenant ID: $TENANT_ID"
echo ""

# Check if service principal already exists
echo "Checking if service principal '$SP_NAME' exists..."
SP_EXISTS=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv 2>/dev/null)

if [ -n "$SP_EXISTS" ] && [ "$SP_EXISTS" != "null" ]; then
    echo "✅ Service principal already exists"
    APP_ID="$SP_EXISTS"
    echo "   App ID: $APP_ID"
    echo ""

    # Ask if user wants to generate new secret
    read -p "Generate new secret for existing service principal? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Generating new secret..."
        CREDENTIAL_OUTPUT=$(az ad sp credential reset \
            --id "$APP_ID" \
            --append \
            --years 1 \
            --output json)
        PASSWORD=$(echo "$CREDENTIAL_OUTPUT" | jq -r '.password')
        GENERATED_NEW_SECRET=true
    else
        echo "⚠️  Using existing credentials (secret not regenerated)"
        PASSWORD="<existing-secret-not-shown>"
        GENERATED_NEW_SECRET=false
    fi
else
    echo "Service principal does not exist. Creating..."

    # Create service principal without role assignment (we'll add it at tenant root)
    SP_OUTPUT=$(az ad sp create-for-rbac \
        --name "$SP_NAME" \
        --skip-assignment \
        --years 1 \
        --output json)

    APP_ID=$(echo "$SP_OUTPUT" | jq -r '.appId')
    PASSWORD=$(echo "$SP_OUTPUT" | jq -r '.password')

    echo "✅ Service principal created"
    echo "   App ID: $APP_ID"
    echo ""
    GENERATED_NEW_SECRET=true

    # Wait a few seconds for SP to propagate
    echo "Waiting for service principal to propagate..."
    sleep 10
fi

# Get Tenant Root Group management group ID
echo "Getting Tenant Root Group management group..."
TENANT_ROOT_MG=$(az account management-group list --query "[?name=='$TENANT_ID'].id" -o tsv 2>/dev/null)

if [ -z "$TENANT_ROOT_MG" ]; then
    # Try alternate name format
    TENANT_ROOT_MG=$(az account management-group list --query "[?displayName=='Tenant Root Group'].id" -o tsv 2>/dev/null)
fi

if [ -z "$TENANT_ROOT_MG" ]; then
    echo ""
    echo "⚠️  Tenant Root Group not found. This could mean:"
    echo "   1. Your account doesn't have access to management groups"
    echo "   2. Management groups are not set up in your tenant"
    echo ""
    echo "Attempting to assign role at all accessible subscriptions instead..."
    echo ""

    # Get all subscriptions
    SUBSCRIPTIONS=$(az account list --query "[].id" -o tsv)

    if [ -z "$SUBSCRIPTIONS" ]; then
        echo "❌ No subscriptions found. Cannot assign role."
        exit 1
    fi

    # Assign role to each subscription
    for SUB_ID in $SUBSCRIPTIONS; do
        SUB_NAME=$(az account show --subscription "$SUB_ID" --query name -o tsv)
        echo "Assigning '$ROLE' role to subscription: $SUB_NAME ($SUB_ID)"

        # Check if role assignment already exists
        EXISTING_ASSIGNMENT=$(az role assignment list \
            --assignee "$APP_ID" \
            --role "$ROLE" \
            --scope "/subscriptions/$SUB_ID" \
            --query "[0].id" -o tsv 2>/dev/null)

        if [ -n "$EXISTING_ASSIGNMENT" ]; then
            echo "   ✓ Role already assigned"
        else
            az role assignment create \
                --assignee "$APP_ID" \
                --role "$ROLE" \
                --scope "/subscriptions/$SUB_ID" \
                --output none
            echo "   ✓ Role assigned"
        fi
    done

    SCOPE_INFO="All accessible subscriptions"
else
    echo "✅ Found Tenant Root Group: $TENANT_ROOT_MG"
    echo ""

    # Check if role assignment already exists
    echo "Checking for existing role assignment..."
    EXISTING_ASSIGNMENT=$(az role assignment list \
        --assignee "$APP_ID" \
        --role "$ROLE" \
        --scope "$TENANT_ROOT_MG" \
        --query "[0].id" -o tsv 2>/dev/null)

    if [ -n "$EXISTING_ASSIGNMENT" ]; then
        echo "✅ '$ROLE' role already assigned at Tenant Root Group"
    else
        echo "Assigning '$ROLE' role at Tenant Root Group..."
        az role assignment create \
            --assignee "$APP_ID" \
            --role "$ROLE" \
            --scope "$TENANT_ROOT_MG" \
            --output none
        echo "✅ Role assigned successfully"
    fi

    SCOPE_INFO="Tenant Root Group (all subscriptions)"
fi

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Service Principal: $SP_NAME"
echo "App ID: $APP_ID"
echo "Tenant ID: $TENANT_ID"
echo "Role: $ROLE"
echo "Scope: $SCOPE_INFO"
echo ""

if [ "$GENERATED_NEW_SECRET" = true ]; then
    echo "⚠️  SAVE THIS SECRET NOW - IT WON'T BE SHOWN AGAIN:"
    echo ""
    echo "AZURE_CLIENT_SECRET=$PASSWORD"
    echo ""
fi

echo "=========================================="
echo "Environment Variables for .env file:"
echo "=========================================="
echo ""
echo "AZURE_CLIENT_ID=$APP_ID"
if [ "$GENERATED_NEW_SECRET" = true ]; then
    echo "AZURE_CLIENT_SECRET=$PASSWORD"
else
    echo "AZURE_CLIENT_SECRET=<use-your-existing-secret>"
fi
echo "AZURE_TENANT_ID=$TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID=<your-default-subscription-id>"
echo ""

# Optionally create/update .env file
read -p "Do you want to create/update .env file? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Get default subscription
    DEFAULT_SUB=$(az account show --query id -o tsv 2>/dev/null || echo "<your-subscription-id>")

    if [ -f .env ]; then
        echo "⚠️  .env file exists. Creating backup..."
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    fi

    cat > .env << ENVEOF
# Azure Service Principal Credentials (Generated: $(date))
# Service Principal: $SP_NAME
# Scope: $SCOPE_INFO
AZURE_CLIENT_ID=$APP_ID
AZURE_CLIENT_SECRET=${PASSWORD}
AZURE_TENANT_ID=$TENANT_ID
AZURE_SUBSCRIPTION_ID=$DEFAULT_SUB

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Azure AD Authentication (for API endpoints)
AZURE_AD_TENANT_ID=$TENANT_ID
AZURE_AD_CLIENT_ID=<api-app-registration-client-id>
AZURE_AD_AUDIENCE=api://mdc-agent-api

# Feature Flags
ENABLE_ACTIVE_USER=true
ENVEOF

    echo "✅ Created/updated .env file"
    if [ "$DEFAULT_SUB" = "<your-subscription-id>" ]; then
        echo "⚠️  Don't forget to update AZURE_SUBSCRIPTION_ID in .env!"
    fi
fi

echo ""
echo "=========================================="
echo "Verify the service principal:"
echo "=========================================="
echo ""
echo "# Login with service principal"
echo "az login --service-principal \\"
echo "  -u $APP_ID \\"
echo "  -p <your-secret> \\"
echo "  --tenant $TENANT_ID"
echo ""
echo "# List all subscriptions accessible to the SP"
echo "az account list --output table"
echo ""
echo "# Test access to security assessments"
echo "az security assessment list --subscription <subscription-id> | head"
echo ""
echo "=========================================="
echo "Next steps:"
echo "=========================================="
echo ""
echo "1. Copy the credentials to your .env file (done if you selected yes)"
echo "2. Test the service principal authentication"
echo "3. Run the MDC Agent API: uv run uvicorn src.main:app --reload"
echo ""
