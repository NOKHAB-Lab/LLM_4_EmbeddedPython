#!/usr/bin/env python3
"""
Raspberry Pi Code Example Generator - Main Script v5
Generates realistic Raspberry Pi code examples for training AI models
Enhanced with context-aware validation and flat JSON output structure
Author: Sakkibbb
"""

import os
import json
import re
import random
import time
import logging
import sys
import argparse
import traceback
from tqdm import tqdm
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from collections import defaultdict

# Import our modules
from validation import CodeValidator
from progress_manager import ProgressManager
from dkb import (
    CATEGORIES, CODE_STYLES, COMPLEXITY_LEVELS, PI_MODELS, INTEGRATION_PATTERNS,
    USE_CONTEXTS, STANDARD_LIBRARIES_FLAT,
    SENSOR_LIBRARIES, ACTUATOR_LIBRARIES, CAMERA_LIBRARIES,
    IOT_LIBRARIES, ML_LIBRARIES, BEGINNER_BASIC_LIBRARIES
)
from api_client import APIClient
from prompt_generator import PromptGenerator
from code_generator import CodeGenerator
from prompt_standardizer import PromptStandardizer

# Define hardware and software categories for context-aware validation
HARDWARE_CATEGORIES = [
    "sensors", "actuators", "cameras", "robotics", "beginner_basic"
]

SOFTWARE_CATEGORIES = [
    "iot_applications", "ml_applications", "communications"
]

# Create a mapping of specialized libraries by category
SPECIALIZED_LIBRARIES = {
    "sensors": SENSOR_LIBRARIES,
    "actuators": ACTUATOR_LIBRARIES,
    "cameras": CAMERA_LIBRARIES,
    "iot_applications": IOT_LIBRARIES,
    "ml_applications": ML_LIBRARIES,
    "beginner_basic": BEGINNER_BASIC_LIBRARIES
}

# Configure logging to file and console
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
os.makedirs('logs', exist_ok=True)
log_file = os.path.join('logs', f'generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Script execution context
CURRENT_TIME = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
try:
    CURRENT_USER = os.getlogin()
except Exception:
    CURRENT_USER = "Sakkibbb"

# Global configuration settings
TOTAL_EXAMPLES = 8000  # Default value, can be overridden by command line args
OUTPUT_DIR = "raspberry_pi_code_examples_v5"  # Default value, can be overridden
MIN_QUALITY_SCORE = 60  # Reduced from 70 to 60 as requested
MAX_CORRECTION_ATTEMPTS = 4  # Maximum number of attempts to correct a code sample

# Code length guidelines by complexity level
CODE_LENGTH_LIMITS = {
    "beginner_basic": 20,  # ~30 lines with 50% tolerance
    "beginner": 60,       # ~90 lines with 50% tolerance
    "intermediate": 150,   # ~225 lines with 50% tolerance
    "advanced": 200       # ~300 lines with 50% tolerance
}

# Category-specific length adjustments
CATEGORY_LENGTH_ADJUSTMENTS = {
    "iot_applications": 1.25,  # Allow 25% more lines
    "ml_applications": 1.3,    # Allow 30% more lines
    "cameras": 1.2,            # Allow 20% more lines
    "robotics": 1.2,           # Allow 20% more lines
    "display": 1.15,           # Allow 15% more lines
    "actuators": 1.1           # Allow 10% more lines
}

# Target complexity distribution - weighted toward easier levels (sums to 1.0)
TARGET_COMPLEXITY_DISTRIBUTION = {
    "beginner_basic": 0.25,
    "beginner": 0.30,
    "intermediate": 0.25,
    "advanced": 0.20
}

# Maximum number of output tokens for API generation/correction calls
MAX_OUTPUT_TOKENS = 2048

# Validation error tracking
error_tracker = defaultdict(int)

# API Configuration - load API keys from the environment (comma-separated)
def _load_api_keys():
    raw = os.environ.get("GEMINI_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return keys

API_KEYS = _load_api_keys()

# Rate limiting settings
BASE_DELAY = 1
JITTER = 1      
MAX_REQUESTS_PER_MINUTE = 30
MAX_RETRIES = 3

# Global variables for execution
EXECUTION_TIME = None
METADATA_FILE = None
EXAMPLE_COLLECTION_FILE = None
DEBUG_DIR = None
VALID_DIR = None
INVALID_DIR = None

# Collection to store all examples
all_examples = []

def initialize_metadata_files():
    """Initialize metadata files and directories."""
    global EXECUTION_TIME, METADATA_FILE, EXAMPLE_COLLECTION_FILE, DEBUG_DIR, VALID_DIR, INVALID_DIR
    
    # Create execution timestamp for unique filenames
    EXECUTION_TIME = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
    
    # Set up file paths
    METADATA_FILE = os.path.join(OUTPUT_DIR, f"generation_metadata_{EXECUTION_TIME}.json")
    EXAMPLE_COLLECTION_FILE = os.path.join(OUTPUT_DIR, f"example_collection_{EXECUTION_TIME}.json")
    DEBUG_DIR = os.path.join(OUTPUT_DIR, "debug")
    VALID_DIR = os.path.join(OUTPUT_DIR, "valid")  # New directory for valid examples
    INVALID_DIR = os.path.join(OUTPUT_DIR, "invalid")  # Directory for invalid examples
    
    # Ensure output directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)
    os.makedirs(VALID_DIR, exist_ok=True)
    os.makedirs(INVALID_DIR, exist_ok=True)
    
    # Log the initialization
    logger.info(f"Initialized metadata files with timestamp {EXECUTION_TIME}")
    logger.info(f"Metadata file: {METADATA_FILE}")
    logger.info(f"Example collection file: {EXAMPLE_COLLECTION_FILE}")
    logger.info(f"Valid examples directory: {VALID_DIR}")
    logger.info(f"Invalid examples directory: {INVALID_DIR}")

def is_valid_syntax(code: str) -> Tuple[bool, str]:
    """Check if code has valid Python syntax using compile().
    
    Args:
        code: Python code to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        compile(code, "<string>", "exec")
        return True, ""
    except Exception as e:
        return False, str(e)

def validate_imports(code: str, allowed_libraries: List[str], category: str = None) -> Tuple[bool, List[str]]:
    """Validate that imports in code are from allowed libraries with context awareness.
    
    Args:
        code: Python code to check
        allowed_libraries: List of allowed library names
        category: Category to determine context-specific validation
        
    Returns:
        Tuple of (is_valid, invalid_imports)
    """
    # Extract imports using regex
    import_patterns = [
        r'import\s+([\w\.]+)',  # Matches: import library
        r'from\s+([\w\.]+)\s+import',  # Matches: from library import ...
    ]
    
    all_imports = []
    for pattern in import_patterns:
        imports = re.findall(pattern, code)
        all_imports.extend(imports)
    
    # Python standard libraries to ignore
    PYTHON_STANDARD_LIBS = [
        "os", "sys", "time", "datetime", "random", "math", "json", "logging", 
        "argparse", "collections", "re", "threading", "multiprocessing", 
        "subprocess", "shutil", "glob", "pathlib", "csv", "sqlite3", 
        "tempfile", "hashlib", "uuid", "socket", "ssl", "email", "urllib", 
        "http", "ftplib", "smtplib", "asyncio", "typing", "enum", "abc",
        "functools", "itertools", "operator", "contextlib", "traceback"
    ]
    
    # Check if all imports are in the allowed libraries list
    invalid_imports = []
    for imp in all_imports:
        # Skip standard Python libraries
        base_lib = imp.split('.')[0]
        if base_lib in PYTHON_STANDARD_LIBS or imp == '__future__':
            continue
            
        # First check the full import path (e.g., "RPi.GPIO")
        if imp in allowed_libraries:
            continue
            
        # Then check the base library name (e.g., "RPi")
        if base_lib in allowed_libraries:
            continue
        
        # Context-aware validation
        if category in SOFTWARE_CATEGORIES:
            # For software applications, be more strict about hardware libraries
            hardware_libs = ["RPi", "GPIO", "gpiozero", "pigpio", "board", "busio"]
            if base_lib in hardware_libs:
                # Check if the code actually uses hardware functionality
                if "gpio" not in code.lower() and "pin" not in code.lower():
                    invalid_imports.append(f"{imp} (hardware library in software-focused code)")
                    continue
        
        # If we get here, the import is not allowed
        invalid_imports.append(imp)
    
    return len(invalid_imports) == 0, invalid_imports

def extract_requirements(code: str) -> List[str]:
    """Extract package requirements from code.
    
    Args:
        code: Python code to analyze
        
    Returns:
        List of package names for requirements
    """
    # Python standard libraries to ignore
    PYTHON_STANDARD_LIBS = [
        "os", "sys", "time", "datetime", "random", "math", "json", "logging", 
        "argparse", "collections", "re", "threading", "multiprocessing", 
        "subprocess", "shutil", "glob", "pathlib", "csv", "sqlite3", 
        "tempfile", "hashlib", "uuid", "socket", "ssl", "email", "urllib", 
        "http", "ftplib", "smtplib", "asyncio", "typing", "enum", "abc",
        "functools", "itertools", "operator", "contextlib", "traceback"
    ]
    
    # Extract imports using regex
    import_patterns = [
        r'import\s+([\w\.]+)',  # Matches: import library
        r'from\s+([\w\.]+)\s+import',  # Matches: from library import ...
    ]
    
    all_imports = []
    for pattern in import_patterns:
        imports = re.findall(pattern, code)
        all_imports.extend(imports)
    
    # Filter out standard libraries and get unique imports
    unique_imports = []
    for imp in all_imports:
        base_lib = imp.split('.')[0]
        if base_lib not in PYTHON_STANDARD_LIBS and base_lib != '__future__' and imp not in unique_imports:
            unique_imports.append(imp)
    
    return unique_imports

def is_length_valid(code: str, target_lines: int, tolerance: float = 0.5) -> Tuple[bool, str]:
    """Check if code length is within tolerance of target.
    
    Args:
        code: Python code to check
        target_lines: Target number of lines
        tolerance: Tolerance as a fraction (0.5 = ±50%)
        
    Returns:
        Tuple of (is_valid, message)
    """
    num_lines = len(code.strip().splitlines())
    min_lines = int(target_lines * (1 - tolerance))
    max_lines = int(target_lines * (1 + tolerance))
    
    if min_lines <= num_lines <= max_lines:
        return True, ""
    elif num_lines < min_lines:
        return False, f"Code is too short: {num_lines} lines (minimum {min_lines})"
    else:
        return False, f"Code is too long: {num_lines} lines (maximum {max_lines})"

def run_pylint_if_applicable(code: str, threshold: int = 200):
    """Run pylint on code if applicable (not too long).
    
    Args:
        code: Python code to check
        threshold: Maximum lines to run pylint on
        
    Returns:
        Tuple of (pylint_score, pylint_feedback) or (None, None) if not applicable
    """
    num_lines = len(code.strip().splitlines())

    # Skip pylint for large files (not assessed -> neutral)
    if num_lines > threshold:
        return None, None

    # Check if pylint is available
    try:
        from pylint import lint
        from io import StringIO
        import sys
        import tempfile
        import json
    except ImportError:
        logger.warning("Pylint not available, skipping pylint check")
        return None, None  # Neutral: pylint unavailable

    # Create a temporary file for pylint
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code.encode('utf-8'))

    try:
        # Capture pylint output
        original_stdout = sys.stdout
        pylint_output = StringIO()
        sys.stdout = pylint_output

        # Run pylint with JSON output
        lint_args = [
            '--output-format=json',
            '--disable=C0111',  # Missing docstring - often acceptable in examples
            temp_file_path
        ]

        lint.Run(lint_args, exit=False)

        # Restore stdout
        sys.stdout = original_stdout

        # Parse JSON output
        try:
            output_str = pylint_output.getvalue()
            if output_str:
                pylint_data = json.loads(output_str)

                # Compute the score from the parsed messages: count errors and
                # warnings and penalize accordingly (errors weigh more).
                error_count = 0
                warning_count = 0
                feedback = []
                for issue in pylint_data:
                    issue_type = issue.get('type', '')
                    if issue_type in ('error', 'fatal'):
                        error_count += 1
                    elif issue_type in ('warning', 'convention', 'refactor'):
                        warning_count += 1
                    msg = f"Line {issue['line']}: {issue['message']} ({issue['symbol']})"
                    feedback.append(msg)

                score = max(0.0, 10.0 - (error_count * 1.0 + warning_count * 0.5))

                return score, feedback[:10]  # Return score and top 10 issues
            return 10.0, []  # No issues reported -> clean
        except json.JSONDecodeError:
            logger.warning("Failed to parse pylint JSON output")
            return None, None  # Neutral: could not parse pylint output
    except Exception as e:
        logger.error(f"Error running pylint: {str(e)}")
        return None, None  # Neutral: pylint failed to run
    finally:
        # Clean up temporary file
        try:
            os.remove(temp_file_path)
        except Exception:
            pass

def adjust_prompt_for_frequent_errors(category: str, subcategory: str, error_type: str, prompt: str) -> str:
    """Add clarifying instructions to prompt based on frequent error types with context awareness.
    
    Args:
        category: Code category
        subcategory: Code subcategory
        error_type: Type of error (syntax, import, length, pylint)
        prompt: Original prompt
        
    Returns:
        Adjusted prompt
    """
    # Create a key for the error tracker
    error_key = f"{category}:{subcategory}:{error_type}"
    
    # Increment error count
    error_tracker[error_key] += 1
    
    # Only adjust prompt if this error is frequent (occurs 2+ times)
    if error_tracker[error_key] < 2:
        return prompt
    
    # Determine if this is a hardware or software category
    is_hardware = category in HARDWARE_CATEGORIES
    is_software = category in SOFTWARE_CATEGORIES
    
    # Add appropriate clarification based on error type and category
    clarifications = {
        "syntax": "\n\nIMPORTANT: Please ensure the code has valid Python syntax with no syntax errors.",
        "import": "\n\nIMPORTANT: Only use standard Python libraries and " +
                 ("appropriate Raspberry Pi hardware libraries for this application." if is_hardware else
                  "software-oriented libraries. Only include hardware libraries if absolutely necessary for this application."),
        "length": "\n\nIMPORTANT: Keep the code length appropriate for the requested complexity level.",
        "pylint": "\n\nIMPORTANT: Ensure code follows PEP 8 style guidelines with proper naming conventions, indentation, and documentation."
    }
    
    # Add clarification if available for this error type
    if error_type in clarifications:
        prompt += clarifications[error_type]
    
    return prompt

def validate_code_comprehensive(code: str, category: str, subcategory: str, complexity: str, 
                              code_validator, standard_libraries: List[str]) -> Tuple[bool, Dict, List[str]]:
    """Run all validations in a single pass and collect all issues with context awareness.
    
    Args:
        code: Python code to validate
        category: Code category
        subcategory: Code subcategory
        complexity: Code complexity
        code_validator: CodeValidator instance
        standard_libraries: List of allowed libraries
        
    Returns:
        Tuple of (is_valid, validation_details, error_messages)
    """
    validation_details = {}
    error_messages = []
    critical_failure = False
    
    # 1. Syntax validation
    syntax_valid, syntax_error = is_valid_syntax(code)
    validation_details["syntax_valid"] = syntax_valid
    
    if not syntax_valid:
        error_messages.append(f"Syntax error: {syntax_error}")
        critical_failure = True
    
    # 2. Import validation with context awareness
    imports_valid, invalid_imports = validate_imports(code, standard_libraries, category)
    validation_details["imports_valid"] = imports_valid
    validation_details["invalid_imports"] = invalid_imports
    
    if not imports_valid:
        error_messages.append(f"Invalid imports: {', '.join(invalid_imports)}")
        critical_failure = True
    
    # 3. Extract requirements
    requirements = extract_requirements(code)
    validation_details["requirements"] = requirements
    
    # 4. Length validation with category-specific adjustment
    base_target_length = CODE_LENGTH_LIMITS.get(complexity, 100)
    adjustment_factor = CATEGORY_LENGTH_ADJUSTMENTS.get(category, 1.0)
    adjusted_target_length = int(base_target_length * adjustment_factor)
    
    # Use adjusted target for length validation
    length_valid, length_message = is_length_valid(code, adjusted_target_length)
    validation_details["length_valid"] = length_valid
    validation_details["line_count"] = len(code.strip().splitlines())
    
    if not length_valid:
        error_messages.append(length_message)
    
    # 5. Run standard code validator
    is_valid, validation_errors, validator_details = code_validator.validate(
        code=code,
        category=category,
        subcategory=subcategory,
        complexity=complexity
    )
    
    # Merge validation details
    validation_details.update(validator_details)
    
    # Add validation errors to error messages
    if validation_errors:
        error_messages.extend(validation_errors)
    
    # 6. Check for category-specific patterns
    if category in HARDWARE_CATEGORIES and "GPIO" not in code and "gpiozero" not in code:
        if not any(hw_term in code.lower() for hw_term in ["gpio", "pin", "board", "sensor", "actuator"]):
            error_messages.append(f"Missing hardware interaction code for {category} category")
    
    # 7. Pylint validation (if applicable)
    pylint_score, pylint_feedback = run_pylint_if_applicable(code)
    
    # Always store pylint results
    validation_details["pylint_score"] = pylint_score
    validation_details["pylint_feedback"] = pylint_feedback

    # A None score means pylint could not assess the code (unavailable, skipped,
    # or parse failure) -> treat as neutral and exclude it from scoring entirely.
    if pylint_score is not None:
        # Convert pylint score (0-10) to scale of 100
        normalized_score = pylint_score * 10
        validation_details["pylint_normalized"] = normalized_score

        # Add pylint score to quality calculation
        if "quality_score" in validation_details:
            # Weight: 70% original score, 30% pylint
            validation_details["quality_score"] = (
                validation_details["quality_score"] * 0.7 +
                normalized_score * 0.3
            )

        # Add pylint feedback to error messages if score is low
        if pylint_score < 6.0:  # Below 6/10 is concerning
            error_messages.append(f"Pylint score too low ({pylint_score}/10). Issues:")
            for issue in (pylint_feedback or [])[:5]:  # Top 5 issues
                error_messages.append(f"  - {issue}")
    
    # Check if quality score meets minimum threshold
    quality_score = validation_details.get("quality_score", 0)
    validation_details["meets_quality_threshold"] = quality_score >= MIN_QUALITY_SCORE
    
    if quality_score < MIN_QUALITY_SCORE:
        error_messages.append(f"Quality score too low: {quality_score:.1f}/100 (minimum {MIN_QUALITY_SCORE})")
    
    # Final validity determination: syntax, imports, and quality must all be valid
    is_valid = (
        syntax_valid and 
        imports_valid and 
        quality_score >= MIN_QUALITY_SCORE and
        not critical_failure
    )
    
    return is_valid, validation_details, error_messages

def send_code_for_correction(code: str, error_messages: List[str], original_prompt: str,
                           category: str, subcategory: str, complexity: str, error_type: str, api_client):
    """Send code with error messages to LLM for correction with context awareness.

    Args:
        code: Original code
        error_messages: List of validation error messages
        original_prompt: Original prompt
        category: Code category
        subcategory: Code subcategory
        complexity: Code complexity level
        error_type: Primary type of error (for prompt adjustment)
        api_client: APIClient instance

    Returns:
        Corrected code or None if correction failed
    """
    # Adjust prompt based on frequent errors
    adjusted_prompt = adjust_prompt_for_frequent_errors(category, subcategory, error_type, original_prompt)
    
    # Get adjusted length limit for this complexity level
    target_length = CODE_LENGTH_LIMITS.get(complexity, 100)
    adjustment_factor = CATEGORY_LENGTH_ADJUSTMENTS.get(category, 1.0)
    adjusted_length = int(target_length * adjustment_factor)
    
    # Determine specific guidance based on category type
    is_hardware = category in HARDWARE_CATEGORIES
    is_software = category in SOFTWARE_CATEGORIES
    
    hardware_guidance = ""
    if is_hardware:
        hardware_guidance = "Must properly utilize appropriate Raspberry Pi hardware libraries and GPIO interfaces."
    elif is_software:
        hardware_guidance = "Focus on software functionality. Only include hardware libraries if absolutely necessary."
    else:
        hardware_guidance = "Include appropriate hardware interaction for this specific application."
    
    # Create a detailed correction request
    correction_prompt = f"""
    You are a Python expert specializing in Raspberry Pi code. Please fix the following code to address all validation issues.
    
    ORIGINAL PROMPT:
    {adjusted_prompt}
    
    CURRENT CODE:
    ```python
    {code}
    ```
    
    VALIDATION ERRORS TO FIX:
    {chr(10).join([f"- {error}" for error in error_messages])}
    
    CODE REQUIREMENTS:
    - Category: {category}/{subcategory}
    - Complexity level: {complexity}
    - Target line count: {adjusted_length} lines (±50%)
    - {hardware_guidance}
    
    INSTRUCTIONS:
    1. Address ALL the listed errors
    2. Do not change the core functionality
    3. Ensure the code follows best practices and is well-commented
    4. Provide ONLY the corrected code without explanations
    5. Ensure code is completely self-contained and does not import from custom modules
    
    CORRECTED CODE:
    ```python
    """
    
    # Send to LLM for correction
    result = api_client.call_gemini_api(correction_prompt, temperature=0.2)
    
    # Extract code from response
    if result:
        # Try to extract code between markdown blocks
        code_match = re.search(r'```python\s+(.*?)\s+```', result, re.DOTALL)
        
        if code_match:
            return code_match.group(1).strip()
        
        # If no markdown blocks, check if the response looks like Python code
        if result.strip().startswith('import ') or result.strip().startswith('from ') or result.strip().startswith('#'):
            return result.strip()
            
        # If no clear code found, log and return None
        logger.warning("LLM response did not contain clear code block")
        
    return None

def save_example(code, metadata, code_generator, progress_manager, validation_details, is_valid):
    """Save the generated code example with metadata in a flat JSON structure."""
    try:
        # Generate a task title
        task_title = code_generator.generate_task_title(
            metadata["category"], 
            metadata["subcategory"], 
            metadata["context"]
        )
        
        # Generate tags
        tags = code_generator.generate_tags(
            metadata["category"], 
            metadata["subcategory"], 
            metadata["context"], 
            metadata["pi_model"], 
            metadata["integration"],
            metadata["complexity"]
        )
        
        # Get quality score from validation details
        quality_score = validation_details.get("quality_score", 0)
        
        # Extract requirements from validation_details
        requirements = validation_details.get("requirements", [])
        
        # Create filename with ID and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{metadata['category']}_{metadata['subcategory']}_{metadata['id']}_{timestamp}.py"
        
        # Determine output directory based on validation result
        if is_valid:
            output_dir = VALID_DIR
            status = "AIV"  # AI Validated
        else:
            output_dir = INVALID_DIR
            status = "AIVF"  # AI Validation Failed
            
        filepath = os.path.join(output_dir, filename)
        
        # Create the flattened example object (no nested structures)
        example_object = {
            "task": task_title,
            "prompt": metadata["generated_prompt"],
            "standardized_prompt": metadata.get("standardized_prompt", ""),
            "code": code,
            "complexity": metadata["complexity"],
            "tags": tags,
            "source": "gemini-api",
            "verification_status": status,
            "quality_score": quality_score,
            "is_valid": is_valid,
            "requirements": requirements,  # Add requirements at top level
            
            # Include all metadata fields at top level
            "id": metadata["id"],
            "category": metadata["category"],
            "subcategory": metadata["subcategory"],
            "style": metadata["style"],
            "pi_model": metadata["pi_model"],
            "integration": metadata["integration"],
            "context": metadata["context"],
            "timestamp": metadata["timestamp"],
            "filename": filename,
            "correction_attempts": metadata.get("correction_attempts", 0),
            "is_hardware": metadata.get("is_hardware", metadata["category"] in HARDWARE_CATEGORIES),
            "is_software": metadata.get("is_software", metadata["category"] in SOFTWARE_CATEGORIES)
        }
        
        # Add all validation details at top level (excluding requirements which we already added)
        for key, value in validation_details.items():
            if key != "requirements":  # Skip requirements since we already included it
                example_object[key] = value
        
        # Create a temporary nested metadata field for backward compatibility with progress_manager
        example_object["metadata"] = {
            "id": metadata["id"],
            "category": metadata["category"],
            "subcategory": metadata["subcategory"],
            "timestamp": metadata["timestamp"]
        }
        
        # Save the code to a Python file
        with open(filepath, 'w', encoding="utf-8") as f:
            # Add header comment with metadata
            f.write(f"# {task_title}\n")
            f.write(f"# Generated: {metadata['timestamp']}\n")
            f.write(f"# Complexity: {metadata['complexity']}, Style: {metadata['style']}\n")
            
            # Add standardized prompt as a comment if available
            if metadata.get("standardized_prompt"):
                f.write(f"# Task: {metadata['standardized_prompt']}\n")
                
            f.write(f"# Tags: {', '.join(tags)}\n")
            f.write(f"# Quality Score: {quality_score:.1f}/100\n")
            f.write(f"# Validation Status: {status}\n")
            f.write(f"# Requirements: {', '.join(requirements)}\n")
            
            # Add context information to header comments
            f.write(f"# Type: {'Hardware' if metadata.get('is_hardware', metadata['category'] in HARDWARE_CATEGORIES) else 'Software'} focused\n\n")
            
            f.write(code)
        
        # Record completion in progress manager
        progress_manager.record_completion(example_object, success=True)
        
        # Remove the temporary metadata field for storage in the collection
        del example_object["metadata"]
        
        # Add to collection
        all_examples.append(example_object)
        
        # Periodically save the collection (every 10 examples)
        if len(all_examples) % 10 == 0:
            save_example_collection()
            save_generation_metadata()
        
        logger.info(f"Saved example: {filename} (Quality Score: {quality_score:.1f}, Valid: {is_valid}, Requirements: {', '.join(requirements)})")
        return True
    except Exception as e:
        logger.error(f"Error saving example: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def save_example_collection():
    """Save the entire collection of examples to a JSON file."""
    try:
        # Write atomically: write to a temp file then replace, so a crash
        # mid-write cannot corrupt the existing collection file.
        tmp_path = EXAMPLE_COLLECTION_FILE + ".tmp"
        with open(tmp_path, 'w', encoding="utf-8") as f:
            json.dump(all_examples, f, indent=2)
        os.replace(tmp_path, EXAMPLE_COLLECTION_FILE)
        logger.info(f"Saved example collection with {len(all_examples)} examples")
        return True
    except Exception as e:
        logger.error(f"Error saving example collection: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def save_generation_metadata():
    """Save comprehensive metadata about the generation process."""
    try:
        # Calculate overall statistics
        complexity_counts = {}
        category_counts = {}
        subcategory_counts = {}
        quality_scores = []
        valid_count = 0
        invalid_count = 0
        hardware_count = 0
        software_count = 0
        
        for example in all_examples:
            # Complexity distribution
            complexity = example["complexity"]
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            
            # Category distribution
            category = example["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Subcategory distribution
            subcategory = example["subcategory"]
            key = f"{category}_{subcategory}"
            subcategory_counts[key] = subcategory_counts.get(key, 0) + 1
            
            # Quality scores
            quality_scores.append(example.get("quality_score", 0))
            
            # Valid/invalid counts
            if example.get("is_valid", False):
                valid_count += 1
            else:
                invalid_count += 1
                
            # Hardware/software counts
            if example.get("is_hardware", False):
                hardware_count += 1
            elif example.get("is_software", False):
                software_count += 1
        
        # Create comprehensive metadata object
        metadata = {
            "generation_info": {
                "timestamp": CURRENT_TIME,
                "user": CURRENT_USER,
                "total_examples": len(all_examples),
                "valid_examples": valid_count,
                "invalid_examples": invalid_count,
                "hardware_examples": hardware_count,
                "software_examples": software_count,
                "execution_time": EXECUTION_TIME,
                "output_directory": os.path.abspath(OUTPUT_DIR)
            },
            "configuration": {
                "total_target_examples": TOTAL_EXAMPLES,
                "code_length_limits": CODE_LENGTH_LIMITS,
                "complexity_distribution_target": TARGET_COMPLEXITY_DISTRIBUTION,
                "min_quality_score": MIN_QUALITY_SCORE,
                "max_correction_attempts": MAX_CORRECTION_ATTEMPTS,
                "api_settings": {
                    "base_delay": BASE_DELAY,
                    "jitter": JITTER,
                    "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
                    "max_retries": MAX_RETRIES
                }
            },
            "statistics": {
                "complexity_distribution": complexity_counts,
                "category_distribution": category_counts,
                "subcategory_counts": subcategory_counts,
                "quality_scores": {
                    "average": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                    "min": min(quality_scores) if quality_scores else 0,
                    "max": max(quality_scores) if quality_scores else 0
                },
                "frequent_errors": dict(error_tracker)
            },
            "library_usage": {
                "standard_libraries_available": len(STANDARD_LIBRARIES_FLAT),
                "categories_available": list(CATEGORIES.keys()),
                "total_subcategories": sum(len(subcats) for subcats in CATEGORIES.values()),
                "hardware_categories": HARDWARE_CATEGORIES,
                "software_categories": SOFTWARE_CATEGORIES
            }
        }
        
        # Save to file atomically: write to a temp file then replace, so a
        # crash mid-write cannot corrupt the existing metadata file.
        tmp_path = METADATA_FILE + ".tmp"
        with open(tmp_path, 'w', encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        os.replace(tmp_path, METADATA_FILE)

        logger.info(f"Saved generation metadata to {METADATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving generation metadata: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def create_task_list():
    """Create a list of tasks for code generation with GUARANTEED multiple examples per combination."""
    logger.info(f"Creating guaranteed task list with exactly {TOTAL_EXAMPLES} examples")
    
    # First, get all valid combinations
    base_combinations = []
    
    for category, subcategories in CATEGORIES.items():
        for subcategory in subcategories:
            for complexity in COMPLEXITY_LEVELS:
                # Skip invalid combinations
                if category == "beginner_basic" and complexity != "beginner_basic":
                    continue
                    
                base_combinations.append((category, subcategory, complexity))
    
    # IMPROVED: Guaranteed approach - cycle through combinations until we have enough
    all_tasks = []
    example_id = 1
    
    # Multiply each combination until we have enough examples
    while len(all_tasks) < TOTAL_EXAMPLES:
        # Use modulo to cycle through combinations
        idx = (len(all_tasks) % len(base_combinations))
        category, subcategory, complexity = base_combinations[idx]
        
        all_tasks.append((category, subcategory, complexity, f"{example_id:04d}"))
        example_id += 1
    
    # Shuffle to randomize the order
    random.shuffle(all_tasks)
    
    # Double-check we have exactly the right number
    logger.info(f"Created task list with exactly {len(all_tasks)} examples")
    
    # Convert to the format expected by the generator
    simplified_tasks = [(category, subcategory, example_id) 
                        for category, subcategory, _, example_id in all_tasks]
    
    # Store the complexity mapping for later use
    complexity_map = {example_id: complexity
                     for category, subcategory, complexity, example_id in all_tasks}

    return simplified_tasks, complexity_map

def generate_example(category, subcategory, example_id, complexity, prompt_generator, code_generator, progress_manager, prompt_standardizer, code_validator, api_client):
    """Generate a single code example using enhanced validation."""
    
    # Skip if already completed
    if progress_manager.is_completed(example_id):
        logger.info(f"Skipping already completed example {example_id}")
        return True

    # If complexity is not specified, select based on category and distribution
    if complexity is None:
        if category == "beginner_basic":
            # For beginner_basic category, always use beginner_basic complexity
            complexity = "beginner_basic"
        else:
            # For other categories, use weighted random selection
            complexity = random.choices(
                list(TARGET_COMPLEXITY_DISTRIBUTION.keys()),
                weights=list(TARGET_COMPLEXITY_DISTRIBUTION.values()),
                k=1
            )[0]
    
    # Randomly select parameters for variation
    style = random.choice(CODE_STYLES)
    pi_model = random.choice(PI_MODELS)
    integration = "standalone" if complexity == "beginner_basic" else random.choice(INTEGRATION_PATTERNS)
    
    # For beginner_basic, use more educational contexts
    if complexity == "beginner_basic":
        beginner_contexts = ["educational setting", "classroom demonstration", "beginner tutorial", 
                            "kids coding lesson", "STEM education", "hobbyist project"]
        context = random.choice(beginner_contexts)
    else:
        context = random.choice(USE_CONTEXTS)
    
    # Prepare metadata with enhanced context awareness
    metadata = {
        "id": example_id,
        "category": category,
        "subcategory": subcategory,
        "complexity": complexity,
        "style": style,
        "pi_model": pi_model,
        "integration": integration,
        "context": context,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "correction_attempts": 0,
        "is_hardware": category in HARDWARE_CATEGORIES,
        "is_software": category in SOFTWARE_CATEGORIES
    }
    
    # Stage 1: Generate AI-created prompt
    logger.info(f"Generating AI prompt for {category}/{subcategory} (complexity: {complexity})")
    ai_prompt = prompt_generator.generate_ai_prompt(
        category, subcategory, complexity, style, pi_model, integration, context
    )
    
    if not ai_prompt:
        logger.error("Failed to generate AI prompt")
        return False
    
    # Save the generated prompt for reference
    metadata["generated_prompt"] = ai_prompt
    
    # Stage 2: Generate the actual code using the AI-created prompt
    logger.info(f"Generating code based on AI prompt (complexity: {complexity})")
    code, _ = code_generator.generate_code(ai_prompt, metadata)
    
    if not code:
        logger.error("Failed to generate valid code")
        return False
    
    # Stage 3: Comprehensive validation and correction loop
    is_valid = False
    validation_details = {}
    correction_attempts = 0
    
    while correction_attempts < MAX_CORRECTION_ATTEMPTS:
        # Run comprehensive validation with context awareness
        is_valid, validation_details, error_messages = validate_code_comprehensive(
            code, category, subcategory, complexity, code_validator, STANDARD_LIBRARIES_FLAT
        )
        
        # If valid, break the loop
        if is_valid:
            logger.info(f"Code passed all validations after {correction_attempts} correction attempts")
            break
        
        # Log validation issues
        logger.info(f"Validation issues (attempt {correction_attempts + 1}/{MAX_CORRECTION_ATTEMPTS}):")
        for error in error_messages:
            logger.info(f"  - {error}")
        
        # Determine primary error type
        primary_error_type = "quality"  # Default
        if not validation_details.get("syntax_valid", True):
            primary_error_type = "syntax"
        elif not validation_details.get("imports_valid", True):
            primary_error_type = "import"
        elif not validation_details.get("length_valid", True):
            primary_error_type = "length"
        elif validation_details.get("pylint_score") is not None and validation_details.get("pylint_score") < 6.0:
            primary_error_type = "pylint"
        
        # Send code for correction with context awareness
        corrected_code = send_code_for_correction(
            code, error_messages, ai_prompt,
            category, subcategory, complexity, primary_error_type, api_client
        )
        
        # Update metadata with correction attempt
        correction_attempts += 1
        metadata["correction_attempts"] = correction_attempts
        
        # If correction failed or no changes made, break the loop
        if not corrected_code or corrected_code == code:
            logger.warning(f"Correction failed or no changes made (attempt {correction_attempts}/{MAX_CORRECTION_ATTEMPTS})")
            break
        
        # Update code for next validation iteration
        code = corrected_code
        
        # If we've reached max attempts, break the loop
        if correction_attempts >= MAX_CORRECTION_ATTEMPTS:
            logger.warning(f"Max correction attempts ({MAX_CORRECTION_ATTEMPTS}) reached")
            break
    
    # Generate standardized prompt if enabled
    if prompt_standardizer:
        logger.info(f"Generating standardized prompt for {category}/{subcategory}")
        standardized_prompt = prompt_standardizer.standardize_prompt(ai_prompt, code)
        metadata["standardized_prompt"] = standardized_prompt or "Failed to generate standardized prompt"
    
    # Save the example with metadata
    return save_example(code, metadata, code_generator, progress_manager, validation_details, is_valid)

def verify_runtime_environment():
    """Verify that the runtime environment has all necessary packages."""
    required_packages = ["tqdm", "requests"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning(f"Missing required packages: {', '.join(missing_packages)}")
        logger.warning(f"Please install them using: pip install {' '.join(missing_packages)}")
        return False
    
    # Check for valid API keys
    if all(key == "" or key == "YOUR_API_KEY_HERE" for key in API_KEYS):
        logger.error("No valid API keys found. Please update API_KEYS with your actual API keys.")
        return False
        
    return True

def generate_examples(api_client, prompt_generator, code_generator, progress_manager, prompt_standardizer, code_validator, reset=False):
    """Main function to orchestrate the generation process with enhanced validation."""
    logger.info(f"Starting generation of {TOTAL_EXAMPLES} Raspberry Pi code examples with enhanced validation")
    
    # First test the API connection
    if not api_client.test_api_connection():
        return
    
    # Initialize progress tracking
    progress_manager.initialize(reset=reset)
    
    # Create the task list with all complexity combinations
    tasks, complexity_map = create_task_list()
    logger.info(f"Created task list with {len(tasks)} examples")
    
    # Setup progress tracking
    successful = 0
    failed = 0
    
    # Process tasks
    start_time = time.time()
    remaining_tasks = [task for task in tasks if not progress_manager.is_completed(task[2])]
    
    # Initialize progress bar
    pbar = tqdm(total=len(remaining_tasks), desc="Generating examples")
    
    # Process tasks
    for i, (category, subcategory, example_id) in enumerate(remaining_tasks):
        logger.info(f"Generating example {i+1}/{len(remaining_tasks)}: {category}/{subcategory} (ID: {example_id})")
        
        # Get assigned complexity from complexity map
        complexity = complexity_map.get(example_id)
        
        if generate_example(
            category, subcategory, example_id, complexity, 
            prompt_generator, code_generator, progress_manager, 
            prompt_standardizer, code_validator, api_client
        ):
            successful += 1
        else:
            failed += 1
        
        # Update progress bar
        pbar.update(1)
        pbar.set_description(f"Generated: {successful}, Failed: {failed}")
        
        # Calculate and display ETA
        elapsed = time.time() - start_time
        avg_time_per_item = elapsed / (i + 1) if i > 0 else 0
        remaining_items = len(remaining_tasks) - (i + 1)
        eta_seconds = avg_time_per_item * remaining_items
        
        if i % 10 == 0 and i > 0:
            eta_hours = int(eta_seconds // 3600)
            eta_minutes = int((eta_seconds % 3600) // 60)
            logger.info(f"Progress: {i+1}/{len(remaining_tasks)} examples. Estimated time remaining: {eta_hours}h {eta_minutes}m")
            
    pbar.close()
    
    # Final report
    end_time = time.time()
    total_time = end_time - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)
    
    logger.info(f"Generation complete: {successful} successful, {failed} failed")
    logger.info(f"Total execution time: {hours}h {minutes}m {seconds}s")
    logger.info(f"Examples saved in {os.path.abspath(OUTPUT_DIR)}")
    
    # Save final collection
    save_example_collection()
    save_generation_metadata()

def main():
    """Main entry point with command-line argument parsing."""
    # Declare globals at the beginning of the function
    global TOTAL_EXAMPLES, OUTPUT_DIR, MIN_QUALITY_SCORE, MAX_CORRECTION_ATTEMPTS

    parser = argparse.ArgumentParser(description="Raspberry Pi Code Example Generator")
    parser.add_argument("--reset", action="store_true", help="Reset progress and start from beginning")
    parser.add_argument("--examples", type=int, default=TOTAL_EXAMPLES, help="Number of examples to generate")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Directory to save examples")
    parser.add_argument("--report-only", action="store_true", help="Generate a report without creating new examples")
    parser.add_argument("--quality-threshold", type=int, default=MIN_QUALITY_SCORE, help="Minimum quality score for valid examples")
    parser.add_argument("--max-correction-attempts", type=int, default=MAX_CORRECTION_ATTEMPTS, help="Maximum attempts to correct code")
    
    # Parse only known args to avoid issues if run in Jupyter
    args, unknown = parser.parse_known_args()
    
    # Update global settings from arguments
    TOTAL_EXAMPLES = args.examples
    OUTPUT_DIR = args.output_dir
    MIN_QUALITY_SCORE = args.quality_threshold
    MAX_CORRECTION_ATTEMPTS = args.max_correction_attempts
    
    # Initialize metadata files with updated OUTPUT_DIR
    initialize_metadata_files()
    
    logger.info("=" * 80)
    logger.info(f"Raspberry Pi Code Examples Generator with Context-Aware Validation")
    logger.info(f"Current Date and Time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Current User's Login: {CURRENT_USER}")
    logger.info(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
    logger.info(f"Target examples: {TOTAL_EXAMPLES}")
    logger.info(f"Minimum quality score: {MIN_QUALITY_SCORE}")
    logger.info(f"Maximum correction attempts: {MAX_CORRECTION_ATTEMPTS}")
    logger.info("=" * 80)
    
    # Verify environment
    if not verify_runtime_environment():
        logger.warning("Environment check failed. Continuing anyway...")
    
    try:
        # Initialize components
        api_client = APIClient(API_KEYS, max_requests_per_minute=MAX_REQUESTS_PER_MINUTE, max_output_tokens=MAX_OUTPUT_TOKENS)
        
        # Initialize code validator
        code_validator = CodeValidator(
            standard_libraries_flat=STANDARD_LIBRARIES_FLAT,
            code_length_limits=CODE_LENGTH_LIMITS,
            use_pylint=False  # We handle pylint separately
        )
        
        # Initialize progress manager
        progress_manager = ProgressManager(
            output_dir=OUTPUT_DIR,
            total_examples=TOTAL_EXAMPLES
        )
        
        # Initialize prompt generator
        prompt_generator = PromptGenerator(
            categories_dict=CATEGORIES,
            standard_libraries=STANDARD_LIBRARIES_FLAT,
            code_length_limits=CODE_LENGTH_LIMITS,
            api_client=api_client
        )
        
        # Initialize code generator
        code_generator = CodeGenerator(
            api_client=api_client,
            code_validator=code_validator,
            output_dir=OUTPUT_DIR,
            max_retries=MAX_RETRIES,
            debug_dir=DEBUG_DIR,
            invalid_dir=INVALID_DIR
        )
        
        # Initialize prompt standardizer
        prompt_standardizer = PromptStandardizer(api_client=api_client)
        
        if args.report_only:
            # Just generate a report based on existing progress
            progress_manager.initialize(reset=False)
            progress_manager.generate_report()
            save_generation_metadata()
        else:
            # Generate examples
            generate_examples(
                api_client=api_client,
                prompt_generator=prompt_generator,
                code_generator=code_generator,
                progress_manager=progress_manager,
                prompt_standardizer=prompt_standardizer,
                code_validator=code_validator,
                reset=args.reset
            )
            
            # Generate final report
            progress_manager.generate_report()
            
        logger.info("Script completed successfully!")
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user. Saving examples generated so far...")
        save_example_collection()
        save_generation_metadata()
        logger.info(f"Saved {len(all_examples)} examples before exiting.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        # Try to save examples if any were generated
        if all_examples:
            logger.info("Attempting to save examples generated before error...")
            save_example_collection()
            save_generation_metadata()
    
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()