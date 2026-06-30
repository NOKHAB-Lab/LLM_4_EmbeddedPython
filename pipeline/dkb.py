"""
Domain Knowledge Base (DKB) for hardware-aware Raspberry Pi Python code generation.

The DKB is the single source of platform-specific knowledge the pipeline depends on:

  1. Task taxonomy        CATEGORIES (functional category -> subcategories) and the
                          COMPLEXITY_LEVELS / PI_MODELS / INTEGRATION_PATTERNS /
                          USE_CONTEXTS / CODE_STYLES dimensions sampled per example.
  2. Library whitelist    STANDARD_LIBRARIES and the flattened STANDARD_LIBRARIES_FLAT:
                          the permitted standard-library and hardware packages.
  3. Library blacklist    DISALLOWED_LIBRARIES: deprecated, wrong-platform, hallucinated,
                          or Python-2-only packages that must not appear in generated
                          code, with LIBRARY_ALIASES mapping each to its modern equivalent.
  4. Per-domain maps      SENSOR_/ACTUATOR_/CAMERA_/IOT_/ML_/BEGINNER_BASIC_LIBRARIES:
                          recommended libraries per subcategory.
  5. Board constraints    BOARD_SPECS and VALID_BCM_GPIO: per-model hardware capabilities
                          and the valid BCM GPIO range on the 40-pin header.

Helper API: is_allowed, is_disallowed, get_domain_libraries, get_board_spec,
valid_gpio_pin, and validate_dkb (a self-consistency check). The public surface is
declared in __all__; importing modules depend only on these names.

Version: see DKB_VERSION.
"""

# ========================= CATEGORY DEFINITIONS ========================= #

CATEGORIES = {
    "sensors": [
        "temperature", "humidity", "pressure", "motion", "distance", "light",
        "sound", "gas", "accelerometer", "gyroscope", "magnetometer", "IR",
        "ultrasonic", "PIR", "vibration", "water level", "soil moisture"
    ],
    "actuators": [
        "servo", "stepper motor", "DC motor", "relay", "solenoid", "LED",
        "buzzer", "speaker", "display", "LCD", "OLED", "e-ink", "RGB LED"
    ],
    "cameras": [
        "picamera", "USB camera", "CSI camera", "thermal camera",
        "security camera", "motion detection", "object detection",
        "facial recognition", "QR code scanner", "time-lapse"
    ],
    "iot_applications": [
        "smart home", "environment monitoring", "remote control",
        "data logging", "automation", "IoT gateway", "MQTT", "webhooks",
        "weather station", "energy monitoring", "home security",
        "smart garden"
    ],
    "ml_applications": [
        "object detection", "image classification", "voice recognition",
        "anomaly detection", "predictive maintenance", "sentiment analysis",
        "natural language processing", "gesture recognition", "TensorFlow Lite", "TinyML"
    ],
    "beginner_basic": [  # very small, didactic examples
        "LED blink", "button input", "temperature reading", "motion detection",
        "light sensing", "buzzer control", "servo control",
        "distance measurement", "LED matrix", "LCD hello world", "DHT sensor",
        "PIR sensor", "relay switch", "RGB LED control",
        "potentiometer reading"
    ],
    # Newly added so helper constants never break
    "robotics": [
        "chassis control", "line following", "obstacle avoidance",
        "arm control", "path planning"
    ],
    "communications": [
        "mqtt", "http", "websocket", "bluetooth", "nfc"
    ],
    "display": [
        "lcd", "oled", "e-ink", "seven segment", "matrix"
    ]
}

# ================= CONTEXTUAL HELPER LISTS (CONSISTENT) ================= #

HARDWARE_CATEGORIES = [
    "sensors", "actuators", "cameras", "robotics", "beginner_basic", "display"
]

SOFTWARE_CATEGORIES = [
    "iot_applications", "ml_applications", "communications"
]

CODE_STYLES = ["basic", "functional", "simple script"]
COMPLEXITY_LEVELS = ["beginner_basic", "beginner", "intermediate", "advanced"]
PI_MODELS = [
    "Raspberry Pi 5", "Raspberry Pi 4 Model B",
    "Raspberry Pi 3 Model B+", "Raspberry Pi Zero W"
]
INTEGRATION_PATTERNS = [
    "standalone", "with multiple actuators", "with camera, sensor",
    "with multiple sensors", "in distributed system"
]

CODE_LENGTH_LIMITS = {
    "beginner_basic": 40,  # lines
    "beginner": 60,
    "intermediate": 100,
    "advanced": 200
}

CATEGORY_LENGTH_ADJUSTMENTS = {
    "iot_applications": 1.5,
    "ml_applications": 1.5,
    "cameras": 1.2,
    "robotics": 1.2,
    "display": 1.15,
    "actuators": 1.1
}

USE_CONTEXTS = [
    "educational setting", "hobbyist project", "professional monitoring system",
    "research application", "industrial automation", "smart agriculture",
    "robotics project", "wearable technology", "interactive art installation",
    "assistive technology", "environmental science", "home automation",
    "small business automation", "clean energy monitoring", "healthcare monitoring",
    "elder care system", "smart retail", "manufacturing quality control",
    "urban monitoring", "wildlife tracking", "STEM education",
    "hydroponics control", "classroom demonstration", "beginner tutorial",
    "kids coding lesson"
]

# ====================== STANDARD LIBRARY DEFINITIONS ===================== #

STANDARD_LIBRARIES = {
    # Core Python std-lib (unchanged)
    "python_std": [
        "os", "sys", "time", "datetime", "subprocess", "platform", "shutil",
        "pathlib", "glob", "fnmatch", "tempfile", "stat", "fileinput",
        "configparser", "argparse", "getopt", "logging", "warnings",
        "json", "csv", "xml", "pickle", "shelve", "marshal", "base64",
        "bz2", "gzip", "zipfile", "tarfile", "hashlib", "hmac", "uuid",
        "itertools", "functools", "operator", "collections", "heapq",
        "bisect", "array", "enum", "dataclasses",
        "threading", "multiprocessing", "concurrent.futures", "queue",
        "asyncio", "contextvars", "sched",
        "math", "cmath", "decimal", "fractions", "random", "statistics",
        "socket", "ssl", "select", "selectors", "signal",
        "urllib", "urllib.request", "urllib.parse", "urllib.error",
        "http", "http.client", "http.server", "ftplib", "poplib",
        "imaplib", "smtplib", "telnetlib", "socketserver",
        "sqlite3", "dbm"
    ],

    # GPIO and Hardware Interface
    "gpio": [
        "RPi.GPIO", "gpiozero", "lgpio", "pigpio",
        "gpiozero.devices", "gpiozero.pins", "gpiozero.tools"
    ],

    # Bus Communication
    "bus": [
        "smbus", "smbus2", "busio", "board",
        "spidev",  # SPI
        "w1thermsensor",  # 1-Wire
        "serial", "pyserial", "serial.tools.list_ports"  # UART/serial
    ],

    # Adafruit (duplicates trimmed)
    "adafruit": [
        "adafruit_blinka", "adafruit_platformdetect", "adafruit_bus_device",
        "adafruit_register", "adafruit_bitbangio", "adafruit_ble",
        "adafruit_displayio_ssd1306", "adafruit_displayio_sh1106",
        "adafruit_displayio_ssd1322", "adafruit_displayio_ssd1325",
        "adafruit_displayio_ssd1327", "adafruit_seesaw.neopixel",
        "adafruit_rgb_display", "adafruit_st7735", "adafruit_st7789",
        "adafruit_ili9341", "adafruit_pcd8544", "adafruit_epd",
        "adafruit_gfx", "adafruit_led_animation", "adafruit_max7219",
        "adafruit_ht16k33", "adafruit_is31fl3731", "adafruit_aw9523",
        "adafruit_display_text", "adafruit_bitmap_font", "adafruit_framebuf",
        "adafruit_ssd1675", "adafruit_il0373",
        # sensor breakout boards
        "adafruit_dht", "adafruit_ds18x20", "adafruit_bme280",
        "adafruit_mpu6050", "adafruit_lsm303_accel", "adafruit_vl53l0x",
        "adafruit_sgp30", "adafruit_motor", "adafruit_motorkit",
        "adafruit_servokit", "adafruit_pca9685", "adafruit_ads1x15",
        "adafruit_pn532", "adafruit_gps"
    ],

    # Camera / Vision
    "camera": [
        "picamera", "picamera2", "libcamera", "cv2", "opencv-python",
        "pillow", "scikit-image", "imageio", "imutils", "mahotas",
        "face_recognition", "pyzbar", "qrcode", "barcode", "pylibdmtx"
    ],

    # Networking / IoT
    "networking": [
        "requests", "aiohttp", "httpx", "urllib3", "beautifulsoup4",
        "flask", "fastapi", "bottle", "django", "tornado",
        "werkzeug", "uvicorn", "gunicorn", "cherrypy", "starlette",
        "websockets", "python-socketio", "dash", "streamlit", "falcon",
        "paho-mqtt", "adafruit_minimqtt", "AWSIoTPythonSDK",
        "azure.iot.device", "google.cloud.iot", "bleak", "adafruit_io",
        "thingspeak", "ubidots", "dweet", "balena", "tuya",
        "openhab", "pyHS100", "homie", "tasmota", "pyowm", "geocoder"
    ],

    # Machine Learning
    "ml": [
        "tensorflow", "tflite_runtime", "tensorflow_hub",
        "tensorflow_datasets", "tensorflow_model_optimization",
        "tensorflow_addons", "torch", "torchvision", "torchaudio",
        "pytorch_lightning", "onnx", "onnxruntime", "scikit-learn",
        "numpy", "pandas", "scipy", "matplotlib", "seaborn", "plotly",
        "xgboost", "lightgbm", "catboost", "librosa", "soundfile",
        "python_speech_features", "mediapipe"
    ],

    # Audio
    "audio": [
        "sounddevice", "pyaudio", "soundfile", "wave", "simpleaudio",
        "pydub", "audioop", "pygame.mixer", "playsound", "python-sonic",
        "librosa", "audioread", "alsaaudio", "gtts", "speechrecognition",
        "pocketsphinx", "webrtcvad", "espeak", "pyfestival"
    ],

    # Display / UI
    "display": [
        "tkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "wxPython",
        "kivy", "pygame", "pyglet", "arcade", "matplotlib.pyplot",
        "guizero", "appjar", "dearpygui", "toga", "pygubu",
        "curses", "urwid", "blessed", "prompt_toolkit", "rich",
        "textual", "asciimatics", "npyscreen", "pytermgui"
    ],

    # Storage / DB
    "storage": [
        "sqlite3", "sqlalchemy", "peewee", "pymongo", "redis",
        "influxdb", "cassandra-driver", "mysql-connector-python",
        "psycopg2", "mariadb", "firebase", "firestore", "lmdb",
        "hdf5storage", "h5py", "tables", "zarr", "xarray"
    ],

    # Embedded / microcontroller tooling
    "embedded": [
        "esptool", "ampy", "rshell", "pyserial", "micropython-deploy",
        "pyFirmata", "pymata", "pyduino", "nanpy", "pyesp32", "pico-sdk",
        "micropython"
    ]
}

# =========== FLATTENED LIST (unique & order-preserving) =========== #

STANDARD_LIBRARIES_FLAT = list(dict.fromkeys(
    lib for libs in STANDARD_LIBRARIES.values() for lib in libs
))

# ======================= BLACKLIST (DISALLOWED LIBS) ======================= #
# Deprecated, unmaintained, wrong-platform, hallucinated, or Python-2-only
# packages that must NOT appear in generated code. Used by the validator to
# reject "plausible but wrong" imports (the whitelist's complement).
DISALLOWED_LIBRARIES = {
    # Deprecated / unmaintained (superseded by modern equivalents)
    "Adafruit_DHT",      # -> adafruit_dht (CircuitPython) or pigpio
    "Adafruit_GPIO",     # -> adafruit_blinka
    "Adafruit_I2C",      # -> adafruit_bus_device / smbus2
    "Adafruit_BBIO",     # BeagleBone, not Raspberry Pi
    "RPIO",              # deprecated RPi.GPIO fork
    "wiringpi", "wiringpi2",  # deprecated / unmaintained
    # Hallucinated / non-existent packages (common LLM inventions)
    "rpi_hardware", "rpihardware", "rpi_gpio", "RPi_GPIO",
    "gpio_zero", "gpiozero_extended",
    "raspberry_pi", "raspberrypi", "pi_camera", "picam",
    "MQ-series", "mq_series", "mqseries",
    # Python-2-only spellings / modules
    "Tkinter", "cPickle", "urllib2", "cStringIO", "Queue", "SocketServer",
}

# Canonical aliases: map a deprecated/alias spelling to its modern replacement
# (advisory; used to suggest a fix in validation messages).
LIBRARY_ALIASES = {
    "Adafruit_DHT": "adafruit_dht",
    "Adafruit_GPIO": "adafruit_blinka",
    "Adafruit_I2C": "smbus2",
    "Tkinter": "tkinter",
    "cPickle": "pickle",
    "urllib2": "urllib.request",
    "Queue": "queue",
}


def is_disallowed(module_name):
    """True if a top-level import is blacklisted. Matches on the top-level
    package (e.g. 'Adafruit_DHT.common' -> 'Adafruit_DHT')."""
    if not module_name:
        return False
    top = module_name.split(".")[0]
    return top in DISALLOWED_LIBRARIES or module_name in DISALLOWED_LIBRARIES


# ===================== TYPE-SPECIFIC LIBRARY MAPS ===================== #

SENSOR_LIBRARIES = {
    "temperature": [
        "adafruit_dht", "adafruit_ds18x20", "adafruit_mcp9808",
        "w1thermsensor", "adafruit_mlx90614"
    ],
    "humidity": [
        "adafruit_dht", "adafruit_sht31d", "adafruit_bme280"
    ],
    "pressure": [
        "adafruit_bmp280", "adafruit_bme280", "adafruit_bmp388"
    ],
    "motion": ["gpiozero.MotionSensor", "RPi.GPIO"],
    "distance": ["adafruit_vl53l0x", "gpiozero.DistanceSensor"],
    "light": ["adafruit_tsl2591", "adafruit_bh1750", "gpiozero.LightSensor"],
    "sound": ["sounddevice", "pyaudio", "gpiozero.AudioDevice"],
    "gas": ["adafruit_sgp30", "adafruit_ccs811", "adafruit_bme680"],
    "accelerometer": ["adafruit_mpu6050", "adafruit_lis3dh"],
    "gyroscope": ["adafruit_mpu6050", "adafruit_l3gd20"],
    "magnetometer": ["adafruit_lsm303_magnet", "adafruit_lis2mdl"],
    "IR": ["adafruit_irremote", "LIRC"],
    "ultrasonic": ["gpiozero.DistanceSensor", "adafruit_hcsr04"],
    "PIR": ["gpiozero.MotionSensor"],
    "vibration": ["adafruit_adxl34x", "gpiozero.Button"],
    "water level": ["gpiozero.DigitalInputDevice", "adafruit_ads1x15"],
    "soil moisture": ["adafruit_seesaw", "gpiozero.MCP3008"]
}

ACTUATOR_LIBRARIES = {
    "servo": ["gpiozero.Servo", "RPi.GPIO", "adafruit_pca9685", "adafruit_servokit"],
    "stepper motor": ["adafruit_motorkit", "RPi.GPIO", "RpiMotorLib", "adafruit_motor"],
    "DC motor": ["gpiozero.Motor", "adafruit_motorkit", "RPi.GPIO", "adafruit_motor"],
    "relay": ["gpiozero.OutputDevice", "RPi.GPIO", "gpiozero.Energenie"],
    "solenoid": ["gpiozero.OutputDevice", "RPi.GPIO"],
    "LED": ["gpiozero.LED", "RPi.GPIO", "adafruit_dotstar", "adafruit_neopixel", "rpi_ws281x"],
    "buzzer": ["gpiozero.Buzzer", "RPi.GPIO", "pygame.mixer"],
    "speaker": ["pygame.mixer", "sounddevice", "pyaudio", "simpleaudio"],
    "display": ["adafruit_displayio_ssd1306", "adafruit_display_text", "luma.core"],
    "LCD": ["RPLCD", "adafruit_charlcd", "luma.lcd", "smbus"],
    "OLED": ["adafruit_ssd1306", "luma.oled", "adafruit_displayio_ssd1306"],
    "e-ink": ["waveshare_epd", "adafruit_epd"],
    "RGB LED": ["adafruit_neopixel", "rpi_ws281x", "gpiozero.RGBLED", "adafruit_dotstar"]
}

CAMERA_LIBRARIES = {
    "picamera": ["picamera", "picamera2", "numpy"],
    "USB camera": ["cv2", "pygame.camera", "numpy"],
    "CSI camera": ["picamera", "picamera2", "libcamera", "numpy"],
    "thermal camera": ["adafruit_amg88xx", "adafruit_mlx90640", "numpy"],
    "security camera": ["picamera", "cv2"],
    "motion detection": ["picamera", "cv2", "numpy"],
    "object detection": ["cv2", "tflite_runtime", "numpy"],
    "facial recognition": ["face_recognition", "cv2", "numpy"],
    "QR code scanner": ["cv2", "pyzbar", "numpy"],
    "time-lapse": ["picamera", "numpy", "os"]
}

# ------------- Per-domain subcategory -> recommended-library maps ------------- #

# IoT Application libraries by type
IOT_LIBRARIES = {
    "smart home": ["paho.mqtt.client", "homeassistant", "requests", "flask", "adafruit_io"],
    "environment monitoring": ["paho.mqtt.client", "influxdb", "adafruit_io", "requests"],
    "remote control": ["flask", "requests", "paho.mqtt.client", "socketio", "adafruit_io"],
    "data logging": ["influxdb", "sqlite3", "pandas", "csv", "matplotlib"],
    "automation": ["schedule", "apscheduler", "paho.mqtt.client", "requests"],
    "IoT gateway": ["paho.mqtt.client", "fastapi", "requests", "websockets", "aiohttp"],
    "MQTT": ["paho.mqtt.client", "paho.mqtt.subscribe", "mosquitto"],
    "webhooks": ["requests", "flask", "fastapi", "aiohttp"],
    "weather station": ["paho.mqtt.client", "influxdb", "adafruit_io", "matplotlib"],
    "energy monitoring": ["paho.mqtt.client", "influxdb", "pandas", "matplotlib"],
    "home security": ["picamera", "cv2", "flask", "paho.mqtt.client", "twilio"],
    "smart garden": ["schedule", "apscheduler", "paho.mqtt.client", "adafruit_io"]
}

# Machine Learning libraries by type
ML_LIBRARIES = {
    "object detection": ["tensorflow", "tflite_runtime", "cv2", "PIL", "numpy"],
    "image classification": ["tensorflow", "tflite_runtime", "cv2", "PIL", "numpy"],
    "voice recognition": ["tensorflow", "tflite_runtime", "sounddevice", "librosa", "numpy"],
    "natural language processing": ["tensorflow", "tflite_runtime", "nltk", "numpy"],
    "anomaly detection": ["tensorflow", "sklearn", "numpy", "pandas"],
    "predictive maintenance": ["tensorflow", "sklearn", "numpy", "pandas", "matplotlib"],
    "sentiment analysis": ["tensorflow", "nltk", "numpy", "sklearn"],
    "gesture recognition": ["tensorflow", "cv2", "mediapipe", "numpy"],
    "TensorFlow Lite": ["tflite_runtime", "numpy", "PIL", "cv2"],
    "TinyML": ["tflite_runtime", "numpy", "tensorflow"]
}

# Beginner Basic libraries by type (simplified libraries for very basic examples)
BEGINNER_BASIC_LIBRARIES = {
    "LED blink": ["gpiozero.LED", "RPi.GPIO", "time"],
    "button input": ["gpiozero.Button", "RPi.GPIO", "time"],
    "temperature reading": ["adafruit_dht", "w1thermsensor", "time"],
    "motion detection": ["gpiozero.MotionSensor", "RPi.GPIO", "time"],
    "light sensing": ["gpiozero.LightSensor", "RPi.GPIO", "time"],
    "buzzer control": ["gpiozero.Buzzer", "RPi.GPIO", "time"],
    "servo control": ["gpiozero.Servo", "RPi.GPIO", "time"],
    "distance measurement": ["gpiozero.DistanceSensor", "RPi.GPIO", "time"],
    "LED matrix": ["adafruit_ht16k33", "luma.led_matrix", "time"],
    "LCD hello world": ["RPLCD", "adafruit_charlcd", "time"],
    "DHT sensor": ["adafruit_dht", "time", "board"],
    "PIR sensor": ["gpiozero.MotionSensor", "RPi.GPIO", "time"],
    "relay switch": ["gpiozero.OutputDevice", "RPi.GPIO", "time"],
    "RGB LED control": ["gpiozero.RGBLED", "RPi.GPIO", "time"],
    "potentiometer reading": ["gpiozero.MCP3008", "RPi.GPIO", "time"],
}

# ===================== PLATFORM-SPECIFIC CONSTRAINTS ===================== #

DKB_VERSION = "4.0"

# Valid BCM GPIO numbers exposed on the 40-pin header (Pi 2 and later).
VALID_BCM_GPIO = set(range(0, 28))  # BCM 0..27

# Per-model hardware capabilities. Encodes the "platform-specific constraints"
# the generator and (optionally) the validator can reason about.
BOARD_SPECS = {
    "Raspberry Pi 5":          {"soc": "BCM2712",  "cores": 4, "wifi": True, "bluetooth": True,
                                "csi_camera": True, "gpio_header": 40,
                                "notes": "Cortex-A76; PCIe; dual 4-lane MIPI; RP1 I/O controller."},
    "Raspberry Pi 4 Model B":  {"soc": "BCM2711",  "cores": 4, "wifi": True, "bluetooth": True,
                                "csi_camera": True, "gpio_header": 40,
                                "notes": "Cortex-A72; USB 3.0; dual micro-HDMI."},
    "Raspberry Pi 3 Model B+": {"soc": "BCM2837B0","cores": 4, "wifi": True, "bluetooth": True,
                                "csi_camera": True, "gpio_header": 40,
                                "notes": "Cortex-A53; Gigabit Ethernet (USB-bridged)."},
    "Raspberry Pi Zero W":     {"soc": "BCM2835",  "cores": 1, "wifi": True, "bluetooth": True,
                                "csi_camera": True, "gpio_header": 40,
                                "notes": "Single-core; low power; mini-HDMI; no Ethernet."},
}

# Subcategory -> library map lookup, used by helpers below.
_DOMAIN_LIBRARY_TABLES = {
    "sensors": SENSOR_LIBRARIES,
    "actuators": ACTUATOR_LIBRARIES,
    "cameras": CAMERA_LIBRARIES,
    "iot_applications": IOT_LIBRARIES,
    "ml_applications": ML_LIBRARIES,
    "beginner_basic": BEGINNER_BASIC_LIBRARIES,
}

_WHITELIST_TOP = {m.split(".")[0] for m in STANDARD_LIBRARIES_FLAT}


# ============================== HELPER API ============================== #

def is_allowed(module_name):
    """True if an imported module is on the whitelist (exact entry, or a dotted
    child of a whitelisted top-level package)."""
    if not module_name:
        return False
    return module_name in STANDARD_LIBRARIES_FLAT or module_name.split(".")[0] in _WHITELIST_TOP


def get_domain_libraries(category, subcategory):
    """Recommended libraries for a (category, subcategory) pair; [] if unmapped."""
    return list(_DOMAIN_LIBRARY_TABLES.get(category, {}).get(subcategory, []))


def get_board_spec(model):
    """Hardware spec dict for a Pi model name, or None if unknown."""
    return BOARD_SPECS.get(model)


def valid_gpio_pin(pin):
    """True if `pin` is a valid BCM GPIO number on the 40-pin header."""
    try:
        return int(pin) in VALID_BCM_GPIO
    except (TypeError, ValueError):
        return False


def validate_dkb():
    """Internal self-consistency check of the knowledge base.

    Returns (ok, issues): ok is True when no critical inconsistency is found.
    Critical invariants checked: whitelist and blacklist are disjoint; every alias
    key is itself blacklisted; every taxonomy category has at least one subcategory;
    every per-domain map key is a known subcategory.
    """
    issues = []
    overlap = DISALLOWED_LIBRARIES & set(STANDARD_LIBRARIES_FLAT)
    if overlap:
        issues.append(f"whitelist/blacklist overlap: {sorted(overlap)}")
    stray_alias = set(LIBRARY_ALIASES) - DISALLOWED_LIBRARIES
    if stray_alias:
        issues.append(f"alias keys not in blacklist: {sorted(stray_alias)}")
    for cat, subs in CATEGORIES.items():
        if not subs:
            issues.append(f"category '{cat}' has no subcategories")
    for cat, table in _DOMAIN_LIBRARY_TABLES.items():
        known = set(CATEGORIES.get(cat, []))
        for sub in table:
            if known and sub not in known:
                issues.append(f"{cat}: '{sub}' has libraries but is not a listed subcategory")
    return (len(issues) == 0, issues)


__all__ = [
    # taxonomy
    "CATEGORIES", "CODE_STYLES", "COMPLEXITY_LEVELS", "PI_MODELS",
    "INTEGRATION_PATTERNS", "USE_CONTEXTS", "HARDWARE_CATEGORIES", "SOFTWARE_CATEGORIES",
    "CODE_LENGTH_LIMITS", "CATEGORY_LENGTH_ADJUSTMENTS",
    # library whitelist / blacklist
    "STANDARD_LIBRARIES", "STANDARD_LIBRARIES_FLAT",
    "DISALLOWED_LIBRARIES", "LIBRARY_ALIASES",
    # per-domain maps
    "SENSOR_LIBRARIES", "ACTUATOR_LIBRARIES", "CAMERA_LIBRARIES",
    "IOT_LIBRARIES", "ML_LIBRARIES", "BEGINNER_BASIC_LIBRARIES",
    # board constraints
    "BOARD_SPECS", "VALID_BCM_GPIO", "DKB_VERSION",
    # helpers
    "is_allowed", "is_disallowed", "get_domain_libraries",
    "get_board_spec", "valid_gpio_pin", "validate_dkb",
]
