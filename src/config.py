import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/service-account.json")
MAX_UPLOAD_SIZE_MB = 10
SHEET_TAB_NAME = "MAPA DE TRANSFUS\u00c3O"
SHEET_HEADER_ROW = 10
SHEET_DATA_START_ROW = 11

# Phase 2: BASE tab configuration
BASE_TAB_NAME = "BASE"
BASE_GS_RH_RANGE = "A15:A24"
BASE_TIPOS_RANGE = "A48:A70"
BASE_RESPONSAVEIS_RANGE = "A107:A136"
BASE_DESTINOS_RANGE = "A1:A13"
BASE_REACAO_RANGE = "A29:A44"
BASE_CACHE_TTL_MINUTES = 5

# Phase 3: SQLite
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/historico.db")

# Phase 3: SMTP (alertas por email)
SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")

# Phase 3: Scheduler
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
SCHEDULER_ALERT_HOUR = int(os.getenv("SCHEDULER_ALERT_HOUR", "8"))
SCHEDULER_ALERT_MINUTE = int(os.getenv("SCHEDULER_ALERT_MINUTE", "0"))

# Phase 3: Cache
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

# Phase 3: Batch
MAX_BATCH_FILES = 10

# Phase 5: Sync
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))

# Phase 4: Auth
SECRET_KEY = os.getenv("SECRET_KEY", "hemominas-secret-change-in-production")
SESSION_LIFETIME_MINUTES = int(os.getenv("SESSION_LIFETIME_MINUTES", "480"))
