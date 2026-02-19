from typing import List, Dict, Any

def get_mcp_tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "name": "click_element",
            "description": "Click on a web element identified by its numerical label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "integer", "description": "The numerical label of the element to click."}
                },
                "required": ["label"]
            }
        },
        {
            "name": "type_text",
            "description": "Type text into a web element identified by its numerical label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "integer", "description": "The numerical label of the element to type into."},
                    "text": {"type": "string", "description": "The text to type."}
                },
                "required": ["label", "text"]
            }
        },
        {
            "name": "scrape_structured_data",
            "description": "Extract structured data from the current page using a natural language query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What information to extract (e.g., 'list of prices')."},
                    "schema": {"type": "object", "description": "Optional JSON schema for the output."}
                },
                "required": ["query"]
            }
        },
        {
            "name": "update_plan",
            "description": "Update the current task plan or progress.",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {"type": "array", "items": {"type": "string"}, "description": "The revised list of steps."}
                },
                "required": ["steps"]
            }
        }
    ]
