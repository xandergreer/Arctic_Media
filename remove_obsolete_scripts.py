#!/usr/bin/env python3
"""
Remove obsolete Python scripts from Arctic Media project
"""

import os
import shutil
from pathlib import Path

def remove_obsolete_scripts():
    """Remove scripts that are no longer needed"""
    project_root = Path(__file__).parent

    # Scripts to remove (obsolete or redundant)
    obsolete_scripts = [
        'check_domain_settings.py',  # Domain-specific, not generally useful
        'domain_test.py',            # Domain testing, specific use case
        'fix_dist_db.py',           # Database fix for specific issue
        'fix_dist_db_8096.py',      # Database fix for specific issue
        'fix_port_80.py',           # Port-specific fix
        'reset_dist_db.py',         # Database reset (dangerous)
        'test_login.py',            # Login test with hardcoded IPs
        'test_remote_settings.py',  # Remote settings test
    ]

    removed_scripts = []

    print("🗑️  Removing Obsolete Scripts")
    print("=" * 40)

    for script in obsolete_scripts:
        script_path = project_root / script
        if script_path.exists():
            try:
                # Get file size
                size = os.path.getsize(script_path) / 1024  # KB
                script_path.unlink()
                removed_scripts.append(f"{script} ({size:.1f} KB)")
                print(f"✅ Removed {script}")
            except Exception as e:
                print(f"❌ Could not remove {script}: {e}")

    print(f"\n📊 Summary: {len(removed_scripts)} obsolete scripts removed")

    if removed_scripts:
        print("\n📋 Removed scripts:")
        for script in removed_scripts:
            print(f"   • {script}")

    # Show remaining useful scripts
    remaining_scripts = [
        'run_server.py',           # ✅ Main server startup
        'add_search_indexes.py',    # ✅ Database optimization
        'cleanup_project.py',       # ✅ Project maintenance
        'check_auth.py',           # ✅ Authentication troubleshooting
        'configure_ssl.py',        # ✅ SSL setup
        'fix_admin_user.py',       # ✅ Admin user fixes
        'troubleshoot_http.py',    # ✅ Network/server issues
        'test_config.py',          # ✅ Configuration verification
    ]

    print("\n📋 Useful scripts to keep:")
    for script in remaining_scripts:
        print(f"   • {script}")

    print("\n💡 Tip: You can always recreate any removed script if needed from git history")
    if removed_scripts:
        print(f"\n💾 Space saved: ~{sum(float(s.split('(')[1].split(' ')[0]) for s in removed_scripts):.1f} KB")

if __name__ == "__main__":
    remove_obsolete_scripts()
