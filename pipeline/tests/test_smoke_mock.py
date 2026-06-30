"""End-to-end smoke test with a MOCK Gemini client (no network/keys).
Exercises generate -> extract -> validate, and the standardizer, integrated."""
import os, sys, tempfile
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import dkb as ld
from validation import CodeValidator
from code_generator import CodeGenerator
from prompt_standardizer import PromptStandardizer

GOOD_LED = '''import time  # timing helper
from gpiozero import LED  # LED control library

# Set up the LED on GPIO pin 17
led = LED(17)

# Blink the LED a fixed number of times
def blink_led():
    # Loop to toggle the LED on and off
    for _ in range(5):
        led.on()   # turn the LED on
        time.sleep(1)
        led.off()  # turn the LED off
        time.sleep(1)

if __name__ == "__main__":
    blink_led()  # run the blink routine
'''


class MockAPIClient:
    """Stand-in for APIClient: returns canned responses, no network."""
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def call_gemini_api(self, prompt, temperature=None):
        self.calls += 1
        return self.response

    def test_api_connection(self):
        return True


def test_generate_code_end_to_end_valid():
    api = MockAPIClient("```python\n" + GOOD_LED + "\n```")
    validator = CodeValidator(ld.STANDARD_LIBRARIES_FLAT, ld.CODE_LENGTH_LIMITS, use_pylint=False)
    gen = CodeGenerator(api, validator, output_dir=tempfile.mkdtemp())
    meta = {"complexity": "beginner", "subcategory": "LED", "category": "actuators",
            "context": "home automation", "pi_model": "Raspberry Pi 4 Model B"}
    code, score = gen.generate_code("Write code that blinks an LED on a Raspberry Pi.", meta)
    assert code is not None, "valid code should be accepted"
    assert "LED" in code and "```" not in code
    assert isinstance(score, (int, float))
    assert api.calls >= 1


def test_generate_code_rejects_unfixable_invalid():
    # mock always returns broken code; with accept_invalid_on_final=False (default),
    # generate_code must return (None, 0) rather than smuggling invalid code through.
    api = MockAPIClient("```python\ndef broken(:\n```")
    validator = CodeValidator(ld.STANDARD_LIBRARIES_FLAT, ld.CODE_LENGTH_LIMITS, use_pylint=False)
    gen = CodeGenerator(api, validator, output_dir=tempfile.mkdtemp(), max_retries=2)
    meta = {"complexity": "beginner", "subcategory": "LED", "category": "actuators",
            "context": "home automation", "pi_model": "Raspberry Pi 4 Model B"}
    code, score = gen.generate_code("Write code that blinks an LED.", meta)
    assert code is None and score == 0


def test_standardizer_collapses_whitespace():
    api = MockAPIClient("Write code that   reads a\n\n temperature   sensor.")
    std = PromptStandardizer(api)
    out = std.standardize_prompt("verbose prompt ...", GOOD_LED)
    assert out is not None
    assert "\n" not in out and "  " not in out  # single-line, collapsed
