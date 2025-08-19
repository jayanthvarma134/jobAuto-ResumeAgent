import json
from datetime import datetime
from services.browser import BrowserService
from services.form_scraper import FormScraper
from services.form_filler import FormFiller
from services.form_submitter import FormSubmitter
from services.twocaptcha_handler import TwoCaptchaHandler
from pathlib import Path
from utils.constants import TIMEOUTS

# Test URLs
URLS = [
    ("https://jobs.lever.co/voltus/e6e12da1-116e-4fa9-bb36-a6d224aaee4f/apply", "voltus"),
    ("https://jobs.lever.co/Regentcraft/f8597117-3d67-4989-944a-c89fd4f756ac/apply", "regentcraft")
]

# Captcha solver API key
CAPTCHA_API_KEY = "<your api key>"

def main():
    """Main entry point for the scraper"""
    try:
        # Initialize captcha handler
        captcha_handler = TwoCaptchaHandler(CAPTCHA_API_KEY)
        
        with BrowserService(headless=False, slow_mo=1000) as browser:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            for url, name in URLS:
                try:
                    print(f"\nProcessing {name}...")
                    print("Navigating to URL...")
                    browser.goto(url)
                    
                    # Extract form elements
                    print("Scraping form elements...")
                    scraper = FormScraper(browser.get_page())
                    form_elements = scraper.scrape_form()
                    
                    # Save form structure
                    output = {
                        "url": url,
                        "timestamp": datetime.now().isoformat(),
                        "elements": [elem.to_dict() for elem in form_elements]
                    }
                    
                    output_path = output_dir / f"{name}-form.json"
                    with open(output_path, "w") as f:
                        json.dump(output, f, indent=2)
                    print(f"Found {len(form_elements)} elements")
                    
                    # Fill the form
                    print("\nFilling form fields...")
                    filler = FormFiller(browser.get_page())
                    filler.fill_form(form_elements, captcha_handler=captcha_handler)
                    
                    # Submit the form
                    print("\nSubmitting form...")
                    submitter = FormSubmitter(browser.get_page())
                    if submitter.submit_form(captcha_handler=captcha_handler):
                        print("Form submitted successfully")
                        print("\nWaiting for submission to complete...")
                        browser.get_page().wait_for_timeout(TIMEOUTS['navigation'])
                        print("Moving to next form...")
                    
                except Exception as e:
                    print(f"Error processing {name}: {e}")
                    browser.get_page().wait_for_timeout(TIMEOUTS['navigation'])  # 1 minute wait

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 