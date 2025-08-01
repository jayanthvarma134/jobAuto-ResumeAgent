from typing import List, Optional, TypedDict
from dataclasses import dataclass

@dataclass
class FormElement:
    label: str
    id_of_input_component: str
    required: bool
    type_of_input: str
    options: Optional[List[str]] = None
    user_data_select_values: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        return {
            "label": self.label,
            "id_of_input_component": self.id_of_input_component,
            "required": self.required,
            "type_of_input": self.type_of_input,
            "options": self.options,
            "user_data_select_values": self.user_data_select_values
        }

class ScrapedForm(TypedDict):
    url: str
    timestamp: str
    elements: List[FormElement]