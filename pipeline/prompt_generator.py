#!/usr/bin/env python3
"""
Advanced Prompt Generator for Raspberry Pi Code Examples
Generates sophisticated, context-aware coding prompts with intelligent adaptations
Created: 2025-04-20 13:15:19
Author: Sakkibbb
Modified: 2025-04-20 15:05:22
"""

import logging
import random
import hashlib
import json
from typing import Dict, List

from dkb import HARDWARE_CATEGORIES, SOFTWARE_CATEGORIES

# Logger configuration
logger = logging.getLogger(__name__)

class PromptGenerator:
    """
    Advanced prompt generator that creates highly detailed and contextually appropriate
    coding prompts for Raspberry Pi applications across multiple complexity levels.
    """
    
    def __init__(self, categories_dict: Dict, standard_libraries: List[str], 
                 code_length_limits: Dict[str, int], api_client):
        """
        Initialize the prompt generator with categories, libraries and API client.
        
        Args:
            categories_dict: Dictionary of categories and subcategories
            standard_libraries: List of standard Python libraries
            code_length_limits: Dictionary mapping complexity levels to code length limits
            api_client: Client for making API calls to Gemini
        """
        self.categories = categories_dict
        self.standard_libraries = standard_libraries
        self.code_length_limits = code_length_limits
        self.api_client = api_client
        
        # Define explicitly disallowed libraries to avoid validation issues
        self.DISALLOWED_LIBRARIES = [
            "PiCamera",      # Use picamera2 instead
            "Flask",         # Usually too heavy for simple Pi applications
            "io",            # Often misused - use standard file operations
            "Image",         # Use PIL or pillow instead
            "Button",        # Use gpiozero.Button instead
            "Adafruit_DHT",  # Older library - use adafruit_dht instead
            "SMBus",         # Use smbus instead for consistency
            "digitalio",     # Use direct GPIO access instead
            "MCP3008",       # Use SpiDev or gpiozero equivalents
            "OutputDevice",  # Use gpiozero equivalents
            "Camera",        # Use picamera2 instead
            "django",        # Too heavyweight for most Pi applications
        ]
        
        # Category-specific length adjustments
        self.CATEGORY_LENGTH_ADJUSTMENTS = {
            "iot_applications": 1.5,  # Allow 50% more lines
            "ml_applications": 1.5,   # Allow 50% more lines
            "cameras": 1.2,           # Allow 20% more lines
            "robotics": 1.2,          # Allow 20% more lines
            "display": 1.15           # Allow 15% more lines 
        }
        
        # Define hardware-focused categories (canonical taxonomy from dkb)
        self.hardware_categories = list(HARDWARE_CATEGORIES)

        # Define software-focused categories (canonical taxonomy from dkb)
        self.software_categories = list(SOFTWARE_CATEGORIES)
        
        # Initialize comprehensive specialized library mappings
        self._initialize_specialized_library_mappings()
        
        # Cache for generated prompts (to avoid API calls for identical parameters)
        self.prompt_cache = {}
        
        # Temperature ranges by complexity level (for adjusting AI randomness)
        self.temperature_ranges = {
            "beginner_basic": (0.5, 0.6),  # More focused, less creative
            "beginner": (0.6, 0.7),
            "intermediate": (0.7, 0.8),
            "advanced": (0.7, 0.9),  # More creative, diverse outputs
        }

    def get_adjusted_length_limit(self, category: str, complexity: str) -> int:
        """
        Get length limit adjusted for specific categories that naturally need more code.
        
        Args:
            category: The hardware/application category
            complexity: Complexity level
            
        Returns:
            Adjusted line count limit
        """
        # Base length from code_length_limits
        base_length = self.code_length_limits.get(complexity, 100)
        
        # Apply adjustment factor if category has one
        adjustment_factor = self.CATEGORY_LENGTH_ADJUSTMENTS.get(category, 1.0)
        adjusted_length = int(base_length * adjustment_factor)
        
        return adjusted_length

    def _initialize_specialized_library_mappings(self):
        """Initialize comprehensive specialized library mappings for various applications."""
        # Specialized library options for different application types
        self.specialized_libraries = {
            # Sensors with specialized libraries
            "sensors": {
                "temperature": ["w1thermsensor", "adafruit_dht", "adafruit_mlx90614", "gpiozero", "RPi.GPIO", "pigpio"],
                "humidity": ["adafruit_dht", "adafruit_sht31d", "adafruit_ahtx0", "gpiozero", "RPi.GPIO", "pigpio"],
                "pressure": ["adafruit_bmp280", "adafruit_bme280", "adafruit_ms8607", "smbus", "gpiozero", "RPi.GPIO"],
                "motion": ["gpiozero", "RPi.GPIO", "pigpio"],
                "light": ["adafruit_tsl2591", "adafruit_veml7700", "gpiozero", "RPi.GPIO", "spidev"],
                "distance": ["hcsr04sensor", "gpiozero", "RPi.GPIO", "pigpio"],
                "fingerprint": ["pyserial", "serial", "RPi.GPIO", "gpiozero"],
                "biometric": ["pyserial", "serial", "smbus", "RPi.GPIO", "gpiozero"]
            },
            
            # Actuators with specialized control libraries
            "actuators": {
                "led": ["gpiozero", "RPi.GPIO", "pigpio", "neopixel", "rpi_ws281x", "apa102_pi"],
                "motor": ["gpiozero", "RPi.GPIO", "pigpio", "adafruit_motorkit", "adafruit_motor", "PCA9685"],
                "servo": ["gpiozero", "RPi.GPIO", "pigpio", "adafruit_servokit", "adafruit_pca9685", "servokit"],
                "relay": ["gpiozero", "RPi.GPIO", "pigpio"],
                "display": ["RPLCD", "luma.oled", "spidev", "smbus", "adafruit_ssd1306"]
            },
            
            # Camera applications with vision libraries
            "cameras": {
                "picamera": ["picamera2", "numpy", "PIL"],
                "usb camera": ["cv2", "PIL", "numpy", "pygame"],
                "thermal camera": ["numpy", "matplotlib", "PIL", "adafruit_amg88xx"],
                "depth sensor": ["numpy", "cv2", "PIL", "pyrealsense2"],
                "QR code scanner": ["cv2", "PIL", "numpy", "pyzbar", "qrcode"],
                "facial recognition": ["cv2", "PIL", "numpy", "face_recognition"]
            },
            
            # IoT with networking options
            "iot_applications": {
                "mqtt": ["paho-mqtt", "json", "ssl", "asyncio"],
                "web server": ["socket", "http.server", "bottle", "wsgiref"],
                "data logging": ["logging", "sqlite3", "csv", "pandas", "numpy"],
                "home automation": ["paho-mqtt", "schedule", "json", "yaml"],
                "weather station": ["requests", "json", "sqlite3", "datetime"],
                "environmental monitoring": ["matplotlib", "sqlite3", "pandas", "numpy"],
                "smart home": ["paho-mqtt", "json", "yaml", "socket"]
            },
            
            # ML with specialized libraries
            "ml_applications": {
                "image classification": ["cv2", "PIL", "numpy", "tflite_runtime"],
                "speech recognition": ["pyaudio", "numpy", "wave", "librosa"],
                "sensor analytics": ["numpy", "matplotlib", "pandas", "scikit-learn"],
                "predictive maintenance": ["numpy", "pandas", "matplotlib", "scipy"],
                "natural language processing": ["json", "re", "nltk", "sqlite3"]
            },
            
            # Software-focused categories with no hardware dependencies
            "data_processing": {
                "data visualization": ["matplotlib", "pandas", "numpy", "seaborn"],
                "data collection": ["requests", "json", "csv", "sqlite3"],
                "data analysis": ["pandas", "numpy", "scipy", "matplotlib"]
            },
            
            "web_applications": {
                "dashboard": ["bottle", "json", "sqlite3", "datetime"],
                "api": ["bottle", "json", "requests", "socket"],
                "static site": ["http.server", "socket", "os", "pathlib"]
            },
            
            "system_utils": {
                "file management": ["os", "shutil", "pathlib", "glob"],
                "process monitor": ["psutil", "subprocess", "datetime", "logging"],
                "backup tool": ["os", "shutil", "datetime", "zipfile"]
            },
            
            "audio": {
                "playback": ["pygame", "pyaudio", "wave", "numpy"],
                "recording": ["pyaudio", "wave", "numpy", "datetime"],
                "processing": ["pyaudio", "numpy", "wave", "scipy"]
            },
            
            "networking": {
                "client": ["socket", "requests", "ssl", "json"],
                "server": ["socket", "http.server", "threading", "json"],
                "protocol": ["socket", "ssl", "struct", "threading"]
            },
            
            # Beginners with simpler options
            "beginner_basic": {
                "led blink": ["RPi.GPIO", "gpiozero", "time"],
                "button": ["RPi.GPIO", "gpiozero", "time"],
                "basic sensor": ["RPi.GPIO", "gpiozero", "time"],
                "temperature sensor": ["w1thermsensor", "RPi.GPIO", "time"],
                "display": ["RPLCD", "spidev", "RPi.GPIO"]
            }
        }

    def get_recommended_libraries(self, category: str, subcategory: str, complexity: str = None) -> List[str]:
        """
        Get recommended libraries for the given category and subcategory,
        with context-appropriate selection and no forced hardware libraries.
        
        Args:
            category: The hardware/application category
            subcategory: The specific type within the category
            complexity: Optional complexity level to adjust recommendations
            
        Returns:
            List of recommended library names
        """
        libraries = []
        
        # Check if this is a hardware or software focused category
        is_hardware_focused = category in self.hardware_categories
        is_software_focused = category in self.software_categories
        
        # Determine how many libraries to recommend based on complexity
        if complexity == "beginner_basic":
            num_libraries = 1
        elif complexity == "beginner":
            num_libraries = random.randint(1, 2)
        elif complexity == "intermediate":
            num_libraries = random.randint(2, 3)
        else:  # advanced
            num_libraries = random.randint(2, 4)
        
        # Get specialized library options for this category/subcategory
        category_options = self.specialized_libraries.get(category, {})
        # Copy to avoid mutating the stored DKB list via append/shuffle below
        options = list(category_options.get(subcategory, []))
        
        # If no specific options found, use standard libraries
        if not options:
            # Some standard Python libraries that are generally useful
            if complexity == "beginner_basic":
                options = ["time"]
            else:
                options = ["time", "os", "logging", "json", "datetime"]
        
        # For software-focused applications, don't include hardware libraries by default
        if is_software_focused:
            # Filter out hardware-specific libraries
            options = [lib for lib in options if lib not in 
                      ['RPi.GPIO', 'gpiozero', 'pigpio', 'adafruit_servokit', 
                       'adafruit_motorkit', 'adafruit_ssd1306', 'picamera2']]
        
        # For hardware applications, ensure we have some hardware libraries in the options
        elif is_hardware_focused and not any(lib in options for lib in ['RPi.GPIO', 'gpiozero', 'pigpio']):
            # Add appropriate hardware libraries if they're missing
            if random.random() > 0.5:
                options.append('RPi.GPIO')
            else:
                options.append('gpiozero')
        
        # Randomly select libraries from our options
        if options:
            random.shuffle(options)  # Shuffle to ensure variety
            libraries = options[:num_libraries]
        
        # Add some standard libraries based on complexity
        standard_additions = []
        if complexity != "beginner_basic":
            # Always add time unless it's already included
            if "time" not in libraries:
                standard_additions.append("time")
            
            # Sometimes add logging for more advanced code
            if complexity in ["intermediate", "advanced"] and random.random() > 0.5:
                standard_additions.append("logging")
        
        # Filter out any disallowed libraries
        libraries = [lib for lib in libraries if lib not in self.DISALLOWED_LIBRARIES]
        standard_additions = [lib for lib in standard_additions if lib not in libraries and lib not in self.DISALLOWED_LIBRARIES]
        
        # Return the combined list with duplicates removed (preserving order)
        seen = set()
        return [x for x in (libraries + standard_additions) 
                if not (x in seen or seen.add(x))]
    
    def get_library_usage_guidance(self, libraries: List[str], complexity: str = "intermediate") -> str:
        """
        Get detailed usage guidance for specific libraries with complexity-appropriate detail.
        
        Args:
            libraries: List of libraries to provide guidance for
            complexity: Complexity level to adjust detail
            
        Returns:
            Formatted string with library usage guidance
        """
        # Comprehensive library guidance database
        library_guidance = {
            "RPi.GPIO": {
                "basic": "for direct GPIO pin control",
                "intermediate": "for direct GPIO control with edge detection and PWM support",
                "advanced": "for low-level GPIO operations with interrupt-driven event detection and precise timing"
            },
            "gpiozero": {
                "basic": "for easy-to-use GPIO interfaces",
                "intermediate": "for simplified GPIO interfaces with built-in device abstractions",
                "advanced": "for high-level GPIO abstractions with event handling and device composition patterns"
            },
            "pigpio": {
                "basic": "for precise GPIO timing control",
                "intermediate": "for advanced GPIO control with hardware PWM and servo control",
                "advanced": "for sophisticated GPIO access with hardware-timed PWM, servo control, and waveform generation"
            },
            "picamera2": {
                "basic": "for simple camera capture",
                "intermediate": "for camera control with various capture modes and settings",
                "advanced": "for advanced camera operations including custom image formats, overlays, and GPU acceleration"
            },
            "w1thermsensor": {
                "basic": "for reading temperature from 1-Wire sensors",
                "intermediate": "for reading temperature from multiple 1-Wire sensors with proper timing",
                "advanced": "for reliable 1-Wire temperature sensor readings with comprehensive error handling and calibration"
            },
            "adafruit_dht": {
                "basic": "for reading temperature and humidity from DHT sensors",
                "intermediate": "for reliable DHT sensor readings with error handling",
                "advanced": "for advanced DHT sensor integration with automatic retries and calibration"
            },
            "RPLCD": {
                "basic": "for controlling character LCD displays",
                "intermediate": "for character LCD control with custom characters and animations",
                "advanced": "for sophisticated LCD interfaces with custom character sets and menu systems"
            },
            "luma.oled": {
                "basic": "for controlling OLED displays",
                "intermediate": "for OLED graphics display with text and simple shapes",
                "advanced": "for advanced OLED graphics with animations and custom rendering"
            },
            "paho-mqtt": {
                "basic": "for simple MQTT messaging",
                "intermediate": "for MQTT communication with QoS options and persistence",
                "advanced": "for robust MQTT messaging with QoS guarantees, TLS security, and automatic reconnection"
            },
            "cv2": {
                "basic": "for basic image processing",
                "intermediate": "for computer vision with built-in algorithms",
                "advanced": "for high-performance computer vision with hardware acceleration and custom processing pipelines"
            },
            "numpy": {
                "basic": "for basic numerical operations",
                "intermediate": "for efficient numerical computation with arrays",
                "advanced": "for high-performance numerical processing with vectorized operations"
            },
            "pandas": {
                "basic": "for data manipulation and analysis",
                "intermediate": "for structured data processing with filtering and transformations",
                "advanced": "for sophisticated data analysis with complex operations and performance optimization"
            }
        }
        
        # Determine which guidance level to use based on complexity
        guidance_level = "basic"
        if complexity == "intermediate":
            guidance_level = "intermediate"
        elif complexity == "advanced":
            guidance_level = "advanced"
        
        # Create guidance for each library
        library_tips = []
        for lib in libraries[:3]:  # Limit to first 3 for conciseness
            if lib in library_guidance:
                desc = library_guidance[lib].get(guidance_level, library_guidance[lib].get("basic", ""))
                library_tips.append(f"{lib} ({desc})")
            else:
                library_tips.append(lib)
                
        # Format the guidance
        if not library_tips:
            return ""
        
        if complexity == "beginner_basic":
            return "Suggested library: " + library_tips[0]
        else:
            return "Suggested libraries: " + ", ".join(library_tips)

    def generate_category_guidance(self, category: str, subcategory: str, complexity: str) -> str:
        """
        Generate detailed guidance based on category, subcategory and complexity.
        
        Args:
            category: The hardware/application category
            subcategory: The specific type within the category
            complexity: Code complexity level
            
        Returns:
            Detailed technical guidance string
        """
        # Expanded category guidance with multiple complexity levels
        category_guidance = {
            "sensors": {
                "beginner_basic": "Focus on reading a single sensor value and displaying it.",
                "beginner": "If simulation is necessary, clearly label it as a simulation.",
                "intermediate": "Include calibration routines and error correction for sensor readings.",
                "advanced": "Implement configurable sampling rates, noise filtering, and data validation."
            },
            "actuators": {
                "beginner_basic": "Focus on basic control of a single actuator.",
                "beginner": "Include precise control mechanisms and safety features.",
                "intermediate": "Add position feedback and closed-loop control where applicable.",
                "advanced": "Implement PWM control with proper frequency selection and protection circuits."
            },
            "cameras": {
                "beginner_basic": "Capture and display a single image.",
                "beginner": "Include image capture, processing, and storage capabilities.",
                "intermediate": "Add configurable resolution, exposure, and effects.",
                "advanced": "Implement streaming, motion detection, and frame buffer management."
            },
            "iot_applications": {
                "beginner_basic": "Focus on a single IoT interaction like reading/sending data.",
                "beginner": "Include networking, data handling, and remote access features.",
                "intermediate": "Add secure connections, data validation, and error recovery.",
                "advanced": "Implement message queuing, offline operation, and synchronization."
            },
            "ml_applications": {
                "beginner_basic": "Focus on using a pre-trained model for simple inference.",
                "beginner": "Consider memory and processing limitations of Raspberry Pi.",
                "intermediate": "Implement model optimization and inference acceleration.",
                "advanced": "Add model quantization, hardware acceleration, and pipeline optimizations."
            },
            "data_processing": {
                "beginner_basic": "Focus on reading and processing a single data source.",
                "beginner": "Include data parsing, basic analysis, and simple visualization.",
                "intermediate": "Add more sophisticated data transformations and reporting.",
                "advanced": "Implement advanced analytics, optimization, and complex visualizations."
            },
            "web_applications": {
                "beginner_basic": "Create a simple web server with static content.",
                "beginner": "Implement basic request handling and dynamic content.",
                "intermediate": "Add more sophisticated routing, templates, and data storage.",
                "advanced": "Implement authentication, sessions, and advanced request handling."
            },
            "system_utils": {
                "beginner_basic": "Create a simple utility for a specific task.",
                "beginner": "Include proper error handling and user feedback.",
                "intermediate": "Add configuration options and more robust operation.",
                "advanced": "Implement comprehensive logging, recovery mechanisms, and advanced features."
            },
            "beginner_basic": {
                "beginner_basic": "Keep the code extremely simple and focused on one task.",
                "beginner": "Keep the code simple, focused on one task, and suitable for beginners.",
                "intermediate": "Build a simple but complete application with proper structure.",
                "advanced": "Create a comprehensive but accessible application with best practices."
            }
        }
        
        # Get basic guidance for the category and complexity
        guidance = category_guidance.get(category, {}).get(complexity, "")
        
        # Add subcategory-specific guidance
        subcategory_guidance = self._get_subcategory_guidance(category, subcategory, complexity)
        if subcategory_guidance:
            guidance = f"{guidance} {subcategory_guidance}"
            
        return guidance
    
    def _get_subcategory_guidance(self, category: str, subcategory: str, complexity: str) -> str:
        """
        Get specific guidance for subcategories with complexity-based details.
        
        Args:
            category: The hardware/application category
            subcategory: The specific type within the category
            complexity: Code complexity level
            
        Returns:
            Subcategory-specific guidance
        """
        # Define subcategory-specific guidance by complexity
        subcategory_map = {
            "sensors": {
                "temperature": {
                    "beginner_basic": "Read temperature values at regular intervals.",
                    "beginner": "Include temperature range validation.",
                    "intermediate": "Add unit conversion and moving average filtering.",
                    "advanced": "Implement sensor calibration, fault detection, and compensation algorithms."
                },
                "humidity": {
                    "beginner_basic": "Read humidity values at regular intervals.",
                    "beginner": "Consider sensor limitations in extreme conditions.",
                    "intermediate": "Consider condensation thresholds and response time limitations.",
                    "advanced": "Implement dewpoint calculation, trend analysis, and environmental correlations."
                },
                "motion": {
                    "beginner_basic": "Detect motion events and respond with a simple action.",
                    "beginner": "Implement basic debouncing for motion detection.",
                    "intermediate": "Implement debouncing and false-positive filtering.",
                    "advanced": "Add zone-based detection, sensitivity adjustment, and sophisticated filtering."
                }
            },
            "actuators": {
                "led": {
                    "beginner_basic": "Control LED on/off states.",
                    "beginner": "Include brightness control via PWM.",
                    "intermediate": "Add lighting patterns and transitions.",
                    "advanced": "Implement color mixing, gamma correction, and power management."
                },
                "motor": {
                    "beginner_basic": "Control motor direction and on/off states.",
                    "beginner": "Add variable speed control and safety limits.",
                    "intermediate": "Implement speed ramping and basic feedback.",
                    "advanced": "Add closed-loop control, stall detection, and thermal protection."
                },
                "display": {
                    "beginner_basic": "Show simple text on a display.",
                    "beginner": "Display dynamic content with updates.",
                    "intermediate": "Add graphics, fonts, and user interface elements.",
                    "advanced": "Implement advanced UI with touch control and animations."
                }
            }
        }
        
        # Retrieve the guidance based on category, subcategory and complexity
        category_map = subcategory_map.get(category, {})
        subcategory_guidance = category_map.get(subcategory, {})
        return subcategory_guidance.get(complexity, "")

    def generate_complexity_guidance(self, complexity: str) -> str:
        """
        Generate detailed guidance specific to the complexity level.
        
        Args:
            complexity: Code complexity level
            
        Returns:
            Comprehensive complexity-specific guidance
        """
        complexity_guidance = {
            "beginner_basic": """
            - Keep code extremely simple and straightforward (30-50 lines maximum)
            - Use minimal imports (3-4 maximum) and focus on clear, readable code
            - Include helpful comments explaining each step for beginners
            - Use simple error handling if any (try/except for critical operations)
            - Focus on demonstrating just one core concept
            - Use a procedural approach with minimal function definitions
            - Avoid complex programming patterns or advanced Python features
            - Include print statements to show progress and status
            """,
            
            "beginner": """
            - Use simple but complete implementation (50-100 lines)
            - Organize code with proper functions for readability
            - Include basic error handling for main operations
            - Add docstrings for functions
            - Implement 1-2 related features in a cohesive application
            - Use clear variable names and descriptive comments
            - Follow basic Python style conventions
            - Avoid overly complex constructs or advanced patterns
            """,
            
            "intermediate": """
            - Develop a modular approach with well-designed functions (100-150 lines)
            - Implement proper error handling with specific exception types
            - Include complete documentation with parameters and return values
            - Add configuration options and flexible implementation
            - Consider performance and resource constraints
            - Use appropriate design patterns for the problem domain
            - Implement robust validation and error recovery
            - Include proper resource management (close files, connections)
            - Follow PEP 8 style guidelines consistently
            """,
            
            "advanced": """
            - Design professional-grade architecture (150-250 lines)
            - Implement comprehensive error handling, logging, and recovery
            - Create well-structured class hierarchies where appropriate
            - Add detailed documentation including examples and edge cases
            - Consider threading for non-blocking operations
            - Implement advanced features like data persistence or network resilience
            - Add configuration management and runtime adaptability
            - Optimize for performance with profiling considerations
            - Implement graceful degradation for error conditions
            - Add integration points for potential system expansion
            - Consider security implications and implement safeguards
            """
        }
        
        return complexity_guidance.get(complexity, "")
    
    def generate_integration_guidance(self, integration: str, complexity: str) -> str:
        """
        Generate guidance specific to the integration pattern, adjusted for complexity.
        
        Args:
            integration: Integration pattern name
            complexity: Code complexity level
            
        Returns:
            Integration-specific guidance adjusted for complexity
        """
        # Basic guidance keyed on the actual INTEGRATION_PATTERNS taxonomy values
        base_guidance = {
            "standalone": "Application should be completely self-contained with no external dependencies beyond the Pi itself.",
            "with multiple actuators": "Coordinate control of multiple actuators, managing their state and timing safely.",
            "with camera, sensor": "Integrate camera and sensor input together, synchronizing capture with sensor readings.",
            "with multiple sensors": "Read and fuse data from multiple sensors, handling per-sensor initialization and error states.",
            "in distributed system": "Operate as part of a distributed system, exchanging data with other nodes over the network.",
        }

        # Advanced guidance by complexity level
        advanced_guidance = {
            "with multiple sensors": {
                "beginner_basic": "Read each sensor sequentially with minimal error handling.",
                "beginner": "Read each sensor with basic error handling and clear separation per sensor.",
                "intermediate": "Manage multiple sensors with per-sensor initialization, polling intervals, and error recovery.",
                "advanced": "Fuse multiple sensor streams with robust error recovery, timestamping, and concurrent acquisition."
            },
            "in distributed system": {
                "beginner_basic": "Use a simple message exchange with minimal error handling.",
                "beginner": "Implement basic network communication with simple error handling.",
                "intermediate": "Implement reliable networked communication with authentication and reconnection handling.",
                "advanced": "Implement full distributed-system features with delivery guarantees, security, and offline operation."
            }
        }
        
        # Get the basic guidance first
        guidance = base_guidance.get(integration, "")
        
        # Add advanced guidance if available for this integration and complexity
        if integration in advanced_guidance and complexity in advanced_guidance[integration]:
            guidance = advanced_guidance[integration][complexity]
            
        return guidance
    
    def generate_pi_model_guidance(self, pi_model: str) -> str:
        """
        Generate guidance specific to the Raspberry Pi model.
        
        Args:
            pi_model: Raspberry Pi model name
            
        Returns:
            Pi model-specific guidance
        """
        # Expanded guidance with technical specifications, keyed by a normalized
        # token derived from the actual PI_MODELS taxonomy values.
        model_guidance = {
            "zero": """
            Consider the limited processing power (1GHz single-core) and memory (512MB RAM).
            Optimize for low resource usage and minimize background processes.
            Built-in Wi-Fi 802.11n and Bluetooth 4.1 available (Pi Zero W).
            GPIO pins available: 40 pins (same layout as Pi 3/4).
            """,

            "3": """
            Balance performance with power efficiency.
            Specifications: 1.2GHz quad-core ARMv8, 1GB RAM.
            Built-in Wi-Fi 802.11n, Bluetooth 4.1, Ethernet.
            Available GPIO pins: 40.
            """,

            "4": """
            Leverage USB 3.0 and gigabit Ethernet if needed.
            Specifications: 1.5GHz quad-core ARMv8, 2GB/4GB/8GB RAM options.
            Built-in Wi-Fi 802.11ac, Bluetooth 5.0, true Gigabit Ethernet.
            Available GPIO pins: 40.
            Consider heat management for sustained performance.
            """,

            "5": """
            Leverage the higher performance and PCIe/USB 3.0 connectivity if needed.
            Specifications: 2.4GHz quad-core ARM Cortex-A76, 4GB/8GB RAM options.
            Built-in Wi-Fi 802.11ac, Bluetooth 5.0, true Gigabit Ethernet, PCIe 2.0.
            Available GPIO pins: 40.
            Consider active cooling for sustained performance.
            """
        }

        # Normalize the real PI_MODELS strings to a match token.
        # Order matters: check "zero" before the numeric models.
        model_lower = pi_model.lower()
        if "zero" in model_lower:
            return model_guidance["zero"]
        for token in ("5", "4", "3"):
            if token in model_lower:
                return model_guidance[token]

        # Default guidance if no specific model matched
        return "Ensure code is optimized for the specific capabilities of the target Raspberry Pi model."
    
    def generate_context_guidance(self, context: str) -> str:
        """
        Generate guidance specific to the use context.
        
        Args:
            context: Usage context description
            
        Returns:
            Context-specific guidance
        """
        context_keywords = {
            "education": """
            - Focus on clear explanations and visualizations
            - Prioritize readability and understandability over optimization
            - Include abundant comments explaining concepts
            - Add learning checkpoints or challenges in comments
            - Consider classroom or learning environment constraints
            """,
            
            "home": """
            - Emphasize user-friendly interfaces and reliability
            - Consider integration with common home systems
            - Prioritize stability and ease of maintenance
            - Add clear setup instructions for non-experts
            - Implement power-saving features for 24/7 operation
            """,
            
            "industrial": """
            - Implement robust error handling and comprehensive logging
            - Consider environmental factors (temperature, vibration, EMI)
            - Prioritize reliability and fault tolerance
            - Add watchdog mechanisms to recover from failures
            - Consider power backup and safe shutdown procedures
            """,
            
            "research": """
            - Prioritize data accuracy and flexible configuration
            - Add comprehensive logging and data validation
            - Implement flexible parameter adjustment
            - Consider integration with analysis tools or frameworks
            - Allow experimental configuration and extension points
            """,
        }
        
        # Look for matching keywords in the context
        for keyword, guidance in context_keywords.items():
            if keyword in context.lower():
                return guidance
        
        # Default guidance if no specific context matched
        return "Ensure the implementation is suitable for the specific use case."

    def _generate_prompt_fingerprint(self, params: Dict) -> str:
        """
        Generate a unique fingerprint for caching prompt generation parameters.
        
        Args:
            params: Dictionary of prompt generation parameters
            
        Returns:
            Unique hash string for the parameter set
        """
        # Create a stable representation of params
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()

    def generate_prompt_template(self, category: str, subcategory: str, complexity: str = "intermediate") -> str:
        """
        Generate a detailed template for the prompt generation API call.
        
        Args:
            category: The hardware/application category
            subcategory: The specific type within the category
            complexity: Code complexity level
            
        Returns:
            Complete prompt template for first-stage API call
        """
        # Get appropriate libraries for this application type
        recommended_libs = self.get_recommended_libraries(category, subcategory, complexity)
        libraries_text = ""
        
        if recommended_libs:
            libraries_guidance = self.get_library_usage_guidance(recommended_libs, complexity)
            libraries_text = f"""
            Consider using appropriate libraries for implementation. Some suggestions:
            {', '.join(recommended_libs)}
            
            {libraries_guidance}
            """
        
        # Add category-specific instructions
        category_guidance = self.generate_category_guidance(category, subcategory, complexity)
        
        # Get adjusted length limit for this category
        adjusted_length = self.get_adjusted_length_limit(category, complexity)
        
        # Determine if this is hardware or software focused
        is_hardware_focused = category in self.hardware_categories
        is_software_focused = category in self.software_categories
        
        # Create appropriate hardware guidance based on category type
        if is_hardware_focused:
            hardware_text = """
            This application involves hardware interaction. Include appropriate hardware connections 
            and GPIO pins in your prompt. Choose libraries appropriate for the specific hardware components.
            """
        elif is_software_focused:
            hardware_text = """
            This is primarily a software application. Focus on data processing, user interface, 
            and software functionality rather than hardware control.
            """
        else:
            hardware_text = """
            Consider whether this application requires hardware interaction. If it does, include 
            appropriate hardware connections. If not, focus on software functionality.
            """
        
        # Adjust the prompt complexity based on the target code complexity
        prompt_detail_level = {
            "beginner_basic": "Create a simple, straightforward coding prompt suitable for absolute beginners.",
            "beginner": "Create a clear, focused coding prompt with basic technical requirements.",
            "intermediate": "Create a detailed coding prompt with specific technical requirements and considerations.",
            "advanced": "Create a comprehensive, technically detailed coding prompt with in-depth requirements and edge cases."
        }
        
        detail_instruction = prompt_detail_level.get(complexity, prompt_detail_level["intermediate"])
        
        # Show a subset of standard libraries (up to 20) to avoid too much text
        standard_libs_subset = self.standard_libraries[:20] if len(self.standard_libraries) > 20 else self.standard_libraries
        
        template = f"""
        You are a specialized prompt engineer for Raspberry Pi programming. {detail_instruction}
        
        Create a detailed, creative coding prompt for a Python program that implements a {subcategory} {category} application on a Raspberry Pi.

        The prompt should be specific, technical, and highly detailed. Include requirements about:
        1. The specific functionality and features required
        2. Appropriate libraries for the task (choose libraries that make sense for this specific application)
        3. What the code should accomplish in a realistic real-world application
        4. Error handling requirements
        5. Documentation standards
        6. A detailed and practical use case scenario with real-world relevance
        
        {hardware_text}
        
        {libraries_text}
        
        Technical guidance:
        {category_guidance}
        
        IMPORTANT LIBRARY GUIDELINES:
        - Choose only libraries that are appropriate for this specific application
        - Use standard Python libraries and Raspberry Pi-specific libraries as needed
        - Available Raspberry Pi libraries include: {', '.join(standard_libs_subset)}... and more
        - DISALLOWED libraries: {', '.join(self.DISALLOWED_LIBRARIES)} - DO NOT use these!
        - DO NOT import from custom modules - all code MUST be in a single file
        - DO NOT use libraries that require pip install unless they are standard Raspberry Pi libraries
        
        CODE LENGTH GUIDANCE:
        - The final code should be approximately {adjusted_length} lines long
        - Be concise but complete - don't unnecessarily pad the code
        
        Make your prompt technically accurate for real-world implementation. Focus on solving actual problems that might be encountered in production environments, education, research, or hobbyist contexts.
        
        Provide ONLY the prompt text, formatted as a direct instruction to a developer. Do not include any meta-commentary or notes about the prompt itself.
        """
        
        return template

    def generate_ai_prompt(self, category: str, subcategory: str, complexity: str, 
                          style: str, pi_model: str, integration: str, context: str) -> str:
        """
        Use Gemini to generate a creative, detailed coding prompt with comprehensive guidance.
        
        Args:
            category: The hardware/application category
            subcategory: The specific type within the category
            complexity: Code complexity level
            style: Programming style (basic, functional, simple script)
            pi_model: Target Raspberry Pi model
            integration: Integration pattern
            context: Usage context
            
        Returns:
            Complete, enriched prompt ready for code generation
        """
        # Parameters for caching
        params = {
            "category": category,
            "subcategory": subcategory,
            "complexity": complexity,
            "style": style,
            "pi_model": pi_model,
            "integration": integration,
            "context": context
        }
        
        # Check cache first
        cache_key = self._generate_prompt_fingerprint(params)
        if cache_key in self.prompt_cache:
            logger.info(f"Using cached prompt for {category}/{subcategory} (complexity: {complexity})")
            return self.prompt_cache[cache_key]
        
        # Determine if this is hardware or software focused
        is_hardware_focused = (
            category in self.hardware_categories or
            (category not in self.software_categories and random.random() < 0.3)  # 30% chance for mixed categories
        )
        
        # Generate the base template with specific complexity considerations
        template = self.generate_prompt_template(category, subcategory, complexity)
        
        # Set temperature based on complexity (more complex = more variation)
        temp_range = self.temperature_ranges.get(complexity, (0.7, 0.8))
        temperature = random.uniform(temp_range[0], temp_range[1])
        
        # First stage: Generate a creative prompt foundation
        base_prompt = self.api_client.call_gemini_api(template, temperature=temperature)
        
        if not base_prompt:
            logger.error("Failed to generate base prompt, using fallback")
            # Fallback to a basic template if API call fails
            base_prompt = f"Create a Python program for Raspberry Pi that implements a {subcategory} {category} application."
        
        # Get recommended libraries for the enrichment prompt
        recommended_libs = self.get_recommended_libraries(category, subcategory, complexity)
        library_recommendations = ""
        if recommended_libs:
            library_recommendations = f"Consider using appropriate libraries such as: {', '.join(recommended_libs[:4])}"
        
        # Get complexity-specific guidance
        complexity_guidance = self.generate_complexity_guidance(complexity)
        
        # Get integration-specific guidance
        integration_guidance = self.generate_integration_guidance(integration, complexity)
        
        # Get Pi model-specific guidance
        pi_model_guidance = self.generate_pi_model_guidance(pi_model)
        
        # Get context-specific guidance
        context_guidance = self.generate_context_guidance(context)
        
        # Add extensive code pattern examples for each complexity level
        code_pattern_examples = self._get_code_pattern_examples(complexity, style)
        
        # Get adjusted length limit for this category
        adjusted_length = self.get_adjusted_length_limit(category, complexity)
        
        # Create hardware-specific instructions based on category type
        if is_hardware_focused:
            hardware_instruction = """
            - Include appropriate hardware interaction for this application
            - Choose suitable hardware-specific libraries for the task
            - Describe any necessary GPIO connections or peripherals
            """
        else:
            hardware_instruction = """
            - Focus on the software aspects of the application
            - Only include hardware interactions if they're essential for this application
            - Don't unnecessarily include hardware libraries if the application doesn't need them
            """
        
        # Second stage: Enrich the prompt with specific parameters and comprehensive guidance.
        # Build the prompt from only the NON-EMPTY sections so that optional guidance
        # values (e.g. code_pattern_examples, which is currently always empty) never leave
        # a bare, dangling header with no content in the prompt sent to the LLM.

        # Always-present opening block with the core requirements.
        core_block = f"""
        Enhance the following coding prompt by integrating these specific requirements:

        Original prompt: "{base_prompt}"

        ADD THESE CORE REQUIREMENTS:
        1. Code should use {style} programming style
        2. Complexity level should be {complexity} - code MUST be approximately {adjusted_length} lines long (not significantly longer)
        3. Specifically designed for {pi_model}
        4. Should implement {integration} approach
        5. The use context is: {context}
        """

        # Optional (header, body) sections. A section is only included when its body
        # is non-empty after stripping. An empty header is allowed (used for the
        # free-form library recommendations, which carry no header of their own).
        optional_sections = [
            ("", library_recommendations),
            ("CODE PATTERN RECOMMENDATION:", code_pattern_examples),
            ("INTEGRATION SPECIFIC GUIDANCE:", integration_guidance),
            ("PI MODEL SPECIFIC GUIDANCE:", pi_model_guidance),
            ("CONTEXT SPECIFIC GUIDANCE:", context_guidance),
            ("COMPLEXITY SPECIFIC GUIDANCE:", complexity_guidance),
        ]

        # Always-present closing block with the critical implementation requirements.
        critical_block = f"""
        CRITICAL IMPLEMENTATION REQUIREMENTS:
        - Code must be COMPLETELY SELF-CONTAINED in a single file
        - USE ONLY libraries that are appropriate for this specific application
        - DO NOT use these forbidden libraries: {', '.join(self.DISALLOWED_LIBRARIES)}
        - DO NOT import from custom modules like 'sensor', 'data_logger', etc.
        - NEVER use custom module imports that aren't standard Python or Raspberry Pi libraries
        - Implement any needed classes directly in the main file
        {hardware_instruction}
        - Focus on realistic implementation that would work in an actual {context} environment
        - If code becomes lengthy, show complete but simplified implementations
        - Code should be approximately {adjusted_length} lines long (±20%)
        """

        # Assemble: core block, then only the non-empty optional sections, then critical block.
        prompt_parts = [core_block.strip()]
        for header, body in optional_sections:
            if body and body.strip():
                if header:
                    prompt_parts.append(f"{header}\n{body.strip()}")
                else:
                    prompt_parts.append(body.strip())
        prompt_parts.append(critical_block.strip())

        enrichment_prompt = "\n\n".join(prompt_parts) + "\n"

        enrichment_prompt += """
        Make the prompt cohesive, technical, and detailed. Ensure it specifies appropriate libraries, functions, and implementation details.
        Format as a direct instruction to a developer. Return ONLY the final enhanced prompt.
        """
        
        # Get the enriched prompt with slight randomness
        enriched_prompt = self.api_client.call_gemini_api(
            enrichment_prompt, 
            temperature=max(0.6, temperature - 0.1)  # Slightly lower temperature for consistency
        )
        
        if not enriched_prompt:
            logger.error("Failed to enrich prompt, using fallback with manual enrichment")
            # Fallback to manual enrichment
            enriched_prompt = f"{base_prompt}\n\nAdditional requirements:\n- Use {style} programming style\n- Code complexity: {complexity}\n- Target: {pi_model}\n- Integration: {integration}\n- Context: {context}\n- IMPORTANT: Use only appropriate libraries for this task"
        
        # Log the enriched prompt for debugging
        logger.debug(f"Generated enriched prompt for {category}/{subcategory} (complexity: {complexity})")
        
        # Cache the result
        self.prompt_cache[cache_key] = enriched_prompt
        
        # Manage cache size (simple strategy - clear if too many entries)
        if len(self.prompt_cache) > 1000:
            logger.info("Clearing prompt cache (size > 1000)")
            self.prompt_cache = {}
        
        return enriched_prompt
    
    def _get_code_pattern_examples(self, complexity: str, style: str) -> str:
        """
        Get code pattern examples tailored to complexity and style.
        
        Args:
            complexity: Code complexity level
            style: Programming style
            
        Returns:
            Example code patterns as guidance
        """
        if complexity == "beginner_basic" or style != "procedural":
            return ""  # Only provide patterns for non-beginner_basic procedural code
            
        # Example patterns for procedural style at different complexity levels
        patterns = {
            "beginner": """
            For this beginner-level code, structure your program like this:
            1. Import statements
            2. Constants and configuration
            3. Helper functions for specific tasks
            4. Main function that orchestrates the program flow
            5. Main guard (if __name__ == "__main__")
            """,
            
            "intermediate": """
            For this intermediate-level code, consider this structure:
            1. Import statements
            2. Constants and configuration
            3. Error handling functions
            4. Core functionality functions
            5. I/O and peripheral interaction functions
            6. Main program function with proper error handling
            7. Program execution with command-line argument parsing
            """,
            
            "advanced": """
            For this advanced-level procedural code, recommend this sophisticated structure:
            1. Import statements
            2. Constants and configuration
            3. Custom exception classes for domain-specific errors
            4. Configuration management functions
            5. Modular subsystem functions with comprehensive error handling
            6. Resource management functions (setup/teardown)
            7. Signal handlers for clean shutdown
            8. Logging configuration and utilities
            9. Main program orchestration with state management
            10. Entry point with argument parsing and validation
            """
        }
        
        return patterns.get(complexity, "")

    def generate_task_title(self, category: str, subcategory: str, context: str) -> str:
        """
        Generate a task title for a code example.
        
        Args:
            category: Code category
            subcategory: Specific type within category
            context: Use context
            
        Returns:
            Task title string
        """
        return f"Create a {subcategory.title()} {category.title()} Application for {context.title()}"