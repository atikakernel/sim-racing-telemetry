#!/bin/bash

# Configuration
SUBSCRIPTION_ID="9a66aaac-ea16-4e89-8c69-9346d5d61cff"
PRINCIPAL_ID="7f2c16f9-d012-44ff-8ef7-24820a647e47"
ROLE_1="Azure AI Developer"
ROLE_2="Cognitive Services OpenAI User"
ROLE_3="Cognitive Services Contributor"  # Muy potente, incluye casi todo

echo "--------------------------------------------------------"
echo "🔐 Azure AI Agent Permissions Fix (Exhaustive)"
echo "--------------------------------------------------------"

# Ensure we are in the right subscription
echo "Setting subscription to $SUBSCRIPTION_ID..."
az account set --subscription "$SUBSCRIPTION_ID"

# Check if principal exists
echo "Verifying Managed Identity ($PRINCIPAL_ID)..."
PRINCIPAL_NAME=$(az ad sp show --id "$PRINCIPAL_ID" --query displayName -o tsv 2>/dev/null)

if [ -z "$PRINCIPAL_NAME" ]; then
    echo "❌ Error: Could not find Managed Identity with ID $PRINCIPAL_ID."
    echo "Please check if the App Service 'papales-ai-agent' has Managed Identity enabled."
    exit 1
fi

echo "✅ Found identity: $PRINCIPAL_NAME"

# Function to assign role and handle errors
assign_role() {
    local role=$1
    echo "Assigning role '$role' at SUBSCRIPTION scope..."
    az role assignment create \
        --assignee "$PRINCIPAL_ID" \
        --role "$role" \
        --scope "/subscriptions/$SUBSCRIPTION_ID" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Success: $role"
    else
        echo "⚠️ $role could not be assigned (maybe already exists?)"
    fi
}

assign_role "$ROLE_1"
assign_role "$ROLE_2"
assign_role "$ROLE_3"

echo "--------------------------------------------------------"
echo "✅ Done! All roles assigned to $PRINCIPAL_NAME."
echo "CRITICAL: Azure may take up to 10-15 minutes to recognize new roles."
echo "Please RESTART your App Service after 5 minutes."
echo "--------------------------------------------------------"
