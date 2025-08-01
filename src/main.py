import json
from datetime import datetime
from services.browser import BrowserService
from services.form_scraper import FormScraper
from pathlib import Path

# Test URLs
URLS = [
    ("https://jobs.lever.co/voltus/e6e12da1-116e-4fa9-bb36-a6d224aaee4f/apply", "voltus"),
    ("https://jobs.lever.co/Regentcraft/f8597117-3d67-4989-944a-c89fd4f756ac/apply", "regentcraft")
]

def main():
    """Main entry point for the scraper"""
    try:
        with BrowserService(headless=False, slow_mo=100) as browser:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            for url, name in URLS:
                try:
                    print(f"\nScraping {name}...")
                    browser.goto(url)
                    
                    scraper = FormScraper(browser.get_page())
                    form_elements = scraper.scrape_form()
                    
                    output = {
                        "url": url,
                        "timestamp": datetime.now().isoformat(),
                        "elements": [elem.to_dict() for elem in form_elements]
                    }
                    
                    output_path = output_dir / f"{name}-form.json"
                    with open(output_path, "w") as f:
                        json.dump(output, f, indent=2)
                    
                    print(f"Found {len(form_elements)} elements")
                    
                except Exception as e:
                    print(f"Error scraping {name}: {e}")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 