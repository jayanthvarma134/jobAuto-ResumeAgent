# Job Application Form Scraper

A Python-based tool that scrapes job application forms from various job portals and extracts form elements in a structured format.

## Features

- Extracts form elements including:
  - Text inputs
  - Textareas
  - Dropdowns
  - Radio buttons
  - Checkboxes
  - File uploads
- Detects required fields
- Handles multi-select options
- Outputs structured JSON data

## Setup

1. Create a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install browser dependencies:
```bash
python src/install_browsers.py
```

## Usage

Run the scraper:
```bash
python src/main.py
```

The script will:
1. Open each job application URL
2. Extract all form elements
3. Save the data to JSON files in the `output` directory

## Output Format

The scraper generates JSON files with the following structure:
```json
{
    "url": "job_application_url",
    "timestamp": "timestamp",
    "elements": [
        {
            "label": "Field label/question",
            "id_of_input_component": "field identifier",
            "required": true/false,
            "type_of_input": "text|textarea|dropdown|multiselect|checkbox|radio|file|date",
            "options": ["option1", "option2"],  // For dropdowns, checkboxes, radio buttons
            "user_data_select_values": ["selected value"]
        }
    ]
}
```

## Project Structure

```
jobAuto/
├── src/
│   ├── main.py              # Main script
│   ├── install_browsers.py  # Browser installation script
│   ├── models/
│   │   └── form.py         # Form element data models
│   └── services/
│       ├── browser.py      # Browser service
│       └── form_scraper.py # Form scraping logic
├── requirements.txt        # Python dependencies
└── README.md
```

## Development

The scraper is designed to be extensible for different job portals. Currently supports:
- Phase 1: Lever.co job applications
- Future: Support for SmartRecruiters and Workday portals

## Requirements

- Python 3.9+
- Playwright
- See requirements.txt for full list of dependencies 