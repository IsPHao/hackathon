"""Backend package initialization with environment variable loading."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    # Try to load from any .env file in the current working directory
    load_dotenv(override=True)
