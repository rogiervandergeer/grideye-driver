from dataclasses import dataclass
from enum import Enum
from time import sleep
from typing import List, Union

from smbus2 import SMBus

from .conversion import (
    _byte_to_bools,
    _bytes_to_temperature,
    _bytes_to_thermistor_temperature,
    _temperature_to_bytes,
)


class FrameRate(bytes, Enum):
    low = b"\x01"  # 1fps
    high = b"\x00"  # 10fps


@dataclass
class InterruptConfig:
    upper_limit: float
    lower_limit: float
    hysteresis: float
    absolute: bool = True
    enabled: bool = True


class GridEye:
    def __init__(
        self,
        bus: SMBus,
        address: int = 0x69,
    ):
        self.address = address
        self.bus = bus
        self.sleep()  # Default mode is sleeping.

    # =========== #
    # Device Mode #
    # =========== #

    @property
    def asleep(self) -> bool:
        """Returns True is the device is asleep."""
        return self.device_temperature == 2048

    def sleep(self) -> None:
        """Set the device to sleep mode.

        This will render the device useless until a wake() command is performed."""
        if not self.asleep:
            self._write(0x00, b"\x10")
            sleep(0.05)

    def wake(self) -> None:
        """Set the device to normal mode.

        If the device was asleep, perform a device reset.
        We need to wait for at least two frames before we can take any measurements."""
        if self.asleep:
            self._write(0x00, b"\x00")
            sleep(0.05)
            self._write(0x01, b"\x3f")  # Perform initial reset.
            sleep(0.002)
            self.reset_flags()
            sleep(3 if self.frame_rate.name == "low" else 0.3)

    def __enter__(self) -> "GridEye":
        self.wake()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.sleep()

    # ==================== #
    # Device Configuration #
    # ==================== #

    @property
    def frame_rate(self) -> FrameRate:
        """Get or set the frame rate setting.

        The frame rate can take two values:
        - FrameRate.low, which equals to 1 fps,
        - FrameRate.high, which equals to 10 fps.

        When setting, FrameRate objects as well as the strings 'low' and 'high' are accepted.
        """
        return FrameRate(self._read(0x02))

    @frame_rate.setter
    def frame_rate(self, value: Union[FrameRate, str]) -> None:
        if isinstance(value, str):
            value = FrameRate[value]
        self._write(0x02, value=FrameRate(value).value)

    @property
    def moving_average(self) -> bool:
        """Get or set the moving average mode.

        When False, moving average is disabled. When True, it is enabled."""
        return bool(self._read(0x07)[0] & 0x20)

    @moving_average.setter
    def moving_average(self, value: bool) -> None:
        self._write(0x1F, b"\x50")
        self._write(0x1F, b"\x45")
        self._write(0x1F, b"\x57")
        self._write(0x1F, b"\x20" if value else b"\x00")
        self._write(0x1F, b"\x00")

    # ============ #
    # Measurements #
    # ============ #

    @property
    def device_temperature(self) -> float:
        """Read the device temperature."""
        return _bytes_to_thermistor_temperature(*self._read(0x0E, length=2))

    @property
    def image(self) -> List[List[float]]:
        """Read sensor image data.

        The result is an 8x8 matrix of pixel values in degrees Celsius."""
        # SMBus does not allow to read everything in one go.
        data = [self._read(0x80 + line * 16, length=16) for line in range(8)]
        return [
            [
                _bytes_to_temperature(line[pixel], line[pixel + 1])
                for pixel in reversed(range(0, 16, 2))
            ]
            for line in data[::-1]
        ]

    # ========== #
    # Interrupts #
    # ========== #

    def reset_flags(self) -> None:
        """Reset the interrupt and overflow flags.

        This clears the interrupt and overflow flags, as well as the pixel interrupt flags."""
        self._write(0x01, b"\x30")

    def disable_interrupts(self) -> None:
        """Disable the interrupts.

        This will set the interrupt status flag to True."""
        self.interrupt_config = InterruptConfig(
            enabled=False, absolute=False, upper_limit=0, lower_limit=0, hysteresis=0
        )

    @property
    def interrupt_config(self) -> InterruptConfig:
        """Get or set the interrupt configuration."""
        status_data = self._read(0x03)[0]
        threshold_data = self._read(0x08, length=6)
        return InterruptConfig(
            upper_limit=_bytes_to_temperature(threshold_data[0], threshold_data[1]),
            lower_limit=_bytes_to_temperature(threshold_data[2], threshold_data[3]),
            hysteresis=_bytes_to_temperature(threshold_data[4], threshold_data[5]),
            enabled=bool(status_data & 0b01),
            absolute=bool(status_data & 0b10),
        )

    @interrupt_config.setter
    def interrupt_config(self, value: InterruptConfig) -> None:
        self._write(
            0x08,
            bytes(
                _temperature_to_bytes(value.upper_limit)
                + _temperature_to_bytes(value.lower_limit)
                + _temperature_to_bytes(value.hysteresis)
            ),
        )
        self._write(
            0x03,
            ((value.enabled * 0b01) | (value.absolute * 0b10)).to_bytes(
                length=1, byteorder="little"
            ),
        )
        self.reset_interrupt()

    @property
    def interrupt(self) -> bool:
        """Interrupt status flag.

        If any pixel value breaches the interrupt limits, this flag is set to True.
        This flag is always True when interrupts are disabled."""
        return bool(self._read(0x04)[0] & 0x02)

    def reset_interrupt(self) -> None:
        """Reset the interrupt status flag.

        This does not clear the pixel interrupt data."""
        self._write(0x05, b"\x02")

    @property
    def overflow(self) -> bool:
        """Overflow status flag.

        If this is True, the internal ADC has overflowed."""
        return bool(self._read(0x04)[0] & 0x04)

    def reset_overflow(self) -> None:
        """Reset the overflow status flag."""
        self._write(0x05, b"\x04")

    @property
    def pixel_interrupt(self) -> List[List[bool]]:
        """Pixel interrupt status flags.

        This is an interrupt flag per pixel, presented as an 8x8 matrix of booleans."""
        return [
            _byte_to_bools(register)
            for register in reversed(self._read(0x10, length=8))
        ]

    def _read(self, register: int, length: int = 1) -> bytes:
        return bytes(
            self.bus.read_i2c_block_data(self.address, register=register, length=length)
        )

    def _write(self, register: int, value: bytes) -> None:
        self.bus.write_i2c_block_data(self.address, register=register, data=list(value))


__all__ = [GridEye, FrameRate, InterruptConfig]
