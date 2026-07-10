"""
INDB v2.0 - Main FastAPI Application Entry Point

Restructured with modular architecture and Application Factory pattern.
"""
import uvicorn
from core.app_factory import create_app
from core.config import config

# Create Application Instance via Factory
app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 INDB v2.0 'Kruiskade Refactored' - Starting Server")
    print("✨ Standardized API v2: ACTIVE")
    print("=" * 70)
    print(f"📡 Host: {config.HTTP_HOST}")
    print(f"🔌 Port: {config.HTTP_PORT}")
    print("=" * 70)
    
    # Use centralized configuration
    uvicorn.run(app, host=config.HTTP_HOST, port=config.HTTP_PORT)
