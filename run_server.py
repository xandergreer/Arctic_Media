# run_server.py
import uvicorn
import asyncio
import os
import socket
from app.main import app
from app.config import settings
from app.database import init_db, get_db
from app.models import ServerSetting
from sqlalchemy import select, insert

def _is_port_available(host: str, port: int) -> bool:
    """Check if a TCP port is available for binding on the given host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((("0.0.0.0" if host == "0.0.0.0" else host), port))
        return True
    except Exception:
        return False


def _pick_first_run_port(host: str) -> int:
    """Pick a safer default port for first run, avoiding common conflicts.

    Respects an explicit PORT environment override if it is not a commonly used port.
    Otherwise prefers settings.FIRST_RUN_PORT, then tries a small set of alternatives
    until it finds a free port.
    """
    COMMON_PORTS = {8000, 8080, 8096, 8920, 32400, 3000, 5000, 5173, 8888, 7860}

    # If user explicitly set PORT and it is not in the common/conflict set, prefer it
    env_port = os.environ.get("PORT")
    if env_port:
        try:
            p = int(env_port)
            if 1 <= p <= 65535 and p not in COMMON_PORTS and _is_port_available(host, p):
                return p
        except Exception:
            pass

    candidates = []
    # Primary candidate from settings (configurable)
    try:
        if getattr(settings, "FIRST_RUN_PORT", None):
            candidates.append(int(settings.FIRST_RUN_PORT))
    except Exception:
        pass
    # Reasonable additional fallbacks
    candidates += [8085, 8754, 8181, 8585, 8283, 8899, 8686, 8822]

    for p in candidates:
        if p not in COMMON_PORTS and 1 <= p <= 65535 and _is_port_available(host, p):
            return p

    # Last resort: let OS choose ephemeral port, though this is not ideal for UX
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((("0.0.0.0" if host == "0.0.0.0" else host), 0))
            return s.getsockname()[1]
    except Exception:
        # Fallback to configured PORT
        return int(getattr(settings, "PORT", 8085))


async def get_server_config():
    """Get server configuration from database or use defaults.

    If no server settings exist (first run), choose a safer default port to avoid
    common conflicts (e.g., 8000) and persist this choice to the database so that
    subsequent runs are stable.
    """
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
                # Fall back to env-backed SSL defaults when fields missing in DB
                ssl_enabled = config.get("ssl_enabled", bool(getattr(settings, "SSL_ENABLED", False)))
                ssl_cert_file = config.get("ssl_cert_file", getattr(settings, "SSL_CERT_FILE", ""))
                ssl_key_file = config.get("ssl_key_file", getattr(settings, "SSL_KEY_FILE", ""))
                
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
            else:
                # First run: pick a safer default port and persist it to DB
                host = settings.HOST
                port = _pick_first_run_port(host)
                try:
                    cfg = {
                        "server_host": host,
                        "server_port": int(port),
                        "external_access": host == "0.0.0.0",
                        "ssl_enabled": False,
                        "ssl_cert_file": "",
                        "ssl_key_file": "",
                    }
                    await db.execute(insert(ServerSetting).values(key="server", value=cfg))
                    await db.commit()
                except Exception:
                    # Non-fatal if we cannot persist; we still return the picked port
                    pass
                # Friendly guidance on first-time setup
                try:
                    print("\n=== Arctic Media - First-Time Setup ===")
                    print("Open your browser to:")
                    print(f"  http://127.0.0.1:{port}")
                    print("If accessing from another device on your network, use your PC's LAN IP,")
                    print(f"for example:  http://YOUR_LAN_IP:{port}")
                    print("========================================\n")
                except Exception:
                    # Printing guidance should never break startup
                    pass
                return host, port, False, "", ""
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
            print(f"SSL enabled with certificate: {ssl_cert_file}")
            print(f"   Access via: https://{host}:{port}")
            
            # Prefer Hypercorn for HTTP/2 if available; fallback to Uvicorn
            try:
                from hypercorn.config import Config as HyperConfig
                from hypercorn.asyncio import serve as hyper_serve

                cfg = HyperConfig()
                # Bind to the configured host and port
                cfg.bind = [f"{host}:{port}"]
                cfg.certfile = ssl_cert_file
                cfg.keyfile = ssl_key_file
                cfg.alpn_protocols = ["h2", "http/1.1"]
                cfg.keep_alive_timeout = 20
                cfg.graceful_timeout = 30
                cfg.ssl_handshake_timeout = 10
                print("[server] Using Hypercorn (HTTP/2 enabled)")
                try:
                    asyncio.run(hyper_serve(app, cfg))
                except Exception as ssl_error:
                    print(f"[server] SSL error in Hypercorn: {ssl_error}")
                    print("[server] Falling back to Uvicorn for SSL...")
                    # Run on both addresses for Uvicorn fallback
                    uvicorn.run(
                        app, 
                        host="0.0.0.0", 
                        port=port, 
                        log_level="info",
                        proxy_headers=True,
                        forwarded_allow_ips="*",
                        timeout_keep_alive=20,
                        ssl_certfile=ssl_cert_file,
                        ssl_keyfile=ssl_key_file
                    )
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
            print("WARNING: SSL files not found, falling back to HTTP")
            print(f"   Certificate file: {ssl_cert_file} - {'exists' if os.path.exists(ssl_cert_file) else 'missing'}")
            print(f"   Key file: {ssl_key_file} - {'exists' if os.path.exists(ssl_key_file) else 'missing'}")
            uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=True, forwarded_allow_ips="*", timeout_keep_alive=20)
    else:
        print(f"HTTP mode - Access via: http://{host}:{port}")
        # no reload, no workers; single-process is best for a desktop EXE
        uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=True, forwarded_allow_ips="*", timeout_keep_alive=20)
