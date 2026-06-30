"""Deterministic tests for the Raspberry Pi code-generation pipeline.
Covers the parts that run without network/API: the DKB (taxonomy + whitelist + blacklist),
the validator (syntax / blacklist / quality), and the markdown fence extractor.
"""
import os, sys, tempfile
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import dkb as ld
from validation import CodeValidator


# ----------------------------- DKB / blacklist ----------------------------- #
def test_blacklist_exists_and_is_a_set():
    assert isinstance(ld.DISALLOWED_LIBRARIES, set)
    assert len(ld.DISALLOWED_LIBRARIES) >= 10

def test_is_disallowed_flags_deprecated_and_hallucinated():
    assert ld.is_disallowed("Adafruit_DHT") is True       # deprecated
    assert ld.is_disallowed("rpi_hardware") is True        # hallucinated
    assert ld.is_disallowed("Adafruit_DHT.common") is True # top-level match
    assert ld.is_disallowed("adafruit_dht") is False       # modern replacement is allowed
    assert ld.is_disallowed("RPi.GPIO") is False
    assert ld.is_disallowed("") is False

def test_aliases_suggest_modern_replacements():
    assert ld.LIBRARY_ALIASES.get("Adafruit_DHT") == "adafruit_dht"

def test_no_nonascii_dashes_in_dkb():
    src = open(os.path.join(HERE, "dkb.py"), encoding="utf-8").read()
    for bad in ["‐", "‑", "‒", "–", "—", "−"]:
        assert bad not in src, f"non-ASCII dash {bad!r} still present"
    assert "e-ink" in src

def test_whitelist_flat_is_deduped():
    flat = ld.STANDARD_LIBRARIES_FLAT
    assert len(flat) == len(set(flat))

def test_length_limits_keyed_by_complexity():
    for k in ("beginner_basic", "beginner", "intermediate", "advanced"):
        assert k in ld.CODE_LENGTH_LIMITS

def test_categories_have_subcategories():
    assert ld.CATEGORIES
    for cat, subs in ld.CATEGORIES.items():
        assert isinstance(subs, list) and subs, f"{cat} has no subcategories"

def test_dkb_self_consistency():
    ok, issues = ld.validate_dkb()
    assert ok, f"DKB inconsistent: {issues}"

def test_board_specs_cover_all_models():
    for model in ld.PI_MODELS:
        spec = ld.get_board_spec(model)
        assert spec and "soc" in spec, f"no board spec for {model}"

def test_gpio_and_whitelist_helpers():
    assert ld.valid_gpio_pin(17) and not ld.valid_gpio_pin(40) and not ld.valid_gpio_pin("x")
    assert ld.is_allowed("RPi.GPIO") and ld.is_allowed("gpiozero")
    assert not ld.is_allowed("totally_made_up_pkg")


# ------------------------------ validator ---------------------------------- #
@pytest.fixture
def validator():
    return CodeValidator(
        standard_libraries_flat=ld.STANDARD_LIBRARIES_FLAT,
        code_length_limits=ld.CODE_LENGTH_LIMITS,
        use_pylint=False,
    )

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

def test_valid_example_passes(validator):
    is_valid, errors, details = validator.validate(GOOD_LED, "actuators", "LED", "beginner")
    assert is_valid is True, f"expected valid; errors={errors}"
    assert isinstance(details.get("quality_score"), (int, float))

def test_syntax_error_is_rejected(validator):
    bad = "import RPi.GPIO as GPIO\ndef f(:\n    pass\n"  # invalid syntax
    is_valid, errors, details = validator.validate(bad, "actuators", "LED", "beginner")
    assert is_valid is False
    assert any("synt" in e.lower() for e in errors)

def test_blacklisted_import_is_rejected(validator):
    code = GOOD_LED.replace("import time  # timing helper",
                            "import time  # timing helper\nimport Adafruit_DHT  # deprecated")
    is_valid, errors, details = validator.validate(code, "actuators", "LED", "beginner")
    # must be flagged with a blacklist/deprecated message...
    assert any(("blacklist" in e.lower() or "deprecated" in e.lower()) for e in errors), \
        f"blacklist not flagged; errors={errors}"
    # ...and must actually make the example invalid (enforcement, not just a note)
    assert is_valid is False, f"blacklisted import must reject the example; errors={errors}"

def test_quality_score_is_numeric_in_range(validator):
    _, _, details = validator.validate(GOOD_LED, "actuators", "LED", "beginner")
    qs = details.get("quality_score")
    assert qs is not None and 0 <= qs <= 100, f"quality_score={qs}"


# ------------------------- fence extraction -------------------------------- #
@pytest.fixture
def gen():
    from code_generator import CodeGenerator
    d = tempfile.mkdtemp()
    return CodeGenerator(api_client=None, code_validator=None, output_dir=d)

@pytest.mark.parametrize("raw,expected_contains", [
    ("```python\nprint('hi')\n```", "print('hi')"),
    ("```py\nimport os\n```", "import os"),
    ("```\nx = 1\n```", "x = 1"),
    ("```python import sys```", "import sys"),          # no newline after tag
    ("Here is code:\n```python\na=2\n```\nThanks!", "a=2"),  # surrounding prose
    ("import time\nprint(1)", "print(1)"),               # raw, no fence
])
def test_extract_code_handles_fence_variants(gen, raw, expected_contains):
    out = gen.extract_code(raw)
    assert expected_contains in out
    assert "```" not in out
