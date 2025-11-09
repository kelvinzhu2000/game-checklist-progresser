"""
AI Service for generating checklist items using OpenAI.
"""
import os
import json
import logging
import functools
from openai import OpenAI

logger = logging.getLogger(__name__)

def log_function_call(func):
    """Decorator to log function calls with parameters."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"{func.__name__} called with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper


@log_function_call
def generate_checklist_items(game_name, title, prompt, description=""):
    """
    Generate checklist items using OpenAI API.
    
    Args:
        game_name: Name of the game
        title: Title of the checklist
        prompt: User's description of what they want in the checklist
        description: Optional additional description
    
    Returns:
        List of dictionaries with 'title' and 'description' keys, or None if error
    """
    # Check if API key is available
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    
    try:
        # Initialize OpenAI client with timeout setting
        # Use default httpx client which handles proxies automatically from environment
        client = OpenAI(
            api_key=api_key,
            timeout=30.0
        )
        
        # Construct the prompt
        system_message = (
            "You are a helpful assistant that generates comprehensive checklists for video games. "
            "Generate a list of checklist items based on the user's request. "
            "Return ONLY a valid JSON array of objects, where each object has 'title' and 'description' fields. "
            "The title should be concise (under 200 characters) and the description should provide helpful details. "
            "Generate between 5-20 items depending on the scope of the request."
        )
        
        user_message = f"""Game: {game_name}
Checklist Title: {title}
User Request: {prompt}"""
        
        if description:
            user_message += f"\nAdditional Context: {description}"
        
        user_message += "\n\nGenerate a JSON array of checklist items."
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse the response
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response (in case it's wrapped in markdown)
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()
        
        # Parse JSON
        items = json.loads(content)
        
        # Validate the structure
        if not isinstance(items, list):
            return None
        
        valid_items = []
        for item in items:
            if isinstance(item, dict) and 'title' in item:
                # Ensure description exists
                if 'description' not in item:
                    item['description'] = ''
                # Truncate title if too long
                if len(item['title']) > 200:
                    item['title'] = item['title'][:197] + '...'
                valid_items.append(item)
        
        return valid_items if valid_items else None
        
    except Exception as e:
        # Log error for debugging
        logger.error(f"Error generating checklist items: {e}")
        return None
