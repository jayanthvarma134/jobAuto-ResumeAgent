from playwright.sync_api import Page
from utils.constants import TIMEOUTS

class FormSubmitter:
    """Service for handling form submission"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def submit_form(self) -> bool:
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
                        submit_button.click()
                        return True
                except:
                    print(f"Selector failed: {selector}")
                    continue
            
            print("Submit button not found!")
            return False
            
        except Exception as e:
            print(f"Error submitting form: {e}")
            return False 