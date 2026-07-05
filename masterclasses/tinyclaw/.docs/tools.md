## Browser Tools
```json
tools = [
    {
        "name": "browse_url",
        "description": "Navigate to a URL and return the page title and text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to visit"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "click_element",
        "description": "Click an element on the page by CSS selector or text.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector or text content, e.g. 'button.submit' or 'text=Sign In'",
                },
            },
            "required": ["selector"],
        },
    },
    {
        "name": "fill_input",
        "description": "Type text into an input field.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input"},
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "get_page_content",
        "description": "Get the text content of the current page or a specific element.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Optional CSS selector to extract text from, e.g. '#title' or '.content' If empty, returns full page text.",
                },
            },
            "required": [],
        },
    },
]

```

## Memory Tools
```json
tools = [
    {
        "name": "save_note",
        "description": "Save a note or fact about the user to memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short descriptive key"},
                "content": {"type": "string", "description": "Note content"},
            },
            "required": ["key", "content"],
        },
    },
]
```