import os
import subprocess
from pathlib import Path

def install_browsers():
    """Install Playwright browsers to custom cache directory"""
    venv_path = os.environ.get('VIRTUAL_ENV', os.path.join(os.path.dirname(__file__), '../../envs', 'jobAuto'))
    cache_dir = os.path.join(venv_path, 'playwright-cache')
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = cache_dir
    print(f"Installing browsers to: {cache_dir}")
    subprocess.run(['playwright', 'install', 'chromium'], check=True)
    subprocess.run(['playwright', 'install', 'firefox'], check=True)

if __name__ == "__main__":
    install_browsers()