from core.secrets import get_secret
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.discovery_cache.base import Cache


class MemoryCache(Cache):
    _CACHE = {}

    def get(self, url):
        return MemoryCache._CACHE.get(url)

    def set(self, url, content):
        MemoryCache._CACHE[url] = content


def get_gdrive_credentials_info() -> dict:
    """
    Fetches Google Drive service account credentials info from secrets.
    Returns:
        dict: Credentials info dictionary for service_account.Credentials.from_service_account_info
    """
    return {
        "type": get_secret("GDRIVE_TYPE"),
        "project_id": get_secret("GDRIVE_PROJECT_ID"),
        "private_key_id": get_secret("GDRIVE_PRIVATE_KEY_ID"),
        "private_key": get_secret("GDRIVE_PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": get_secret("GDRIVE_CLIENT_EMAIL"),
        "client_id": get_secret("GDRIVE_CLIENT_ID"),
        "auth_uri": get_secret("GDRIVE_AUTH_URI"),
        "token_uri": get_secret("GDRIVE_TOKEN_URI"),
        "auth_provider_x509_cert_url": get_secret("GDRIVE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": get_secret("GDRIVE_CLIENT_X509_CERT_URL"),
        "universe_domain": get_secret("GDRIVE_UNIVERSE_DOMAIN"),
    }


def get_gdrive_service():
    """
    Returns an authenticated Google Drive service object.
    """
    credentials_info = get_gdrive_credentials_info()
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    return build("drive", "v3", credentials=credentials, cache=MemoryCache())
