"""
Code Generator for Raspberry Pi Examples
Generates code from enhanced prompts
Created: 2025-03-26 01:28:38
Author: Sakkibbb
"""

import re
import os
import time
import logging
from datetime import datetime
import random
from typing import Dict, List, Tuple, Optional, Any
import dkb

# Logger configuration
logger = logging.getLogger(__name__)

class CodeGenerator:
    def __init__(self, api_client, code_validator, 
                output_dir: str = "raspberry_pi_code_examples",
                max_retries: int = 3,
                debug_dir: str = None,
                invalid_dir: str = None,
                accept_invalid_on_final: bool = False):
        """Initialize the code generator."""
        self.api_client = api_client
        self.code_validator = code_validator
        self.output_dir = output_dir
        self.max_retries = max_retries
        self.accept_invalid_on_final = accept_invalid_on_final
        
        # Set up directories
        self.debug_dir = debug_dir or os.path.join(output_dir, "debug")
        self.invalid_dir = invalid_dir or os.path.join(output_dir, "invalid_examples")
        os.makedirs(self.debug_dir, exist_ok=True)
        os.makedirs(self.invalid_dir, exist_ok=True)

    def extract_code(self, response_text: str) -> str:
        """Extract code from response text, removing markdown formatting if present."""
        if not response_text:
            return ""

        # Try to extract the first fenced code block. This handles ```python,
        # ```py, a bare ``` block, an optional language tag, a missing trailing
        # newline after the opening fence, and surrounding prose.
        pattern = r"```[a-zA-Z0-9_+-]*[ \t]*\n?(.*?)```"
        match = re.search(pattern, response_text, re.DOTALL)

        if match:
            return match.group(1).strip("\n")

        # Truncated/unclosed fenced block (e.g. the model hit MAX_TOKENS
        # mid-block): there is an opening fence but no closing one. Strip
        # everything up to and including the opening fence and recover the
        # remaining (truncated) code instead of losing it.
        open_fence = re.search(r"```[a-zA-Z0-9_+-]*\s*\n", response_text)
        if open_fence:
            recovered = response_text[open_fence.end():].strip("\n")
            return recovered if recovered.strip() else ""

        # No fenced block found: strip any stray leading/trailing ``` lines and
        # return the remaining text trimmed (assuming it might be raw code).
        lines = response_text.splitlines()
        while lines and lines[0].strip().startswith("```"):
            lines.pop(0)
        while lines and lines[-1].strip().startswith("```"):
            lines.pop()
        return "\n".join(lines).strip()

    def generate_task_title(self, category: str, subcategory: str, context: str) -> str:
        """Generate a descriptive task title."""
        return f"Create a {subcategory.title()} {category.title()} Application for {context.title()}"

    def generate_tags(self, category: str, subcategory: str, context: str, 
                     pi_model: str, integration: str, complexity: str) -> List[str]:
        """Generate relevant tags for the example."""
        # Base tags include category and subcategory
        tags = [category, subcategory, complexity]
        
        # Extract main context word
        context_words = context.split()
        if context_words:
            tags.append(context_words[-1])
        
        # Add Pi model tag
        pi_tag = pi_model.lower().replace(" ", "-")
        tags.append(pi_tag)
        
        # Add integration tag if it's not just "standalone"
        if integration != "standalone":
            integration_tag = integration.lower().replace(" ", "-")
            tags.append(integration_tag)
        
        return tags

    def generate_code(self, generated_prompt: str, metadata: Dict[str, Any], 
                       base_delay: float = 2.0, jitter: float = 1.0) -> Tuple[Optional[str], int]:
        """Generate code based on an enhanced prompt."""
        # Customize code generation instructions based on complexity
        complexity = metadata["complexity"]
        code_instructions = ""
        if complexity == "beginner_basic":
            code_instructions = """
            1. Keep the code EXTREMELY SIMPLE - between 30-50 lines total
            2. Focus on a single core concept that's easy to understand
            3. Use minimal imports - only what's absolutely necessary
            4. Include comments explaining each major step
            5. Use simple error handling if any
            6. Make code suitable for absolute beginners with no prior experience
            """
        else:
            code_instructions = f"""
            1. Use ONLY standard Raspberry Pi libraries like RPi.GPIO, gpiozero, picamera, smbus, etc.
            2. NEVER import from custom modules like 'sensor.py', 'data_logger.py', etc.
            3. All classes and functions must be defined DIRECTLY in the main file
            4. Keep code length appropriate for {complexity} level
            5. Make sure to explicitly mention "{metadata['subcategory']}" in your code comments or variable names
            6. Include AT LEAST 5 detailed comment lines explaining implementation details
            7. Include proper error handling and graceful shutdown
            8. The code must be complete, functional, and realistic for a {metadata['context']}
            """

        # Recommended libraries for this task, drawn from the domain knowledge base.
        recommended_libs = dkb.get_domain_libraries(metadata.get("category"), metadata.get("subcategory"))[:4]
        libraries_instruction = (
            f"\n            - Prefer these libraries where appropriate: {', '.join(recommended_libs)}."
            if recommended_libs else ""
        )

        # Assemble the final code-generation prompt. The complexity-specific items above
        # carry their own numbering; the universal rules below are bullets, so the list
        # never has gaps or empty entries.
        code_generation_prompt = f"""
        {generated_prompt}

        CRITICAL REQUIREMENTS - your code MUST satisfy ALL of these:
        {code_instructions}
            - Output a single Python code block: start with ```python and end with ```.
            - Do NOT include any text or explanation outside of code comments.{libraries_instruction}

        This must be a realistic Raspberry Pi implementation for {metadata['pi_model']}, usable in a real-world {metadata['context']}.
        """
        
        # Try multiple times in case of failure
        for attempt in range(self.max_retries):
            try:
                # Generate code with slightly higher temperature for creativity
                # Use lower temperature for beginner_basic to ensure simpler code
                temp = 0.6 if complexity == "beginner_basic" else 0.65
                response_text = self.api_client.call_gemini_api(code_generation_prompt, temperature=temp)
                
                if not response_text:
                    logger.warning(f"Empty response from API, retrying ({attempt+1}/{self.max_retries})")
                    time.sleep(base_delay)
                    continue
                    
                # Extract and clean the code
                code = self.extract_code(response_text)
                
                # Debug: Print first few lines of code for inspection
                code_preview = "\n".join((code or "").split("\n")[:5])
                logger.info(f"Code preview (first 5 lines):\n{code_preview}...")
                
                # Save raw response for debugging regardless of validation.
                # Include microseconds so rapid retries don't overwrite each other.
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                # Sanitize category/subcategory: they're interpolated into a file
                # path and may contain '/', spaces, or other unsafe characters.
                safe = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{metadata['category']}_{metadata['subcategory']}")
                debug_file = os.path.join(self.debug_dir, f"raw_response_{safe}_{timestamp}.txt")
                with open(debug_file, 'w', encoding="utf-8") as f:
                    f.write(response_text)
                
                # Validate the code with the code validator
                is_valid, validation_errors, validation_details = self.code_validator.validate(
                    code=code,
                    category=metadata['category'],
                    subcategory=metadata['subcategory'],
                    complexity=complexity
                )
                
                if is_valid:
                    # Successfully generated valid code
                    quality_score = validation_details.get("quality_score", 0)
                    return code, quality_score
                else:
                    logger.warning(f"Generated code failed validation, retrying ({attempt+1}/{self.max_retries})")
                    logger.warning(f"Validation errors: {', '.join(validation_errors)}")
                    
                    # Save invalid example for inspection
                    self.code_validator.save_invalid_example(
                        code=code,
                        category=metadata['category'],
                        subcategory=metadata['subcategory'],
                        errors=validation_errors,
                        output_dir=self.invalid_dir,
                        timestamp=timestamp
                    )
                    
                    # On last attempt, optionally accept code anyway with a warning flag
                    if attempt == self.max_retries - 1:
                        if self.accept_invalid_on_final:
                            logger.warning("Accepting code despite validation failures (last attempt)")
                            metadata["validation_warning"] = True
                            quality_score = validation_details.get("quality_score", 0)
                            return code, quality_score
                        else:
                            logger.warning("Rejecting code after final attempt failed validation")
                            return None, 0
            except Exception as e:
                logger.error(f"Error generating example: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Wait before retrying
            time.sleep(base_delay + random.uniform(0, jitter))
        
        # If we reach here, all attempts failed
        logger.error(f"Failed to generate valid code after {self.max_retries} attempts")
        return None, 0