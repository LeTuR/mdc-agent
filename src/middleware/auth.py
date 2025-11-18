"""Azure authentication middleware using DefaultAzureCredential.

Per constitution: Use Azure managed identity or service principal
authentication via DefaultAzureCredential for all Azure SDK operations.
"""

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential


def get_azure_credential() -> TokenCredential:
    """Get Azure credential for authenticating with Azure services.

    Uses DefaultAzureCredential which automatically tries:
    1. Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
    2. Managed Identity (when running in Azure)
    3. Azure CLI (for local development)
    4. VS Code Azure extension
    5. Azure PowerShell

    Returns:
        TokenCredential instance for Azure SDK authentication

    Raises:
        azure.identity.CredentialUnavailableError: If no authentication method
            is available

    Examples:
        >>> credential = get_azure_credential()
        >>> # Use with Azure SDK clients
        >>> from azure.mgmt.security import SecurityCenter
        >>> client = SecurityCenter(credential, subscription_id="...")
    """
    return DefaultAzureCredential()
