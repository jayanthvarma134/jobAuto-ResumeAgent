import requests
import time
from playwright.sync_api import Page
from typing import Optional

class TwoCaptchaHandler:
    """Handler for automated captcha solving using 2captcha API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://2captcha.com"
        
    @staticmethod
    def detect_hcaptcha(page: Page) -> dict:
        """Find and return visible hCaptcha details"""
        try:
            print("\nChecking for hCaptcha iframes...")
            
            # First get count of iframes
            iframe_count = page.evaluate("""() => {
                return document.querySelectorAll('iframe[src*="hcaptcha"]').length;
            }""")
            print(f"Found {iframe_count} hCaptcha iframes")
            
            # Get details of each iframe
            iframes_data = page.evaluate("""() => {
                const iframes = document.querySelectorAll('iframe[src*="hcaptcha"]');
                return Array.from(iframes).map(iframe => {
                    const style = window.getComputedStyle(iframe);
                    const rect = iframe.getBoundingClientRect();
                    return {
                        src: iframe.src,
                        id: iframe.id,
                        visibility: style.visibility,
                        display: style.display,
                        opacity: style.opacity,
                        width: rect.width,
                        height: rect.height
                    };
                });
            }""")
            
            # Print details of each iframe
            for idx, iframe in enumerate(iframes_data):
                print(f"\nIframe {idx + 1}:")
                print(f"  Source: {iframe['src']}")
                print(f"  ID: {iframe['id']}")
                print(f"  Visibility: {iframe['visibility']}")
                print(f"  Display: {iframe['display']}")
                print(f"  Opacity: {iframe['opacity']}")
                print(f"  Dimensions: {iframe['width']}x{iframe['height']}")
            
            # Now find the visible one
            hcaptcha = page.evaluate("""() => {
                const iframes = document.querySelectorAll('iframe[src*="hcaptcha"]');
                
                // Look for an iframe that's fully visible
                for (const iframe of iframes) {
                    const style = window.getComputedStyle(iframe);
                    const rect = iframe.getBoundingClientRect();
                    if (style.visibility === 'visible' && 
                        style.display === 'block' && 
                        style.opacity === '1' &&
                        rect.width > 0) {
                        
                        // Get the sitekey from parent div
                        const hcaptchaDiv = document.querySelector('.h-captcha');
                        return {
                            found: true,
                            sitekey: hcaptchaDiv ? hcaptchaDiv.getAttribute('data-sitekey') : null,
                            src: iframe.src
                        };
                    }
                }
                return { found: false };
            }""")
            
            if hcaptcha["found"]:
                print("\nFound visible hCaptcha:")
                print(f"  Sitekey: {hcaptcha['sitekey']}")
                print(f"  Source: {hcaptcha['src']}")
            else:
                print("\nNo visible hCaptcha found")
            
            return hcaptcha
            
        except Exception as e:
            print(f"Error checking for hCaptcha: {e}")
            return { "found": False }
            
    def _get_solution_from_2captcha(self, website_key: str, page_url: str) -> Optional[str]:
        """Get solution token from 2captcha API"""
        print(f"Solving hCaptcha with sitekey: {website_key}")
        
        # Create task
        data = {
            "key": self.api_key,
            "method": "hcaptcha",
            "sitekey": website_key,
            "pageurl": page_url,
            "json": 1
        }
        
        print("\nCreating 2captcha task with params:")
        print(f"  sitekey: {website_key}")
        print(f"  pageurl: {page_url}")
        print(f"  method: hcaptcha")
        
        # Submit task
        response = requests.post(
            f"{self.base_url}/in.php",
            params=data
        )

        print("################################## : Response")
        print(response.json())

        # import pdb; pdb.set_trace()
        
        if not response.ok:
            print(f"Error creating task: {response.text}")
            return None
        
        result = response.json()
        if result.get("status") != 1:
            print(f"Error response: {result.get('request')}")
            return None
            
        task_id = result.get("request")
        print(f"Task created with ID: {task_id}")
        
        # Get solution
        print("Waiting for solution...")
        max_attempts = 24  # Increased to 2 minutes total
        for _ in range(max_attempts):
            response = requests.get(
                f"{self.base_url}/res.php",
                params={
                    "key": self.api_key,
                    "action": "get",
                    "id": task_id,
                    "json": 1
                }
            )
            
            result = response.json()
            print(result)

            # # import pdb; pdb.set_trace()
            
            if result.get("status") == 1:
                solution = result.get("request")
                print("Got solution from 2captcha")
                print(f"Solution token: {solution}")
                print(f"Solution token length: {len(solution)}")
                return solution
            elif result.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                print("Captcha reported as unsolvable")
                return None
            elif result.get("request") == "ERROR_WRONG_USER_KEY":
                print("Invalid API key")
                return None
            elif result.get("request") == "ERROR_ZERO_BALANCE":
                print("No balance remaining")
                return None
            elif result.get("request") != "CAPCHA_NOT_READY":
                print(f"Error getting solution: {result.get('request')}")
                return None
            
            time.sleep(5)
        
        print("Timeout waiting for solution")
        return None

    def _set_response_in_checkbox(self, frame, solution: str) -> bool:
        """Set the solution in the checkbox iframe"""
        result = frame.evaluate("""(solution) => {
            try {
                // Find checkbox-invisible iframe and set response
                const checkbox = document.querySelector('iframe[src*="checkbox-invisible"]');
                if (!checkbox) {
                    return { 
                        success: false, 
                        error: 'checkbox-invisible iframe not found in frame' 
                    };
                }
                
                checkbox.setAttribute('data-hcaptcha-response', solution);
                return { 
                    success: true,
                    widgetId: checkbox.getAttribute('data-hcaptcha-widget-id'),
                    response: checkbox.getAttribute('data-hcaptcha-response')
                };
            } catch (e) {
                return { 
                    success: false, 
                    error: e.message 
                };
            }
        }""", solution)

        if not result.get('success'):
            print(f"✗ Error setting response: {result.get('error')}")
            return False

        print("✓ Response set in checkbox iframe")
        print(f"  Widget ID: {result.get('widgetId')}")
        return True

    def _set_response_in_input(self, page, solution: str) -> bool:
        """Set the solution in the hidden input field"""
        print("\nSetting response in hidden input...")
        result = page.evaluate("""(solution) => {
            try {
                const input = document.querySelector('textarea[name="h-captcha-response"]');
                if (!input) {
                    return { 
                        success: false, 
                        error: 'Response input field not found' 
                    };
                }
                input.value = solution;
                return { success: true };
            } catch (e) {
                return { 
                    success: false, 
                    error: e.message 
                };
            }
        }""", solution)

        if not result.get('success'):
            print(f"✗ Error setting input: {result.get('error')}")
            return False

        print("✓ Solution token set in hidden input")
        return True

    def _handle_button_click(self, frame) -> tuple[bool, Optional[str]]:
        """Handle button detection and clicking. Returns (success, button_type)"""
        print("\nChecking available buttons...")
        buttons = frame.evaluate("""() => {
            try {
                const nextButton = document.querySelector('button[title="Next Challenge"], button[data-cy="next-challenge"]');
                const verifyButton = document.querySelector('button[title="Verify Answers"], button[data-cy="verify-answers"]');
                # const skipButton = document.querySelector('button[title="Skip Challenge"], button[data-cy="skip-challenge"]');
                
                console.log("Button search results:", {
                    nextFound: !!nextButton,
                    verifyFound: !!verifyButton,
                    # skipFound: !!skipButton,
                    allButtons: Array.from(document.querySelectorAll('button')).map(b => ({
                        title: b.title,
                        text: b.textContent,
                        class: b.className
                    }))
                });
                
                # if (skipButton) {
                #     console.log("Found Skip button - clicking to skip challenge");
                #     skipButton.click();
                #     return { 
                #         success: true,
                #         buttonClicked: 'skip'
                #     };
                } else if (verifyButton) {
                    console.log("Found Verify button - clicking to complete");
                    verifyButton.click();
                    return { 
                        success: true,
                        buttonClicked: 'verify'
                    };
                } else if (nextButton) {
                    console.log("Found Next button - clicking to continue");
                    nextButton.click();
                    return {
                        success: true,
                        buttonClicked: 'next'
                    };
                } else {
                    // Log all buttons found for debugging
                    const allButtons = Array.from(document.querySelectorAll('button'));
                    return {
                        success: false,
                        error: 'No matching button found',
                        debug: {
                            totalButtons: allButtons.length,
                            buttonDetails: allButtons.map(b => ({
                                title: b.title,
                                text: b.textContent,
                                class: b.className
                            }))
                        }
                    };
                }
            } catch (e) {
                return { 
                    success: false, 
                    error: e.message 
                };
            }
        }""")
        
        if not buttons.get('success'):
            print(f"✗ Error with buttons: {buttons.get('error')}")
            if buttons.get('debug'):
                print("Debug info:", buttons.get('debug'))
            return False, None

        button_type = buttons.get('buttonClicked')
        if button_type == 'verify':
            print("✓ Clicked Verify button")
            return True, 'verify'
        elif button_type == 'next':
            print("✓ Clicked Next Challenge button")
            return True, 'next'
        # elif button_type == 'skip':
        #     print("✓ Clicked Skip Challenge button")
        #     return True, 'verify'  # Treat skip like verify since we're done with challenges
        else:
            print("✗ No actionable buttons found")
            return False, None

    def solve_hcaptcha(self, page: Page, hcaptcha: dict) -> bool:
        """Main method to solve hCaptcha on a page"""
        try:
            print("\nStarting hCaptcha solution process...")
            
            website_key = hcaptcha["sitekey"]
            if not website_key:
                print("Could not find hCaptcha sitekey")
                return False

            print(f"Website key: {website_key}")
            # import pdb; pdb.set_trace()
            # Get solution from 2captcha
            solution = self._get_solution_from_2captcha(website_key, page.url)
            if not solution:
                return False

            # Apply solution
            print("Applying solution...")
            
            # First find our specific iframe
            frame = page.frame(url=hcaptcha["src"])
            if not frame:
                print("Could not find the specific hCaptcha iframe")
                return False
                
            print("Found target iframe, applying solution...")

            # import pdb; pdb.set_trace()
            # Set response in checkbox iframe
            if not self._set_response_in_checkbox(frame, solution):
                return False

            # import pdb; pdb.set_trace()
            # Set response in hidden input
            if not self._set_response_in_input(page, solution):
                return False

            # Handle button clicking
            success, button_type = self._handle_button_click(frame)
            if not success:
                return False

            if button_type == 'verify':
                # Wait for enclave iframes to become hidden
                print("\nWaiting for hCaptcha to process solution...")
                page.wait_for_function("""() => {
                    // Find the initially visible iframe
                    const enclaves = document.querySelectorAll('iframe[src*="hcaptcha-enclave"]');
                    const visibleEnclave = Array.from(enclaves).find(iframe => 
                        window.getComputedStyle(iframe).visibility === 'visible'
                    );
                    
                    // If no visible iframe found, it means it became hidden
                    return !visibleEnclave;
                }""", timeout=5000)
                print("✓ hCaptcha processed solution (visible iframe became hidden)")
                return True
            else:  # button_type == 'next'
                # Wait a bit and try again
                self.page.wait_for_timeout(1000)  # Wait 1 second
                return self.solve_hcaptcha(self.page, hcaptcha)  # Recursive call
                
        except Exception as e:
            print(f"Error in solve_hcaptcha: {e}")
            return False

    def print_captcha_state(self, page: Page, message: str):
        """Print the current state of captcha elements"""
        print(f"\n=== {message} ===")
        
        # Get all hcaptcha iframes and elements
        elements = page.evaluate("""() => {
            const iframes = document.querySelectorAll('iframe[src*="hcaptcha"]');
            const responseInput = document.querySelector('#hcaptchaResponseInput');
            const hcaptchaDiv = document.querySelector('.h-captcha');
            
            return {
                iframes: Array.from(iframes).map(iframe => ({
                    src: iframe.src,
                    style: {
                        display: iframe.style.display || window.getComputedStyle(iframe).display,
                        visibility: iframe.style.visibility || window.getComputedStyle(iframe).visibility,
                        opacity: iframe.style.opacity || window.getComputedStyle(iframe).opacity
                    },
                    attributes: {
                        'data-hcaptcha-widget-id': iframe.getAttribute('data-hcaptcha-widget-id'),
                        'data-hcaptcha-response': iframe.getAttribute('data-hcaptcha-response'),
                        'aria-hidden': iframe.getAttribute('aria-hidden')
                    },
                    dataset: Object.assign({}, iframe.dataset)
                })),
                responseInput: responseInput ? {
                    value: responseInput.value,
                    attributes: {
                        name: responseInput.getAttribute('name'),
                        type: responseInput.getAttribute('type')
                    }
                } : null,
                hcaptchaDiv: hcaptchaDiv ? {
                    attributes: {
                        'class': hcaptchaDiv.getAttribute('class'),
                        'data-sitekey': hcaptchaDiv.getAttribute('data-sitekey'),
                        'data-theme': hcaptchaDiv.getAttribute('data-theme')
                    },
                    dataset: Object.assign({}, hcaptchaDiv.dataset)
                } : null
            };
        }""")
        
        print("\nHCaptcha iframes:")
        for idx, iframe in enumerate(elements['iframes']):
            print(f"\nIframe {idx + 1}:")
            print(f"  Source: {iframe['src']}")
            print(f"  Style: {iframe['style']}")
            print(f"  Attributes: {iframe['attributes']}")
            print(f"  Dataset: {iframe['dataset']}")
            
        print("\nResponse Input:")
        if elements['responseInput']:
            print(f"  Value: {elements['responseInput']['value']}")
            print(f"  Attributes: {elements['responseInput']['attributes']}")
        else:
            print("  Not found")
            
        print("\nHCaptcha Div:")
        if elements['hcaptchaDiv']:
            print(f"  Attributes: {elements['hcaptchaDiv']['attributes']}")
            print(f"  Dataset: {elements['hcaptchaDiv']['dataset']}")
        else:
            print("  Not found")
            
        print("=" * 50) 