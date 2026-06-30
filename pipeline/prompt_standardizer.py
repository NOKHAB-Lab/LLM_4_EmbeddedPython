"""
Prompt Standardizer Module
Converts enriched prompts and generated code into standardized, concise instructions
Created: 2025-04-20 10:31:12
Author: Sakkibbb
"""

import logging
import re
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

class PromptStandardizer:
    """
    Standardizes complex prompts into concise, direct instructions
    using the original prompt and generated code.
    """
    
    def __init__(self, api_client):
        """
        Initialize the prompt standardizer.
        
        Args:
            api_client: Client for making API calls to Gemini
        """
        self.api_client = api_client
    
    def standardize_prompt(self, original_prompt: str, code: str) -> Optional[str]:
        """
        Generate a concise, direct instruction-style prompt for code generation tasks,
        using the original task and the original code block to extract relevant information.
        
        Args:
            original_prompt: The original enriched prompt
            code: The generated code from this prompt
            
        Returns:
            A standardized prompt without newlines, or None if generation fails
        """
        system_prompt = """
        Create a direct programming instruction that asks for specific code functionality using the original task and the 
        original code block to extract relevant information.
        
        IMPORTANT REQUIREMENTS:
        1. Your response must be a SINGLE PARAGRAPH with no line breaks.
        2. Start with phrases like "Write code that..." or "Create a program to...".
        3. Be specific about implementation details (e.g., GPIO pins, values, file paths).
        4. Focus only on WHAT the code should accomplish, not how to write it.
        5. DO NOT include any code snippets in the instruction.
        6. Extract the correct pin numbers, timing delays, and other hardware-related information from the original code.
        7. Make sure to preserve the core task while being more direct and concise.
        8. Describe the functional requirement rather than prescribing a library; only mention a specific library by name when it is essential to the task.
        9. Use semicolons to separate distinct requirements instead of line breaks.
        10. Keep the total length between 3-12 sentences.
        """

        prompt = (
            f"{system_prompt}\n\n"
            f"Original Task:\n{original_prompt}\n\n"
            "Original Code:\n```python\n"
            f"{code}\n"
            "```"
        )

        result = self.api_client.call_gemini_api(prompt, temperature=0.4)
        if not result:
            logger.warning("Failed to generate standardized prompt")
            return None
        
        # Clean up the result: Remove any line breaks and excess whitespace
        cleaned_result = re.sub(r'\s+', ' ', result).strip()
        
        # Log the result for debugging
        logger.debug(f"Generated standardized prompt: {cleaned_result}")
        
        return cleaned_result