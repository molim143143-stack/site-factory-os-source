from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
LOG_DIR = BASE_DIR / "logs"
GENERATED_DIR = BASE_DIR / "generated_sites"
DB_PATH = STORAGE_DIR / "site_factory_os.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

APP_VERSION = "0.1.0"
MOCK_NS = ("ns1.cloudflare-mock.com", "ns2.cloudflare-mock.com")

for directory in (STORAGE_DIR, LOG_DIR, GENERATED_DIR):
    directory.mkdir(parents=True, exist_ok=True)
