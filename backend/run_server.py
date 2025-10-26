import sys
import os

# Add the current directory and venv to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
venv_packages = os.path.join(current_dir, '..', '.venv', 'Lib', 'site-packages')

# Insert paths at the beginning to take priority
sys.path.insert(0, current_dir)
sys.path.insert(0, venv_packages)

# Try to import fastapi to check if paths are set correctly
try:
    import fastapi
    print("FastAPI imported successfully from venv")
except ImportError as e:
    print(f"Failed to import FastAPI from venv: {e}")
    # Try to import from user site packages as fallback
    user_site_packages = r'C:\Users\28386\AppData\Roaming\Python\Python313\site-packages'
    sys.path.insert(0, user_site_packages)
    try:
        import fastapi
        print("FastAPI imported from user site-packages")
    except ImportError as e:
        print(f"Failed to import FastAPI from user site-packages: {e}")

# Now we can import fastapi and other modules
from src.api.app import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)  # Changed to port 8004