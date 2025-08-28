# run_server.py
import uvicorn
import asyncio
from app.main import app
from app.config import settings
from app.database import init_db, get_db
from app.models import ServerSetting
from sqlalchemy import select

async def get_server_config():
    """Get server configuration from database or use defaults"""
    try:
        await init_db()
        async for db in get_db():
            # Get server settings from database
            server_settings = (await db.execute(
                select(ServerSetting).where(ServerSetting.key == "server")
            )).scalars().first()
            
            if server_settings and server_settings.value:
                config = server_settings.value
                host = config.get("server_host", settings.HOST)
                port = config.get("server_port", settings.PORT)
                return host, port
            break
    except Exception as e:
        print(f"Warning: Could not load server settings from database: {e}")
        print("Using default configuration...")
    
    return settings.HOST, settings.PORT

if __name__ == "__main__":
    # Get server configuration
    host, port = asyncio.run(get_server_config())
    
    print(f"Starting Arctic Media server on {host}:{port}")
    print(f"External access: {'enabled' if host == '0.0.0.0' else 'disabled'}")
    
    # no reload, no workers; single-process is best for a desktop EXE
    uvicorn.run(app, host=host, port=port, log_level="info")
