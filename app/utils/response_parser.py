"""
Response Parser Utilities
Extracts structured elements (buttons, links, etc.) from AI responses
Fixed to handle escaped slashes and various button formats
"""

import re
from typing import Dict, List, Any, Tuple


def parse_buttons_from_answer(answer: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Parse button tags from AI answer and extract them into structured format

    Supports formats:
    - <button>[button1] [button2]</button>
    - <button>button1</button>
    - <button>[button1]</button>
    - Multiple button tags
    - Handles escaped slashes (</button>)

    Args:
        answer: The AI's response text

    Returns:
        Tuple of (cleaned_answer, buttons_list)
        - cleaned_answer: Answer with button tags removed
        - buttons_list: List of button objects [{"type": "button", "value": "text"}]

    Examples:
        >>> parse_buttons_from_answer("Hello <button>[Yes] [No]</button>")
        ("Hello", [{"type": "button", "value": "Yes"}, {"type": "button", "value": "No"}])

        >>> parse_buttons_from_answer("Hello <button>Continue</button>")
        ("Hello", [{"type": "button", "value": "Continue"}])

        >>> parse_buttons_from_answer("Hello world")
        ("Hello world", [])
    """
    buttons = []
    cleaned_answer = answer

    # First, handle escaped slashes
    answer = answer.replace(r'<\/button>', '</button>')

    # Pattern to match <button>...</button> tags (case-insensitive, handles newlines)
    # Updated to be more flexible with whitespace and special characters
    button_pattern = r'<button[^>]*?>(.*?)</button>'

    # Find all button tags
    button_matches = list(re.finditer(button_pattern, answer, re.IGNORECASE | re.DOTALL))

    for match in button_matches:
        button_content = match.group(1).strip()

        # Parse individual buttons from content
        # Format 1: [button1] [button2] [button3]
        bracket_buttons = re.findall(r'\[([^\]]+)\]', button_content)

        if bracket_buttons:
            # Multiple buttons in brackets
            for button_text in bracket_buttons:
                button_text = button_text.strip()
                if button_text:
                    buttons.append({
                        "type": "button",
                        "value": button_text
                    })
        else:
            # Format 2: Single button without brackets or pipe-separated
            # Split by common separators if multiple buttons
            # Also handle newlines and multiple spaces
            button_content_clean = re.sub(r'\s+', ' ', button_content)
            button_texts = re.split(r'\s*[,|]\s*', button_content_clean)

            for button_text in button_texts:
                button_text = button_text.strip()
                if button_text and not button_text.startswith('<') and not button_text.endswith('>'):
                    buttons.append({
                        "type": "button",
                        "value": button_text
                    })

    # Remove all button tags from the answer (including escaped versions)
    # First handle the escaped version
    cleaned_answer = re.sub(r'<button[^>]*?>.*?<\\/button>', '', answer, flags=re.IGNORECASE | re.DOTALL)
    # Then handle the normal version
    cleaned_answer = re.sub(r'<button[^>]*?>.*?</button>', '', cleaned_answer, flags=re.IGNORECASE | re.DOTALL)

    # Clean up any extra whitespace and newlines
    cleaned_answer = re.sub(r'\n\s*\n', '\n', cleaned_answer)  # Multiple newlines to single
    cleaned_answer = re.sub(r'[ \t]+', ' ', cleaned_answer)  # Multiple spaces to single
    cleaned_answer = cleaned_answer.strip()

    return cleaned_answer, buttons


def parse_links_from_answer(answer: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Parse link tags from AI answer (future enhancement)

    Args:
        answer: The AI's response text

    Returns:
        Tuple of (cleaned_answer, links_list)
    """
    # Placeholder for future link parsing
    return answer, []


def parse_structured_elements(answer: str) -> Dict[str, Any]:
    """
    Parse all structured elements from AI answer

    Args:
        answer: The AI's response text

    Returns:
        Dict with:
        - cleaned_answer: Text with structured elements removed
        - buttons: List of button objects
        - links: List of link objects (future)
        - other structured elements...
    """
    # Parse buttons
    cleaned_answer, buttons = parse_buttons_from_answer(answer)

    # Parse links (future enhancement)
    cleaned_answer, links = parse_links_from_answer(cleaned_answer)

    return {
        "answer": cleaned_answer,
        "buttons": buttons,
        "links": links,
    }


# Convenience function for backward compatibility
def extract_buttons(answer: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Convenience function to extract buttons from answer
    Same as parse_buttons_from_answer
    """
    return parse_buttons_from_answer(answer)
