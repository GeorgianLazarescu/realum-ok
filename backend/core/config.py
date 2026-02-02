import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# JWT Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'realum-secret-key-2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Token Economy Configuration
TOKEN_BURN_RATE = 0.02  # 2% of transactions get burned
INITIAL_BALANCE = 1000.0
