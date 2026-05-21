import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_env():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-this-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "payments",
]

MIDDLEWARE = [
    "config.settings.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def normalize_database_url(database_url):
    database_url = (database_url or "").strip().strip('"').strip("'")
    if database_url.startswith("DATABASE_URL="):
        database_url = database_url.split("=", 1)[1].strip().strip('"').strip("'")
    return database_url


def postgres_database_from_url(database_url):
    database_url = normalize_database_url(database_url)
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query)
    options = {}
    if query.get("sslmode"):
        options["sslmode"] = query["sslmode"][0]
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "OPTIONS": options,
    }


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL", ""))

if DATABASE_URL:
    DATABASES = {"default": postgres_database_from_url(DATABASE_URL)}
elif os.environ.get("DB_ENGINE", "sqlite") == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("MYSQL_DATABASE", "rough_wallets"),
            "USER": os.environ.get("MYSQL_USER", "root"),
            "PASSWORD": os.environ.get("MYSQL_PASSWORD", ""),
            "HOST": os.environ.get("MYSQL_HOST", "127.0.0.1"),
            "PORT": os.environ.get("MYSQL_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PAYMENT_RECEIVER_ADDRESS = os.environ.get(
    "PAYMENT_RECEIVER_ADDRESS",
    "0x6B3A21807fEE4f04E525DaEBcc0ceC0fCbc3bf91",
)
CHAIN_ID = int(os.environ.get("CHAIN_ID", "1"))
RPC_URL = os.environ.get("RPC_URL", "")
if CHAIN_ID == 1 and "sepolia.infura.io" in RPC_URL:
    RPC_URL = RPC_URL.replace("sepolia.infura.io", "mainnet.infura.io")
CONFIRMATION_BLOCKS = int(os.environ.get("CONFIRMATION_BLOCKS", "1"))
PAYMENT_ASSET = os.environ.get("PAYMENT_ASSET", "ERC20").upper()
PAYMENT_TOKEN_ADDRESS = os.environ.get("PAYMENT_TOKEN_ADDRESS", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
PAYMENT_TOKEN_SYMBOL = os.environ.get("PAYMENT_TOKEN_SYMBOL", "WETH")
PAYMENT_TOKEN_DECIMALS = int(os.environ.get("PAYMENT_TOKEN_DECIMALS", "18"))

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
FOOTBALL_PROVIDER = os.environ.get("FOOTBALL_PROVIDER", "football-data").lower()
FOOTBALL_API_BASE = os.environ.get("FOOTBALL_API_BASE", "https://v3.football.api-sports.io")
FOOTBALL_API_LEAGUE_ID = int(os.environ.get("FOOTBALL_API_LEAGUE_ID", "1"))
FOOTBALL_API_SEASON = int(os.environ.get("FOOTBALL_API_SEASON", "2026"))
FOOTBALL_API_TIMEOUT = int(os.environ.get("FOOTBALL_API_TIMEOUT", "8"))
FOOTBALL_DATA_BASE = os.environ.get("FOOTBALL_DATA_BASE", "https://api.football-data.org/v4")
FOOTBALL_DATA_COMPETITION = os.environ.get("FOOTBALL_DATA_COMPETITION", "WC")


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            from django.http import HttpResponse

            response = HttpResponse()
        else:
            response = self.get_response(request)

        origin = request.headers.get("Origin", "*")
        response["Access-Control-Allow-Origin"] = origin
        response["Vary"] = "Origin"
        response["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type,X-CSRFToken"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
