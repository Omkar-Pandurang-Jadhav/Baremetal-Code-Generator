"""Hardware rules and constraints for STM32F103VB microcontroller.

Contains valid pins, peripherals, pin mappings, and configuration
constraints specific to the STM32F103VB device.
"""

# Valid GPIO ports and pin counts for STM32F103VB
GPIO_PORTS = {
    "A": 16,  # PA0-PA15
    "B": 16,  # PB0-PB15
    "C": 16,  # PC0-PC15
    "D": 16,  # PD0-PD15
    "E": 16,  # PE0-PE15
}

# Generate all valid pin names
VALID_PINS = set()
for port, count in GPIO_PORTS.items():
    for i in range(count):
        VALID_PINS.add(f"P{port}{i}")

# Valid peripheral names
VALID_PERIPHERALS = {
    "GPIO",
    "USART1", "USART2", "USART3",
    "SPI1", "SPI2",
    "I2C1", "I2C2",
    "ADC1", "ADC2",
    "TIM1", "TIM2", "TIM3", "TIM4",
    "CAN1",
    "USB",
}

# Peripheral function names
PERIPHERAL_FUNCTIONS = {
    "USART1": ["TX", "RX", "CK", "CTS", "RTS"],
    "USART2": ["TX", "RX", "CK", "CTS", "RTS"],
    "USART3": ["TX", "RX", "CK", "CTS", "RTS"],
    "SPI1":   ["MOSI", "MISO", "SCK", "NSS"],
    "SPI2":   ["MOSI", "MISO", "SCK", "NSS"],
    "I2C1":   ["SDA", "SCL"],
    "I2C2":   ["SDA", "SCL"],
    "ADC1":   ["IN0", "IN1", "IN2", "IN3", "IN4", "IN5", "IN6", "IN7"],
    "ADC2":   ["IN0", "IN1", "IN2", "IN3", "IN4", "IN5", "IN6", "IN7"],
    "TIM1":   ["CH1", "CH2", "CH3", "CH4"],
    "TIM2":   ["CH1", "CH2", "CH3", "CH4"],
    "TIM3":   ["CH1", "CH2", "CH3", "CH4"],
    "TIM4":   ["CH1", "CH2", "CH3", "CH4"],
}

# Default pin mappings for peripherals (no remap)
PERIPHERAL_PIN_MAP = {
    "USART1": {"TX": "PA9", "RX": "PA10", "CK": "PA8", "CTS": "PA11", "RTS": "PA12"},
    "USART2": {"TX": "PA2", "RX": "PA3", "CK": "PA4", "CTS": "PA0", "RTS": "PA1"},
    "USART3": {"TX": "PB10", "RX": "PB11", "CK": "PB12", "CTS": "PB13", "RTS": "PB14"},
    "SPI1":   {"MOSI": "PA7", "MISO": "PA6", "SCK": "PA5", "NSS": "PA4"},
    "SPI2":   {"MOSI": "PB15", "MISO": "PB14", "SCK": "PB13", "NSS": "PB12"},
    "I2C1":   {"SDA": "PB7", "SCL": "PB6"},
    "I2C2":   {"SDA": "PB11", "SCL": "PB10"},
    "ADC1":   {"IN0": "PA0", "IN1": "PA1", "IN2": "PA2", "IN3": "PA3",
               "IN4": "PA4", "IN5": "PA5", "IN6": "PA6", "IN7": "PA7"},
    "ADC2":   {"IN0": "PA0", "IN1": "PA1", "IN2": "PA2", "IN3": "PA3",
               "IN4": "PA4", "IN5": "PA5", "IN6": "PA6", "IN7": "PA7"},
}

# Valid GPIO modes
VALID_MODES = {"input", "output", "alternate", "analog"}

# Valid output types
VALID_OUTPUT_TYPES = {"push-pull", "open-drain"}

# Valid speeds
VALID_SPEEDS = {"2MHz", "10MHz", "50MHz"}

# Valid pull configurations
VALID_PULL = {"pull-up", "pull-down", "floating"}
