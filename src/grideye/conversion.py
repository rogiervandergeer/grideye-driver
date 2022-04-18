from typing import List, Tuple


def _byte_to_bools(value: int) -> List[bool]:
    """Convert a byte to a list of bools."""
    return [(value >> i) & 0x01 > 0 for i in reversed(range(8))]


def _bytes_to_temperature(lsb: int, msb: int) -> float:
    temperature = (msb << 8) + lsb
    if temperature & (1 << 11):  # if temperature is negative
        temperature -= 1 << 12  # two's complement
    return temperature * 0.25


def _bytes_to_thermistor_temperature(lsb: int, msb: int) -> float:
    temperature = (msb << 8) + lsb
    if temperature & (1 << 11):  # if temperature is negative
        temperature = -(temperature & ~(1 << 11))
    return temperature * 0.0625


def _temperature_to_bytes(temperature: float) -> Tuple[int, int]:
    temperature = int(round(temperature * 4))
    if temperature < 0:
        temperature = temperature + (1 << 12)
    msb, lsb = (temperature >> 8), temperature & 0xFF
    return lsb, msb
