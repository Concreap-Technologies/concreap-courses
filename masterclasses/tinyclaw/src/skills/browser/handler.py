from playwright.async_api import async_playwright

#Globals
_browser = None
_page = None

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

async def get_page():
    global _browser, _page

    # If a browser and page are already active, reuse them instead of re-opening new ones
    if _browser and _page:
        return _page
    
    # Start playwright
    pw = await async_playwright().start()

    # Launch a new chromium broswer instance
    # "headless=True" -> means the broswer window will not be visible during execution
    _browser = await pw.chromium.launch(headless=True)

    # Open a new page (tab) in the launched browser
    _page = await _browser.new_page()

    return _page

# Tool Execution (Execution Function)
async def execute(tool_name, tool_input, context):
    try:
        page = await get_page()

        if tool_name == "browse_url":
            url: str = tool_input["url"]

            if not url.startswith("http"):
                url = "https://" + url

            await page.goto(url, wait_until="domcontentloaded", timeout=10000)

            title = await page.title()
            text = await page.inner_text("body")

            return {
                "title": title,
                "url": url,
                "content_preview": text.strip()[:3000]
            }

        elif tool_name == "click_element":
            await page.click(tool_input["selector"], timeout=3000)

            await page.wait_for_load_state("domcontentloaded")

            return {
                "clicked": tool_input["selector"],
                "new_url": page.url,
                "new_title": await page.title()
            }
        
        elif tool_name == "fill_input":
            await page.fill(tool_input["selector"], tool_input["text"])

            return {
                "filled": tool_input["selector"],
                "text": tool_input["text"]
            }
        
        elif tool_name == "get_page_content":

            selector = tool_input.get("selector") or "body"
            text = await page.inner_text(selector)


            return {
                "url": page.url,
                "content": text.strip()[:5000]
            }

        return { "error": f"unknown tool: {tool_name}" }
    
    except Exception as e:
        return {"error": str(e)}
