WEB_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate to a specific URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_element",
            "description": "Click on a web element by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_id": {"type": "integer", "description": "The ID of the element to click."}
                },
                "required": ["element_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into a web element.",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_id": {"type": "integer", "description": "The ID of the element to type into."},
                    "text": {"type": "string", "description": "The text to type."}
                },
                "required": ["element_id", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "Scroll the page up or down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "description": "The direction to scroll."}
                },
                "required": ["direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_page",
            "description": "Extract structured data from the current page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What information to look for."},
                    "schema": {"type": "object", "description": "Optional JSON schema for the output."}
                }
            }
        }
    }
]
