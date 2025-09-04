#!/usr/bin/env python3
"""
Cleanup script for Arctic Media project
Removes unnecessary files and directories to reduce project bloat
"""

import os
import shutil
import glob
from pathlib import Path

def get_folder_size(folder_path):
    """Get folder size in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError):
                pass
    return total_size / (1024 * 1024)  # Convert to MB

def cleanup_project():
    """Clean up unnecessary files and directories"""
    project_root = Path(__file__).parent
    cleaned_items = []
    total_space_saved = 0

    print("🧹 Arctic Media Project Cleanup")
    print("=" * 50)

    # 1. Remove virtual environments
    venv_patterns = ['.venv', 'venv', 'env', 'ENV']
    for pattern in venv_patterns:
        for venv_path in project_root.rglob(pattern):
            if venv_path.is_dir():
                size = get_folder_size(str(venv_path))
                try:
                    shutil.rmtree(venv_path)
                    cleaned_items.append(f"Removed {venv_path.name} ({size:.1f} MB)")
                    total_space_saved += size
                except Exception as e:
                    print(f"❌ Could not remove {venv_path}: {e}")

    # 2. Remove build artifacts
    build_dirs = ['build', 'dist']
    for build_dir in build_dirs:
        build_path = project_root / build_dir
        if build_path.exists():
            size = get_folder_size(str(build_path))
            try:
                shutil.rmtree(build_path)
                cleaned_items.append(f"Removed {build_dir}/ ({size:.1f} MB)")
                total_space_saved += size
            except Exception as e:
                print(f"❌ Could not remove {build_path}: {e}")

    # 3. Remove Python cache
    for pycache in project_root.rglob('__pycache__'):
        if pycache.is_dir():
            try:
                shutil.rmtree(pycache)
                cleaned_items.append(f"Removed {pycache.relative_to(project_root)}/")
            except Exception as e:
                print(f"❌ Could not remove {pycache}: {e}")

    # 4. Remove spec files
    for spec_file in project_root.glob('*.spec'):
        try:
            size = os.path.getsize(spec_file) / (1024 * 1024)
            spec_file.unlink()
            cleaned_items.append(f"Removed {spec_file.name} ({size:.3f} MB)")
            total_space_saved += size
        except Exception as e:
            print(f"❌ Could not remove {spec_file}: {e}")

    # 5. Remove empty directories
    for dir_path in list(project_root.rglob('*')):
        if dir_path.is_dir() and not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
                cleaned_items.append(f"Removed empty directory {dir_path.relative_to(project_root)}/")
            except Exception:
                pass

    # 6. Remove duplicate/unnecessary scripts
    scripts_to_check = [
        'fix_emby_conflict.py',
        'check_auth.py',
        'test_config.py',
        'check_domain_settings.py',
        'check_server_settings.py',
        'configure_ssl.py',
        'diagnose_emby_conflict.py',
        'domain_test.py',
        'fix_admin_user.py',
        'fix_dist_db.py',
        'fix_dist_db_8096.py',
        'fix_lan_redirect.py',
        'fix_port_80.py',
        'reset_dist_db.py',
        'test_login.py',
        'test_remote_settings.py',
        'troubleshoot_http.py'
    ]

    for script in scripts_to_check:
        script_path = project_root / script
        if script_path.exists():
            # Check if file is empty or very small
            try:
                size = os.path.getsize(script_path)
                if size < 100:  # Less than 100 bytes (likely empty or minimal)
                    script_path.unlink()
                    cleaned_items.append(f"Removed empty/minimal script {script}")
                elif script.endswith(('.pyc', '.pyo')):
                    script_path.unlink()
                    cleaned_items.append(f"Removed compiled Python file {script}")
            except Exception as e:
                print(f"❌ Could not check {script}: {e}")

    # Print results
    print(f"\n✅ Cleanup completed! {len(cleaned_items)} items removed")
    print(f"   Total space saved: ~{total_space_saved:.1f} MB")
    print("\n📋 Items removed:")

    for item in cleaned_items[:20]:  # Show first 20 items
        print(f"   • {item}")

    if len(cleaned_items) > 20:
        print(f"   ... and {len(cleaned_items) - 20} more items")

    print("\n💡 Recommendations:")
    print("   • Run 'git add .' then 'git status' to see what files are now untracked")
    print("   • Consider committing the .gitignore file to prevent future bloat")
    print("   • For production deployments, exclude .venv from your deployment process")
    print("   • Keep only essential troubleshooting scripts")

if __name__ == "__main__":
    cleanup_project()
