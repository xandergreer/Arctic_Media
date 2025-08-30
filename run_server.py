# run_server.py
import uvicorn
import asyncio
import os
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
                ssl_enabled = config.get("ssl_enabled", False)
                ssl_cert_file = config.get("ssl_cert_file", "")
                ssl_key_file = config.get("ssl_key_file", "")
                
                # Validate host - must be IP address, not domain name
                if host and not host.startswith(('http://', 'https://')):
                    # Check if it's a valid IP or localhost
                    if host in ['0.0.0.0', '127.0.0.1', 'localhost'] or host.replace('.', '').isdigit():
                        return host, port, ssl_enabled, ssl_cert_file, ssl_key_file
                    else:
                        print(f"Warning: Invalid host '{host}', using default")
                        return settings.HOST, port, ssl_enabled, ssl_cert_file, ssl_key_file
                else:
                    print(f"Warning: Host '{host}' contains protocol, using default")
                    return settings.HOST, port, ssl_enabled, ssl_cert_file, ssl_key_file
            break
    except Exception as e:
        print(f"Warning: Could not load server settings from database: {e}")
        print("Using default configuration...")
    
    return settings.HOST, settings.PORT, False, "", ""

if __name__ == "__main__":
    # Get server configuration
    host, port, ssl_enabled, ssl_cert_file, ssl_key_file = asyncio.run(get_server_config())
    
    print(f"Starting Arctic Media server on {host}:{port}")
    print(f"External access: {'enabled' if host == '0.0.0.0' else 'disabled'}")
    
    if ssl_enabled and ssl_cert_file and ssl_key_file:
        # Check if SSL files exist
        if os.path.exists(ssl_cert_file) and os.path.exists(ssl_key_file):
            print(f"🔒 SSL enabled with certificate: {ssl_cert_file}")
            print(f"   Access via: https://{host}:{port}")
            
            # Prefer Hypercorn for HTTP/2 if available; fallback to Uvicorn
            try:
                from hypercorn.config import Config as HyperConfig
                from hypercorn.asyncio import serve as hyper_serve

                cfg = HyperConfig()
                cfg.bind = [f"{host}:{port}"]
                cfg.certfile = ssl_cert_file
                cfg.keyfile = ssl_key_file
                cfg.alpn_protocols = ["h2", "http/1.1"]
                cfg.keep_alive_timeout = 20
                print("[server] Using Hypercorn (HTTP/2 enabled)")
                asyncio.run(hyper_serve(app, cfg))
            except Exception as e:
                print(f"[server] Hypercorn unavailable ({e!s}); falling back to Uvicorn (HTTP/1.1)")
                # no reload, no workers; single-process is best for a desktop EXE
                uvicorn.run(
                    app, 
                    host=host, 
                    port=port, 
                    log_level="info",
                    proxy_headers=True,
                    forwarded_allow_ips="*",
                    timeout_keep_alive=20,
                    ssl_certfile=ssl_cert_file,
                    ssl_keyfile=ssl_key_file
                )
        else:
            print("⚠️  SSL files not found, falling back to HTTP")
            print(f"   Certificate file: {ssl_cert_file} - {'exists' if os.path.exists(ssl_cert_file) else 'missing'}")
            print(f"   Key file: {ssl_key_file} - {'exists' if os.path.exists(ssl_key_file) else 'missing'}")
            uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=True, forwarded_allow_ips="*", timeout_keep_alive=20)
    else:
        print(f"🌐 HTTP mode - Access via: http://{host}:{port}")
        # no reload, no workers; single-process is best for a desktop EXE
        uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=True, forwarded_allow_ips="*", timeout_keep_alive=20)
