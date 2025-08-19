from playwright.sync_api import Page
from utils.constants import TIMEOUTS
from services.twocaptcha_handler import TwoCaptchaHandler
from typing import Optional

class FormSubmitter:
    """Service for handling form submission"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def submit_form(self, captcha_handler: Optional[TwoCaptchaHandler] = None) -> bool:
        """Submit the form by finding and clicking the submit button"""
        try:
            # Scroll to bottom of page
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            self.page.wait_for_timeout(TIMEOUTS['interaction'])  # Wait for scroll to complete
            # import pdb; pdb.set_trace()
            
            # Try different submit button selectors
            selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Apply")',
                'input[value="Apply"]'
            ]
            
            # Try each selector
            submit_button = None
            for selector in selectors:
                print(f"Trying selector: {selector}")   
                try:
                    # import pdb; pdb.set_trace()
                    # Wait for button to be visible and enabled
                    submit_button = self.page.wait_for_selector(
                        selector,
                        timeout=TIMEOUTS['element'],
                        state="visible"
                    )
                    
                    if submit_button and submit_button.is_enabled():
                        print(f"Found submit button with selector: {selector}")
                        break
                except:
                    print(f"Selector failed: {selector}")
                    continue
            
            if not submit_button:
                print("Submit button not found!")
                return False

            # First submit attempt
            submit_button.click()
            print("First submit attempt...")
            self.page.wait_for_timeout(TIMEOUTS['interaction'])
            # Check for hCaptcha
            if captcha_handler:
                hcaptcha = CaptchaHandler.detect_hcaptcha(self.page)
                if hcaptcha["found"]:
                    print("hCaptcha detected, attempting to solve...")
                    if captcha_handler.solve_hcaptcha(self.page, hcaptcha):
                        print("hCaptcha solved successfully")
                        # Add extra delay after solving captcha
                        self.page.wait_for_timeout(TIMEOUTS['interaction'])
                        submit_button.click()
                        print("Second submit attempt after captcha...")
                        self.page.wait_for_timeout(TIMEOUTS['interaction'])
                    else:
                        print("Failed to solve hCaptcha")
            
            return True
            
        except Exception as e:
            print(f"Error submitting form: {e}")
            return False 