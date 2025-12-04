from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "any_secret_key")
    MONGO_URL = os.getenv("MONGO_URL")
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "email_tracking")
    TENANT_ID = os.getenv("TENANT_ID")
    PORT = int(os.getenv("PORT", 5000))
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    BASE_URL = os.getenv("BASE_URL")
    MIN_DELAY_BETWEEN_EMAILS = os.getenv("MIN_DELAY_BETWEEN_EMAILS", 60)
    MAX_DELAY_BETWEEN_EMAILS = int(os.getenv("MAX_DELAY_BETWEEN_EMAILS", 100))
    AUTHORITY = "https://login.microsoftonline.com/common"
    GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
    USER_SCOPES = [
    "openid",
    "profile",
    # "offline_access",
    "User.Read",
    "Mail.ReadWrite",
    "Mail.Send"
]