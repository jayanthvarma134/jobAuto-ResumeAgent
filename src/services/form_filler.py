import json
import re
from typing import Dict, Any, List, Union, Optional
from playwright.sync_api import Page, ElementHandle
from models.form import FormElement
from utils.constants import TIMEOUTS
from services.twocaptcha_handler import TwoCaptchaHandler

class FormFiller:
    """Service for mapping form fields to resume data and filling forms"""
    
    def __init__(self, page: Page, resume_data_path: str = "src/data/resume_data.json"):
        self.page = page
        with open(resume_data_path) as f:
            self.resume_data = json.load(f)
            
        # Common field mappings
        self.field_mappings = {
            # Basic info
            "name": ["personal_info", "name", "full_name"],
            "first_name": ["personal_info", "name", "first_name"],
            "last_name": ["personal_info", "name", "last_name"],
            "email": ["personal_info", "contact", "email"],
            "phone": ["personal_info", "contact", "phone"],
            "location": ["personal_info", "contact", "location"],
            "company": ["personal_info", "current_company"],
            "resume": ["personal_info", "resume", "file_path"],
            
            # Links
            "linkedin": ["personal_info", "links", "linkedin"],
            "github": ["personal_info", "links", "github"],
            "portfolio": ["personal_info", "links", "portfolio"],
            "twitter": ["personal_info", "links", "twitter"],
            
            # Additional info
            "pronouns": ["personal_info", "pronouns"],
            "gender": ["additional_info", "eeo_info", "gender"],
            "race": ["additional_info", "eeo_info", "race"],
            "veteran": ["additional_info", "eeo_info", "veteran_status"],
            "age range": ["additional_info", "eeo_info", "age_range"],
            "ethnicity": ["additional_info", "eeo_info", "race"],
            "relocation": ["application_responses", "location_preferences", "willing_to_relocate"],
            "mile radius": ["application_responses", "location_preferences", "willing_to_relocate"],
            "work on-site": ["application_responses", "location_preferences", "willing_to_relocate"]
        }
    
    def fill_form(self, form_elements: List[FormElement], captcha_handler: Optional[TwoCaptchaHandler] = None) -> None:
        """Fill form fields with resume data"""
        unfilled_fields = []
        
        for elem in form_elements:
            print(f"Processing field: {elem.label} ({elem.type_of_input})")

            # Skip if no label
            if not elem.label:
                print(f"Skipping field: no label")
                continue

            #Skip if current location field since it triggers a captcha
            # if "location" in elem.label.lower() and elem.type_of_input in ["text", "textarea"]:
            #     print(f"Skipping location text field: {elem.label}")
            #     continue
                
            value = self._find_matching_data(elem)
            if not value:
                print(f"No matching data found for: {elem.label}")
                unfilled_fields.append(elem.label)
                continue
                
            try:
                # If this is the location field, print captcha state before filling
                if "location" in elem.label.lower() and elem.type_of_input in ["text", "textarea"]:
                    if captcha_handler:
                        print("\nCapturing state before location field...")
                        captcha_handler.print_captcha_state(self.page, "Before location field")
                
                self._fill_field(elem, value)
                print(f"Filled {elem.label} with: {value}")
                # Add delay after filling each field
                self.page.wait_for_timeout(TIMEOUTS['interaction'])
                
                # Check for captcha after field interaction
                if captcha_handler:
                    print("\nChecking for hCaptcha after field fill...")
                    hcaptcha = TwoCaptchaHandler.detect_hcaptcha(self.page)
                    if hcaptcha["found"]:
                        print("hCaptcha detected, attempting to solve...")
                        print("\nCapturing state when captcha becomes active...")
                        captcha_handler.print_captcha_state(self.page, "Captcha active")
                        
                        # Uncomment and use automatic solution
                        # import pdb; pdb.set_trace()
                        # if captcha_handler.solve_hcaptcha(self.page, hcaptcha):
                        #     print("hCaptcha solved successfully")
                        #     # Add extra delay after solving captcha
                        #     self.page.wait_for_timeout(TIMEOUTS['interaction'])
                        #     print("\nCapturing state after captcha solved...")
                        #     captcha_handler.print_captcha_state(self.page, "After captcha solved")
                        # else:
                            # print("Failed to solve hCaptcha")
                        
                        # Comment out manual solution
                        # """
                        print("\nPlease solve the captcha manually...")
                        print("After solving, press Enter to capture the state...")
                        input()
                        # ... rest of manual monitoring code ...
                        # """                        
                        # 1. Get the visible enclave iframe we already detected
                        print("\nInvisible Checkbox Iframe:")
                        try:
                            # Get the frame using the URL from detect_hcaptcha
                            frame = self.page.frame(url=hcaptcha['src'])
                            if frame:
                                # Look for checkbox-invisible inside this frame
                                checkbox_info = frame.evaluate('''() => {
                                    const iframe = document.querySelector('iframe[src*="checkbox-invisible"]');
                                    if (!iframe) return null;
                                    return {
                                        src: iframe.src,
                                        widgetId: iframe.getAttribute('data-hcaptcha-widget-id'),
                                        response: iframe.getAttribute('data-hcaptcha-response'),
                                        display: window.getComputedStyle(iframe).display,
                                        visibility: window.getComputedStyle(iframe).visibility,
                                        attributes: Object.entries(iframe.attributes).reduce((acc, [_, attr]) => {
                                            acc[attr.name] = attr.value;
                                            return acc;
                                        }, {})
                                    };
                                }''')
                                
                                if checkbox_info:
                                    print(f"  Source: {checkbox_info.get('src', 'Not found')}")
                                    print(f"  Widget ID: {checkbox_info.get('widgetId', 'None')}")
                                    print(f"  Response Present: {'Yes' if checkbox_info.get('response') else 'No'}")
                                    if checkbox_info.get('response'):
                                        print(f"  Response Value: {checkbox_info['response']}")
                                    print(f"  Display: {checkbox_info.get('display', 'Not found')}")
                                    print(f"  Visibility: {checkbox_info.get('visibility', 'Not found')}")
                                    print(f"  All Attributes: {checkbox_info.get('attributes', {})}")
                                else:
                                    print("  No checkbox-invisible iframe found in frame")
                            else:
                                print("  Could not access detected frame")
                        except Exception as e:
                            print(f"  Error: {str(e)}")
                            print("  Not found!")
                        
                        # 2. Check enclave iframes
                        enclave_iframes = self.page.query_selector_all('iframe[src*="hcaptcha-enclave"]')
                        for idx, iframe in enumerate(enclave_iframes, 1):
                            print(f"\nEnclave Iframe {idx}:")
                            print(f"  Source: {iframe.get_attribute('src')}")
                            print(f"  Widget ID: {iframe.get_attribute('data-hcaptcha-widget-id')}")
                            print(f"  Response Present: {'Yes' if iframe.get_attribute('data-hcaptcha-response') else 'No'}")
                            print(f"  Display: {iframe.evaluate('node => window.getComputedStyle(node).display')}")
                            print(f"  Visibility: {iframe.evaluate('node => window.getComputedStyle(node).visibility')}")
                            print(f"  Parent: {iframe.evaluate('node => node.parentElement.tagName')}")
                        
                        # 3. Check response input field
                        response_input = self.page.query_selector('textarea[name="h-captcha-response"]')
                        if response_input:
                            print("\nResponse Input Field:")
                            value = response_input.evaluate('node => node.value')
                            print(f"  Value Present: {'Yes' if value else 'No'}")
                            if value:
                                print(f"  Value: {value}")
                            print(f"  Parent Element: {response_input.evaluate('node => node.parentElement.tagName')}")
                            print(f"  Is Visible: {response_input.is_visible()}")
                        
                        print("\nVerifying form continuation...")
                        # Check if form continues processing
                        try:
                            next_field = self.page.query_selector('input:focus, textarea:focus, select:focus')
                            if next_field:
                                print(f"Form is continuing - Found focused field: {next_field.get_attribute('name')}")
                        except Exception as e:
                            print("Could not verify form continuation")
            
            except Exception as e:
                print(f"Error filling {elem.label}: {e}")
                unfilled_fields.append(elem.label)
        
        if unfilled_fields:
            print("\nThe following fields need attention:")
            for field in unfilled_fields:
                print(f"  - {field}")
    
    def _find_matching_data(self, elem: FormElement) -> Any:
        """Find matching resume data for a form field"""
        label = elem.label.lower()
        words = set(label.split())
        
        # Check for work authorization and visa questions first
        if self._is_work_auth_field(words):
            return self._get_work_auth_value(words, elem.options)
            
        # Check for company-specific questions
        if self._is_company_question(words):
            return self._get_company_response(words)
            
        # Check standard field mappings
        for key, path in self.field_mappings.items():
            if key in label:
                print(f"Found matching key: {key}")
                value = self._get_value_from_path(path)
                print(f"Found value: {value}")
                # Convert boolean to Yes/No for relocation questions
                if isinstance(value, bool):
                    return "Yes" if value else "No"
                return value
                
        return None
        
    def _get_value_from_path(self, path: List[str]) -> Any:
        """Get value from resume data using path"""
        value = self.resume_data
        for key in path:
            value = value.get(key, {})
        return value if value != {} else None
        
    def _is_work_auth_field(self, words: set) -> bool:
        """Check if field is asking about work authorization"""
        auth_indicators = {'authorized', 'authorization', 'legally', 'visa', 'sponsorship', 'eligible', 'work'}
        return bool(words & auth_indicators)
        
    def _get_work_auth_value(self, words: set, options: Optional[List[str]] = None) -> str:
        """Get appropriate work authorization response"""
        is_citizen = self.resume_data["additional_info"]["work_authorization"] == "US Citizen"
        needs_sponsorship = self.resume_data["additional_info"]["visa_sponsorship_needed"]
        
        # If we have options, try to match them
        if options:
            if any('visa' in opt.lower() or 'sponsorship' in opt.lower() for opt in options):
                value = "Yes" if needs_sponsorship else "No"
            else:
                value = "Yes" if is_citizen else "No"
                
            # Try to find exact option match
            for opt in options:
                if value.lower() in opt.lower():
                    return opt
            return value
            
        # No options provided
        if any(w in words for w in {'visa', 'sponsorship'}):
            return "Yes" if needs_sponsorship else "No"
        return "Yes" if is_citizen else "No"
        
    def _is_company_question(self, words: set) -> bool:
        """Check if field is a company-specific question"""
        question_indicators = {'why', 'interest', 'learn', 'heard', 'about', 'role', 'what'}
        
        # For 'what' questions, ensure they're about role/company/interest
        if 'what' in words:
            return bool(words & {'role', 'company', 'interest'})
            
        return bool(words & question_indicators)
        
    def _get_company_response(self, words: set) -> str:
        """Get appropriate company-specific response"""
        if any(w in words for w in {'why', 'interest', 'role', 'what'}):
            responses = self.resume_data["application_responses"]["why_company"]
            # Try to find company name in URL
            match = re.search(r"jobs\.lever\.co/([^/]+)", self.page.url)
            if match:
                company = match.group(1).lower()
                response = responses.get(company)
                return response if response else responses.get("default")

        if any(w in words for w in {'learn', 'heard', 'about'}):
            return self.resume_data["application_responses"]["source"]
        return None
        
    def _fill_field(self, elem: FormElement, value: Any) -> None:
        """Fill a form field with the given value"""
        if not elem.id_of_input_component:
            print(f"No field ID for: {elem.label}")
            return
            
        try:
            field_type = elem.type_of_input
            field_id = elem.id_of_input_component
            
            if field_type == "file":
                self._fill_file_field(field_id, value)
            if field_type in ["text", "textarea"]:
                self._fill_text_field(field_id, value)
            elif field_type in ["dropdown", "multiselect"]:
                self._fill_dropdown(field_id, value)
            elif field_type == "radio":
                self._fill_radio(field_id, value, elem.options)
            elif field_type == "checkbox":
                self._fill_checkbox(field_id, value, elem.options)
                
        except Exception as e:
            print(f"Error filling {elem.label}: {e}")
            raise

    def _smooth_scroll_to_element(self, element) -> None:
        """Smoothly scroll element into view"""
        try:
            # Get element's position
            box = element.bounding_box()
            if box:
                self.page.evaluate("""
                    (elementY) => {
                        const currentY = window.scrollY;
                        const offset = 150;  // Space from top
                        
                        window.scrollTo({
                            top: elementY - offset,
                            behavior: 'smooth'
                        });
                    }
                """, box['y'])
                
                # Wait for scroll to complete
                self.page.wait_for_timeout(TIMEOUTS['interaction'])
        except Exception as e:
            print(f"Scroll error: {e}")

    def _fill_text_field(self, field_id: str, value: str) -> None:
        """Fill a text or textarea field"""
        selectors = [
            f"input[name='{field_id}']",
            f"textarea[name='{field_id}']",
            f"#{field_id}",
            f"[data-qa='{field_id}']"
        ]
        for selector in selectors:
            try:
                element = self.page.wait_for_selector(selector, 
                                                    timeout=TIMEOUTS['element'],
                                                    state='visible')
                if element:
                    # Smooth scroll to element
                    self._smooth_scroll_to_element(element)
                    element.click()
                    element.fill("")
                    
                    # # Type value with human-like delays
                    # words = str(value).split()
                    # for i, word in enumerate(words):
                    #     # Type word as a chunk for speed
                    #     element.type(word, delay=1)
                    #     # Add space between words with shorter pause

                    element.type(str(value))
                    self.page.wait_for_timeout(TIMEOUTS['interaction'])
                    break
            except Exception as e:
                print(f"Failed with selector {selector}: {e}")
                continue

    def _fill_dropdown(self, field_id: str, value: Any) -> None:
        """Fill a dropdown or multiselect field"""
        if isinstance(value, list):
            value = value[0]  # Take first value for now
        self.page.select_option(f"select[name='{field_id}']", value)

    def _fill_radio(self, field_id: str, value: Any, options: Optional[List[str]]) -> None:
        """Fill a radio button field"""
        selector = f"input[type='radio'][name='{field_id}'][value='{value}']"
        radio = self.page.wait_for_selector(selector, 
                                          timeout=TIMEOUTS['element'],
                                          state='visible')
        if radio:
            radio.check()
            self.page.wait_for_timeout(TIMEOUTS['interaction'])

    def _fill_checkbox(self, field_id: str, value: Any, options: Optional[List[str]]) -> None:
        """Fill a checkbox field"""
        print(f"\nTrying to fill checkbox with field_id: {field_id}, value: {value}")
        
        try:
            # Find all checkboxes for this field with timeout
            selector = f"input[type='checkbox'][name='{field_id}']"
            self.page.wait_for_selector(selector, timeout=TIMEOUTS['element'])  # Wait for at least one to be present
            checkboxes = self.page.query_selector_all(selector)
            
            # Convert value to lowercase for case-insensitive comparison
            target_value = str(value).lower()
            
            # Find the matching checkbox
            for checkbox in checkboxes:
                checkbox_value = (checkbox.get_attribute('value') or '').lower()
                if target_value in checkbox_value or checkbox_value in target_value:
                    if not checkbox.is_checked():
                        checkbox.check()
                    return
                    
            print(f"No matching checkbox found for value: {value}")
            
        except Exception as e:
            print(f"Error finding/filling checkbox: {e}") 

    def _fill_file_field(self, field_id: str, value: Any) -> None:
        """Handle file upload for resume"""
        try:
            # Use input[type="file"] selector
            file_input = self.page.wait_for_selector(
                f'input[type="file"][name="{field_id}"]',
                timeout=TIMEOUTS['element']
            )
            if file_input:
                file_input.set_input_files(value)
                self.page.wait_for_timeout(TIMEOUTS['resume_upload'])
        except Exception as e:
            print(f"Error uploading file: {e}")