from playwright.sync_api import sync_playwright, Page, Browser
import os
from pathlib import Path
from utils.constants import TIMEOUTS

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
        
        self.browser = self.playwright.firefox.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=['--start-maximized']  # Start browser maximized
        )
        
        # Get system screen size
        context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure proper cleanup of browser resources"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"Error during browser cleanup: {e}")
            # Still try to stop playwright
            if self.playwright:
                self.playwright.stop()

    def goto(self, url: str):
        """Navigate to a URL and wait for form to be ready"""
        self.page.goto(url)
        
        # Wait for form to be present and visible
        self.page.wait_for_selector('form', 
                                  timeout=TIMEOUTS['page_load'],
                                  state='visible')
        
        # Wait for interactive elements to be ready
        self.page.wait_for_selector('input, textarea, select', 
                                  timeout=TIMEOUTS['element'],
                                  state='visible')
        
        # Wait a bit for any dynamic content to load
        self.page.wait_for_timeout(TIMEOUTS['interaction'])

    def get_page(self) -> Page:
        """Get the current page object"""
        if not self.page:
            raise RuntimeError("Page not initialized")
        return self.page 