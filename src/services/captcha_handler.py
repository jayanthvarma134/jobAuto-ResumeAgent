from playwright.sync_api import Page
import time

class CaptchaHandler:
    """Handles detection and manual solving of captchas"""
    
    @staticmethod
    def detect_captcha(page: Page) -> bool:
        """Check if captcha is present and visible on the page"""
        try:
            # Check both iframe and widget visibility
            iframe = page.query_selector('iframe[src*="hcaptcha"]')
            widget = page.query_selector('div[class*="h-captcha"]')
            return bool(iframe or widget)
        except:
            return False
    
    @staticmethod
    def wait_for_manual_solve(page: Page, timeout: int = 300) -> bool:
        """Wait for manual captcha solving with timeout"""
        print("\n hCaptcha detected! Please solve it to continue...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if captcha iframe is still present
                iframe = page.query_selector('iframe[src*="hcaptcha"]')
                if not iframe:
                    # Double check with a small delay to ensure it's really gone
                    time.sleep(1)
                    if not page.query_selector('iframe[src*="hcaptcha"]'):
                        print("✓ Captcha solved!")
                        return True
            except:
                pass
            time.sleep(0.5)  # Check every 500ms
            
        print(" Captcha solving timeout reached!")
        return False 