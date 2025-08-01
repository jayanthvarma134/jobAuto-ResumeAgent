from typing import List, Dict, Any, Optional, Tuple
from playwright.sync_api import Page
from models.form import FormElement

class FormScraper:
    def __init__(self, page: Page):
        self.page = page

    def scrape_form(self) -> List[FormElement]:
        """Scrape form elements using generalized selectors"""
        elements = []
        
        # Wait for form to be present
        form = self.page.wait_for_selector('form')
        if not form:
            return elements

        # Find all application fields
        field_containers = form.query_selector_all('.application-field')
        
        for field in field_containers:
            # Get the label from the previous sibling
            label_text = field.evaluate('''field => {
                const label = field.previousElementSibling;
                return label && label.classList.contains('application-label') 
                    ? label.textContent.trim() 
                    : '';
            }''')

            # Get the input element
            input_elem = field.query_selector('input, select, textarea')
            if not input_elem:
                # Check for checkbox/radio groups
                inputs = field.query_selector_all('input[type="checkbox"], input[type="radio"]')
                if inputs:
                    field_info = self._extract_group_info(label_text, field, inputs)
                    if field_info:
                        print(f"Processing field: {field_info.label} ({field_info.type_of_input})")
                        elements.append(field_info)
                continue

            # Get input type and options
            input_type = self._get_input_type(input_elem)
            options = self._get_options(field, input_elem, input_type) if input_type in ['dropdown', 'radio', 'checkbox'] else []

            # If no label text found, try other sources
            if not label_text:
                label_text = (
                    input_elem.get_attribute('placeholder') or 
                    input_elem.get_attribute('aria-label') or 
                    input_elem.get_attribute('name') or ''
                ).strip()

            # Check if required using Unicode character, clean the label.
            is_required = '\u2731' in label_text
            clean_label = label_text.replace('\u2731', '').strip()

            # Create form element
            field_info = FormElement(
                label=clean_label,
                id_of_input_component=input_elem.get_attribute('name') or input_elem.get_attribute('id') or '',
                required=is_required,
                type_of_input=input_type,
                options=options if options else None,
                user_data_select_values=[options[0]] if options else None
            )
            
            print(f"Processing field: {field_info.label} ({field_info.type_of_input})")
            elements.append(field_info)

        return elements

    def _extract_group_info(self, label_text: str, container, inputs) -> Optional[FormElement]:
        """Extract information from a group of inputs"""
        if not inputs:
            return None

        # Determine if it's a checkbox or radio group
        input_type = inputs[0].get_attribute('type')
        is_multiselect = input_type == 'checkbox'

        # Get all options
        options = []
        for inp in inputs:
            option_label = inp.evaluate('''input => {
                const label = input.labels[0];
                return label ? label.textContent.trim() : '';
            }''')
            if option_label:
                options.append(option_label)

        if not options:
            return None

        return FormElement(
            label=label_text,
            id_of_input_component=inputs[0].get_attribute('name') or '',
            required='*' in label_text,
            type_of_input='multiselect' if is_multiselect else 'radio',
            options=options,
            user_data_select_values=[options[0]]
        )

    def _get_input_type(self, input_elem) -> str:
        """Get standardized input type"""
        tag_name = input_elem.evaluate('el => el.tagName.toLowerCase()')
        
        if tag_name == 'textarea':
            return 'textarea'
        elif tag_name == 'select':
            multiple = input_elem.get_attribute('multiple') == 'true'
            return 'multiselect' if multiple else 'dropdown'
        elif tag_name == 'input':
            html_type = input_elem.get_attribute('type') or 'text'
            if html_type in ['checkbox', 'radio', 'file', 'date']:
                return html_type
            return 'text'
        return 'text'

    def _get_options(self, container, input_elem, input_type) -> List[str]:
        """Get options for select/radio/checkbox fields"""
        if input_type in ['dropdown', 'multiselect']:
            return input_elem.evaluate('''
                el => Array.from(el.options)
                    .map(opt => opt.textContent.trim())
                    .filter(text => text)
            ''')
        elif input_type in ['radio', 'checkbox']:
            name = input_elem.get_attribute('name')
            if name:
                options = []
                inputs = container.query_selector_all(f'input[name="{name}"]')
                for inp in inputs:
                    label = inp.evaluate('el => el.labels[0]?.textContent.trim()')
                    if label:
                        options.append(label)
                return options
        return [] 