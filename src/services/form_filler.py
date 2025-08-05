import json
import re
from typing import Dict, Any, List, Union, Optional
from playwright.sync_api import Page, ElementHandle
from models.form import FormElement
from services.captcha_handler import CaptchaHandler
from utils.constants import TIMEOUTS

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
    
    def fill_form(self, form_elements: List[FormElement]) -> None:
        """Fill form fields with resume data"""
        unfilled_fields = []
        
        for elem in form_elements:
            # import pdb; pdb.set_trace()
            print(f"Processing field: {elem.label} ({elem.type_of_input})")

            # Skip file fields
            if not elem.label or elem.type_of_input == "file":
                print(f"Skipping field: {elem.label}")
                continue

            #Skip if current location field since it triggers a captcha
            if "location" in elem.label.lower() and elem.type_of_input in ["text", "textarea"]:
                print(f"Skipping location text field: {elem.label}")
                continue
                
            value = self._find_matching_data(elem)
            if not value:
                print(f"No matching data found for: {elem.label}")
                unfilled_fields.append(elem.label)
                continue
                
            try:
                self._fill_field(elem, value)
                print(f"Filled {elem.label} with: {value}")
                
                # Check for captcha after each field interaction
                # if CaptchaHandler.detect_captcha(self.page):
                #     print("\n Captcha detected during form filling...")
                #     if CaptchaHandler.wait_for_manual_solve(self.page):
                #         print("Resuming form filling...")
            
                # Add delay after filling each field
                # self.page.wait_for_timeout(1000)  # 1 second delay

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
            
            if field_type in ["text", "textarea"]:
                self._fill_text_field(field_id, value)
            elif field_type in ["dropdown", "multiselect"]:
                self._fill_dropdown(field_id, value)
            elif field_type == "radio":
                self._fill_radio(field_id, value, elem.options)
            elif field_type == "checkbox":
                print("yes")
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
                # Scroll smoothly to element
                print("scrolling to element")
                self.page.evaluate("""(y) => {
                    window.scrollTo({
                        top: y - window.innerHeight/2,
                        behavior: 'smooth'
                    });
                }""", box['y'])
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