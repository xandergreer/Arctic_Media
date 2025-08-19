# run_server.py
import uvicorn
from app.main import app

if __name__ == "__main__":
    # no reload, no workers; single-process is best for a desktop EXE
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
