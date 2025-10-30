import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_TOKENS = 1000
TEMPERATURE = 0.7

# Persistence
VECTOR_STORE_DIR = "data"
VECTOR_STORE_NAME = "mosdac_vs"

# Streamlit configuration
PAGE_TITLE = "MOSDAC SIMPLIFIED"
PAGE_ICON = "🤖"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"
# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Set it in your .env file.")
