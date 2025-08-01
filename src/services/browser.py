from playwright.sync_api import sync_playwright, Page, Browser
import os
from pathlib import Path

class BrowserService:
    def __init__(self, headless: bool = False, slow_mo: int = 1000):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Browser | None = None
        self.page: Page | None = None
        self.playwright = None
        
        # Set Playwright cache directory to be inside venv
        venv_path = os.environ.get('VIRTUAL_ENV', os.path.join(os.path.dirname(__file__), '../../envs', 'jobAuto'))
        self.cache_dir = os.path.join(venv_path, 'playwright-cache')
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = self.cache_dir

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )
        self.page = self.browser.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def goto(self, url: str):
        """Navigate to a URL"""
        self.page.goto(url)
        self.page.wait_for_selector('form', timeout=30000)

    def get_page(self) -> Page:
        """Get the current page object"""
        if not self.page:
            raise RuntimeError("Page not initialized")
        return self.page 