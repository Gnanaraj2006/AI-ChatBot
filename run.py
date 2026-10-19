import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", settings.HOST)

    print("=" * 60)
    print(f"  Starting {settings.APP_NAME}")
    print(f"  Local Access: http://localhost:{port}")
    print(f"  Active Provider: {settings.DEFAULT_MODEL_PROVIDER}")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=(settings.APP_ENV == "development")
    )
