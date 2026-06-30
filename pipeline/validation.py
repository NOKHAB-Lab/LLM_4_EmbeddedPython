"""
Raspberry Pi Code Validator Module
Provides comprehensive validation for generated code examples
Created: 2025-03-24 12:19:44
Author: Sakkibbb
"""

import re
import os
import io
import logging
import subprocess
import tempfile
import tokenize
import json
from typing import Dict, List, Tuple, Optional, Any, Union

from dkb import is_disallowed, LIBRARY_ALIASES

# Configure logging
logger = logging.getLogger(__name__)

class CodeValidator:
    """Advanced code validator with multiple validation strategies"""
    
    def __init__(self, 
                 standard_libraries_flat: List[str],
                 code_length_limits: Dict[str, int],
                 use_pylint: bool = True,
                 use_advanced_validation: bool = True):
        """
        Initialize the code validator.
        
        Args:
            standard_libraries_flat: List of allowed standard libraries
            code_length_limits: Dict mapping complexity levels to code length limits
            use_pylint: Whether to use pylint for validation
            use_advanced_validation: Whether to use advanced validation techniques
        """
        self.standard_libraries_flat = standard_libraries_flat
        self.code_length_limits = code_length_limits
        self.use_pylint = use_pylint
        self.use_advanced_validation = use_advanced_validation
        
        # Pi-related import terms for validation. Matched as whole tokens
        # (word boundaries) to avoid false positives like 'spider' (spi),
        # 'api' (pi), 'serial_number' (serial), 'pi=3.14' (pi).
        self.pi_related_imports = [
            "RPi", "GPIO", "gpiozero", "picamera", "smbus",
            "adafruit", "board", "busio", "digitalio",
            # Additional keywords that might indicate Pi code
            "serial", "i2c", "spi", "mqtt", "raspberry",
            "rpi", "pi"
        ]
        
        # Initialize quality metrics
        self.quality_metrics = {
            "docstrings": 0,
            "error_handling": 0,
            "clean_shutdown": 0,
            "main_guard": 0,
            "function_structure": 0,
            "comments": 0,
            "variable_naming": 0,
            "category_specific": 0
        }
        
    @staticmethod
    def _extract_comments(code: str) -> List[str]:
        """Return the list of real comment strings using the tokenize module so
        that '#' characters inside string literals are not counted. Falls back
        to a naive regex scan if tokenizing the snippet fails."""
        comments = []
        try:
            tokens = tokenize.generate_tokens(io.StringIO(code).readline)
            for tok in tokens:
                if tok.type == tokenize.COMMENT:
                    comments.append(tok.string)
            return comments
        except Exception:
            # Fall back to the old (less accurate) behavior on tokenize failure.
            return re.findall(r'#[^\n]*', code)

    @classmethod
    def _count_comments(cls, code: str) -> int:
        """Count only real comment tokens (not '#' inside strings)."""
        return len(cls._extract_comments(code))

    def validate(self, code: str, category: str, subcategory: str, complexity: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate code against multiple criteria.
        
        Args:
            code: The code to validate
            category: The category of the example
            subcategory: The subcategory of the example
            complexity: The complexity level of the example
        
        Returns:
            Tuple containing:
              - Whether the code is valid
              - List of validation errors
              - Dict of validation details and metrics
        """
        validation_errors = []
        validation_details = {
            "basic_validation": False,
            "syntax_validation": False,
            "import_validation": False,
            "structure_validation": False,
            "pylint_validation": None,
            "quality_score": 0,
            "line_count": 0,
            "quality_metrics": {},
            "pylint_score": None,
            "pylint_messages": []
        }
        
        # Skip empty code
        if not code or len(code.strip()) == 0:
            validation_errors.append("Empty code")
            return False, validation_errors, validation_details
            
        # Basic validation (length, etc.)
        is_valid_basic, basic_errors = self._validate_basic(code, complexity)
        validation_details["basic_validation"] = is_valid_basic
        validation_errors.extend(basic_errors)
        
        # Line count
        line_count = len(code.strip().split('\n'))
        validation_details["line_count"] = line_count
        
        # Syntax validation
        is_valid_syntax, syntax_errors = self._validate_syntax(code)
        validation_details["syntax_validation"] = is_valid_syntax
        validation_errors.extend(syntax_errors)
        
        # If syntax is invalid, skip further validation
        if not is_valid_syntax:
            return False, validation_errors, validation_details
        
        # Import validation
        is_valid_imports, import_errors, custom_imports, has_blacklisted_import = self._validate_imports(code)
        validation_details["import_validation"] = is_valid_imports
        validation_errors.extend(import_errors)
        validation_details["custom_imports"] = custom_imports
        validation_details["has_blacklisted_import"] = has_blacklisted_import
        
        # Raspberry Pi specific validation
        is_valid_pi, pi_errors = self._validate_pi_specific(code, category, subcategory)
        validation_errors.extend(pi_errors)
        
        # Structure validation
        is_valid_structure, structure_errors = self._validate_structure(code, complexity)
        validation_details["structure_validation"] = is_valid_structure
        validation_errors.extend(structure_errors)
        
        # Advanced validation with pylint if enabled
        if self.use_pylint:
            pylint_score, pylint_errors, pylint_messages = self._validate_with_pylint(code)
            validation_details["pylint_score"] = pylint_score
            validation_details["pylint_messages"] = pylint_messages
            if pylint_score is None:
                # Pylint unavailable / tooling failure: treat as neutral (skip),
                # do not count it as passing perfectly.
                validation_details["pylint_validation"] = None
            else:
                validation_details["pylint_validation"] = pylint_score >= 5.0  # Consider valid if score is at least 5.0
                if pylint_score < 5.0:
                    validation_errors.append(f"Low pylint score: {pylint_score}/10.0")
        
        # Quality assessment
        quality_passed, quality_score, metrics = self._assess_quality(code, category, complexity)
        validation_details["quality_score"] = quality_score
        validation_details["quality_metrics"] = metrics
        
        # Determine overall validity.
        # Code must pass basic, syntax, Pi-specific, and structure checks, and
        # must NOT import any blacklisted (deprecated/wrong-platform/hallucinated)
        # library. Non-whitelisted/custom third-party imports stay advisory only
        # and do not gate validity (avoids over-rejecting legitimate libraries).
        is_valid = (
            is_valid_basic
            and is_valid_syntax
            and is_valid_pi
            and is_valid_structure
            and not has_blacklisted_import
        )

        return is_valid, validation_errors, validation_details
    
    def _validate_basic(self, code: str, complexity: str) -> Tuple[bool, List[str]]:
        """Validate basic aspects of the code (length, etc.)"""
        errors = []
        
        # Get line count
        line_count = len(code.strip().split('\n'))
        
        # Check if code is empty or too short based on complexity
        min_length = 30 if complexity == "beginner_basic" else 100
        if not code or len(code) < min_length:
            errors.append(f"Code too short ({len(code) if code else 0} chars)")
        
        # Check line count for specific complexity levels
        max_line_count = self.code_length_limits.get(complexity, 200)

        if complexity == "beginner_basic" and line_count > 60:
            errors.append(f"beginner_basic code is too long ({line_count} lines, should be <= 40 lines)")
        elif complexity == "beginner" and line_count > max_line_count * 1.2:
            errors.append(f"beginner code is too long ({line_count} lines, should be around {max_line_count})")
        elif complexity == "intermediate" and line_count > max_line_count * 2.0:
            errors.append(f"intermediate code is too long ({line_count} lines, should be around {max_line_count})")
        elif complexity == "advanced" and line_count > max_line_count * 2.0:
            errors.append(f"advanced code is too long ({line_count} lines, should be around {max_line_count})")

        # Check for comments and documentation - different thresholds based on complexity
        min_comments = 3 if complexity == "beginner_basic" else 5
        comment_count = self._count_comments(code)
        if comment_count < min_comments:
            errors.append(f"Insufficient comments (found {comment_count}, needed {min_comments})")

        return len(errors) == 0, errors
    
    def _validate_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """Validate Python syntax"""
        errors = []
        
        # Check Python syntax
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            errors.append(f"Syntax error - {str(e)}")
        
        return len(errors) == 0, errors
    
    def _validate_imports(self, code: str) -> Tuple[bool, List[str], List[str], bool]:
        """Validate imports to ensure they're using standard libraries.

        Returns (is_valid, errors, custom_imports, has_blacklisted_import).
        Blacklisted imports are deprecated/hallucinated/wrong-platform libs and
        are tracked separately from merely non-whitelisted/custom imports so that
        the caller can hard-reject blacklisted code while keeping custom imports
        advisory only.
        """
        errors = []
        custom_imports = []
        has_blacklisted_import = False

        # Collect every imported module name. Two regex passes:
        #   'from X import ...' -> X
        #   'import A, B.c, D'  -> each comma-separated target (split clause)
        imported_modules = []
        for imp_from in re.findall(r'from\s+([a-zA-Z0-9_.]+)\s+import', code):
            imported_modules.append(imp_from)
        for imp_clause in re.findall(r'(?m)^\s*import\s+(.+)$', code):
            # Strip trailing comments and split on commas so a blacklisted
            # module in 2nd+ position (e.g. 'import os, Adafruit_DHT') is seen.
            imp_clause = imp_clause.split('#', 1)[0]
            for part in imp_clause.split(','):
                part = part.strip()
                if not part:
                    continue
                # Drop any 'as alias' suffix, keep the module path only.
                mod = part.split(' as ')[0].strip()
                if mod:
                    imported_modules.append(mod)

        for imp in imported_modules:
            if not imp:
                continue
            # Enforce the blacklist of deprecated/hallucinated/wrong-platform libs
            if is_disallowed(imp):
                has_blacklisted_import = True
                mod = imp.split('.')[0]
                replacement = LIBRARY_ALIASES.get(mod) or LIBRARY_ALIASES.get(imp)
                msg = f"Blacklisted/deprecated library: {mod}"
                if replacement:
                    msg += f" (use {replacement} instead)"
                errors.append(msg)
                continue
            # Check if import is in our flattened standard libraries list
            if not any(imp == std_lib or imp.startswith(f"{std_lib}.") for std_lib in self.standard_libraries_flat):
                # Also check if it might be a submodule of any standard library
                is_submodule = False
                for std_lib in self.standard_libraries_flat:
                    if '.' in std_lib and imp.startswith(std_lib.split('.')[0]):
                        is_submodule = True
                        break
                if not is_submodule:
                    custom_imports.append(imp)

        if custom_imports:
            errors.append(f"Custom module imports found: {', '.join(custom_imports)}")

        return len(errors) == 0, errors, custom_imports, has_blacklisted_import
    
    def _validate_pi_specific(self, code: str, category: str, subcategory: str) -> Tuple[bool, List[str]]:
        """Validate Raspberry Pi specific aspects of the code"""
        errors = []
        
        # Check if code contains imports/keywords relevant to Raspberry Pi.
        # Match on whole tokens (word boundaries, case-insensitive) so bare
        # substrings like 'spi'/'pi'/'serial' don't match inside unrelated words
        # such as 'spider', 'api', or 'serial_number'.
        pi_pattern = re.compile(
            r"\b(" + "|".join(re.escape(term) for term in self.pi_related_imports) + r")\b",
            re.IGNORECASE,
        )
        has_pi_imports = bool(pi_pattern.search(code))
        if not has_pi_imports:
            errors.append("No Raspberry Pi related imports or keywords found")
        
        # Check if code mentions the subcategory
        if subcategory.lower() not in code.lower():
            # Try checking with spaces and underscores replaced
            subcategory_alt = subcategory.lower().replace(" ", "_")
            subcategory_alt2 = subcategory.lower().replace(" ", "")
            if subcategory_alt not in code.lower() and subcategory_alt2 not in code.lower():
                errors.append(f"Subcategory '{subcategory}' not found in code")
        
        return len(errors) == 0, errors
    
    def _validate_structure(self, code: str, complexity: str) -> Tuple[bool, List[str]]:
        """Validate code structure (functions, classes, etc.)"""
        errors = []
        
        # For non-beginner_basic, check for proper structure
        if complexity != "beginner_basic":
            # Check for main guard
            if not re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', code):
                errors.append("No '__main__' guard found")
            
            # Check for proper function definitions
            funcs = re.findall(r'def\s+\w+\([^)]*\):', code)
            if complexity in ["intermediate", "advanced"] and len(funcs) < 2:
                errors.append(f"Expected multiple functions for {complexity} code, found {len(funcs)}")
        
        # For advanced, check for proper class definitions
        if complexity == "advanced" and "class " not in code:
            errors.append("Expected class definitions in advanced code")
        
        return len(errors) == 0, errors
    
    def _validate_with_pylint(self, code: str) -> Tuple[Optional[float], List[str], List[Dict[str, Any]]]:
        """Validate code with pylint.

        Returns a real score (0.0-10.0) when pylint runs and a score can be
        computed. Returns None when pylint is unavailable or fails as a tool
        (meaning "unknown/skip"), rather than silently reporting a perfect score.
        """
        errors = []
        pylint_messages = []
        pylint_score = None

        try:
            # Create a temporary file with the code
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(code.encode())
            
            # Run pylint on the temporary file
            # Disable certain warnings that are not relevant for examples
            cmd = [
                'pylint', 
                '--disable=C0111,C0103,C0303,W0311,W0312,C0301,C0305,C0304,C0116',  # Disable formatting checks
                '--output-format=json',
                temp_file_path
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            # Extract score and messages
            if stdout:
                try:
                    # Parse JSON output
                    pylint_output = json.loads(stdout.decode())
                    
                    # Extract messages
                    pylint_messages = [
                        {
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "message": msg.get("message", ""),
                            "symbol": msg.get("symbol", ""),
                            "type": msg.get("type", "")
                        }
                        for msg in pylint_output
                    ]
                    
                    # Count error types
                    error_count = sum(1 for msg in pylint_messages if msg["type"] in ["error", "fatal"])
                    warning_count = sum(1 for msg in pylint_messages if msg["type"] == "warning")
                    
                    # Calculate score (10 - deductions)
                    # Each error counts as -1, each warning as -0.5
                    deduction = error_count + warning_count * 0.5
                    pylint_score = max(0.0, min(10.0, 10.0 - deduction))
                    
                except json.JSONDecodeError:
                    # Fallback to simple score extraction if JSON parsing fails
                    score_match = re.search(r'Your code has been rated at ([-\d.]+)/10', stdout.decode())
                    if score_match:
                        pylint_score = float(score_match.group(1))
                    else:
                        errors.append("Failed to extract pylint score")
            
            if stderr:
                errors.append(f"Pylint error: {stderr.decode()}")
                
        except Exception as e:
            errors.append(f"Error running pylint: {str(e)}")
        finally:
            # Clean up temporary file
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        return pylint_score, errors, pylint_messages
    
    def _assess_quality(self, code: str, category: str, complexity: str) -> Tuple[bool, float, Dict[str, float]]:
        """Assess code quality based on various metrics"""
        quality_score = 0

        # Reset metrics
        metrics = {key: 0 for key in self.quality_metrics.keys()}
        
        # Basic checks
        if re.search(r'def\s+\w+\([^)]*\):\s*\n\s*"""', code):  # Docstrings
            quality_score += 10
            metrics["docstrings"] = 1
        
        if 'try:' in code and 'except' in code:  # Error handling
            quality_score += 10
            metrics["error_handling"] = 1
        
        if 'finally:' in code or 'GPIO.cleanup()' in code:  # Clean shutdown
            quality_score += 5
            metrics["clean_shutdown"] = 1
        
        # Structure checks
        if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', code):  # Main guard
            quality_score += 10
            metrics["main_guard"] = 1
        
        # Code complexity
        funcs = re.findall(r'def\s+\w+\([^)]*\):', code)
        if complexity == "beginner_basic":
            if len(funcs) <= 2:  # Simple structure for beginners
                quality_score += 10
                metrics["function_structure"] = 1
        else:
            if len(funcs) >= 2:  # More structured for higher complexities
                quality_score += 10
                metrics["function_structure"] = 1
        
        # Comments quality (count only real comment tokens, not '#' in strings)
        comments = self._extract_comments(code)
        meaningful_comments = sum(1 for c in comments if len(c) > 5)
        if meaningful_comments >= 3:
            quality_score += 10
            metrics["comments"] = meaningful_comments / max(5, len(comments))

        # Variable naming. Avoid penalizing short names only on assignment;
        # the negative lookahead '(?!=)' prevents matching comparisons like
        # 'x ==' or 'i ==' which are not assignments.
        if not re.search(r'\b[a-z]{1,2}\s*=(?!=)', code):  # Avoid single-letter variables
            quality_score += 10
            metrics["variable_naming"] = 1
        
        # Category-specific checks
        if category == "sensors" and re.search(r'read|get|measure', code, re.IGNORECASE):
            quality_score += 5
            metrics["category_specific"] = 1
        elif category == "actuators" and re.search(r'set|control|turn|move', code, re.IGNORECASE):
            quality_score += 5
            metrics["category_specific"] = 1
        elif category == "cameras" and re.search(r'capture|image|photo|frame', code, re.IGNORECASE):
            quality_score += 5
            metrics["category_specific"] = 1
        
        # Beginner basic specific
        if complexity == "beginner_basic":
            threshold = 60  # Lower threshold for beginner_basic
        else:
            threshold = 70
            
        return quality_score >= threshold, quality_score, metrics
        
    def save_invalid_example(self, code: str, category: str, subcategory: str, errors: List[str], 
                            output_dir: str, timestamp: str = None) -> str:
        """Save invalid code examples for inspection."""
        if not code:
            return None
            
        if timestamp is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use first error type for filename
        error_type = str(errors[0]).split(':')[0].replace(' ', '_') if isinstance(errors, list) and errors else "unknown_error"
        filename = f"invalid_{category}_{subcategory}_{error_type}_{timestamp}.py"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write(f"# INVALID EXAMPLE: {category}/{subcategory}\n")
                if isinstance(errors, list):
                    for i, error in enumerate(errors, 1):
                        f.write(f"# ERROR {i}: {error}\n")
                else:
                    f.write(f"# ERROR: {errors}\n")
                f.write(f"# TIMESTAMP: {timestamp}\n\n")
                f.write(code)
            logger.info(f"Saved invalid example for inspection: {filename}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving invalid example: {str(e)}")
            return None

# Functionality test when run directly
if __name__ == "__main__":
    # Simple test with a code snippet
    test_code = """
import RPi.GPIO as GPIO
import time

# Set up GPIO pins
LED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# Blink the LED
try:
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(1)
except KeyboardInterrupt:
    # Clean up
    GPIO.cleanup()
    """
    
    # Create validator with dummy standard libraries
    validator = CodeValidator(
        standard_libraries_flat=["RPi", "RPi.GPIO", "time", "datetime", "os", "sys"],
        code_length_limits={"beginner_basic": 50, "beginner": 100, "intermediate": 150, "advanced": 250},
        use_pylint=True  # Set to True if you have pylint installed
    )
    
    # Validate
    is_valid, errors, details = validator.validate(test_code, "actuators", "LED", "beginner_basic")
    
    print(f"Is valid: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"Quality score: {details['quality_score']}")
    print(f"Line count: {details['line_count']}")