# grideye-driver
Python driver for the Panasonic AMG88 Grid-EYE infrared array sensor.

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/rogiervandergeer/grideye-driver/Continuous%20Integration) 
![PyPI](https://img.shields.io/pypi/v/grideye-driver)
![PyPI - License](https://img.shields.io/pypi/l/grideye-driver)
![PyPI - Downloads](https://img.shields.io/pypi/dm/grideye-driver) 

## Installation

The package is available on [PyPI](https://pypi.org/project/grideye-driver/). Installation is can be done with your favourite package manager. For example:

```bash
pip install grideye-driver
```

## Usage

In order to initialise the device we need an open `SMBus` object. 
Depending on the machine that you are running on you may need to provide another bus number or path:
```python
from grideye import GridEye
from smbus2 import SMBus


with SMBus(1) as bus:
    device = GridEye(bus=bus)
```

The I2C address of the GridEye sensor is either `0x68` or `0x69`. 
The default of the `GridEye` class is `0x69`, and you can specify another address
by providing for example `GridEye(bus=bus, address=0x68)`.

Basic usage is as simple as:
```python
with SMBus(1) as bus:
    with GridEye(bus=bus) as device:
        image = device.image
```

The `image` variable will be an 8x8 list-of-lists containing 64 floats - each representing the
measured temperature in degrees Celsius of a pixel.

### Device Mode

The device is instantiated in sleep mode. All functionality is unavailable
in sleep mode - except for waking the device. The `asleep` property will be `True`.

The device can be woken with the `wake()`-method, and put back to sleep with
the `sleep()`-method:
```python
device = GridEye(bus=bus)
device.wake()
image = device.image
device.sleep()
```
Or instead, one can use the `GridEye` as context manager, which will
automatically wake the device upon entering the context, and put
it back to sleep when exiting the context - even in case of an error:
```python
with GridEye(bus=bus) as device:
    image = device.image
```

or 
```python
device = GridEye(bus=bus)
with device:
    image = device.image
```

### Settings

The Grid-EYE has two framerate settings: 1 fps or 10 fps.
The framerate can be read and set with the `frame_rate`-property.
The framerate value is always a `grideye.FrameRate` enum object:
```python
device.frame_rate
>>> FrameRate.low   # Low is 1fps
```
It can be set by providing a `FrameRate` object:
```python
from grideye import FrameRate
device.frame_rate = FrameRate.high
```
or by a string with value `"low"` or `"high"`:
```python
device.frame_rate = "low"
```

To reduce noise, the Grid-EYE has a moving average feature.
It can be controlled by setting the `moving_average`-property or
either `True` (enabled) or `False` (disabled).

### Measurements

Two properties are available:
```python
temp = device.device_temperature
image = device.image
```
The first returns the internal device temperature as a float,
the latter an 8x8 matrix of sensor readings.

### Interrupts

The Grid-EYE sports three types of interrupt: global, pixel-level and overflow.

The interrupts are configured with the `interrupt_config`-property,
with is an `InterruptConfig`-object. This object has five attributes:

- An `enabled`-flag. If this is `False`, then the interrupt status flag is always `True`.
- Two limits: `upper_limit` and `lower_limit`.
- An `absolute`-flag. If this is `False`, then the upper and lower limit represent the minimum differences compared to the previous measurement to trigger the interrupt. Otherwise, the upper and lower values represent the absolute values below or above which the interrupt will be triggered.
- The `hysteresis`, which represents the hysteresis applied to the limits.

For example:
```python
from grideye import InterruptConfig

device.interrupt_config = InterruptConfig(
    upper_limit=30,
    lower_limit=5,
    hysteresis=1,
    enabled=True,
    absolute=True
)
```

The interrupts can be easily disabled by calling `device.disable_interrupts()`.

If any pixel breaches the limits as defined in the interrupt config,
the interrupt-flag (`device.interrupt`) will be `True`. This
can be reset to `False` by calling `reset_interrupt`.

Additionally, the interrupt status of each pixel is available
as an 8x8 boolean matrix in `device.pixel_interrupt`. These
values will not be changed by `reset_interrupt`: to clear
those you will need to call `reset_flags()`.

Finally, there is an `overflow`-property, which will be set to True
if the internal ADC of the Grid-EYE has overflowed. This
can be reset by calling `reset_overflow()`, or by calling `reset_flags()`.

## References

[Panasonic product page](https://industry.panasonic.eu/products/components/sensors/ir-thermophile-array-sensor-grid-eye)
