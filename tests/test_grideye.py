from pytest import approx, mark

from grideye.conversion import (
    _byte_to_bools,
    _bytes_to_temperature,
    _bytes_to_thermistor_temperature,
    _temperature_to_bytes,
)


@mark.parametrize(
    "value, result",
    [
        (0b0000_0001, [False, False, False, False, False, False, False, True]),
        (0b0100_0000, [False, True, False, False, False, False, False, False]),
        (0b1000_0001, [True, False, False, False, False, False, False, True]),
        (0b1111_1111, [True] * 8),
        (0b0000_0000, [False] * 8),
    ],
)
def test_byte_to_bools(value, result):
    assert _byte_to_bools(value) == result


@mark.parametrize(
    "lsb, msb, temperature",
    [
        (0b1111_0100, 0b0001, 125),
        (0b0110_0100, 0b0000, 25),
        (0b0000_0001, 0b0000, 0.25),
        (0b0000_0000, 0b0000, 0),
        (0b1111_1111, 0b1111, -0.25),
        (0b1001_1100, 0b1111, -25),
        (0b0010_0100, 0b1111, -55),
    ],
)
def test_convert_temperature(lsb: int, msb: int, temperature: float):
    assert _bytes_to_temperature(lsb, msb) == approx(temperature)
    assert _temperature_to_bytes(temperature) == (lsb, msb)


@mark.parametrize(
    "lsb, msb, temperature",
    [
        (0b1111_1111, 0b0111, 127.9375),
        (0b1001_0000, 0b0001, 25),
        (0b0000_0100, 0b0000, 0.25),
        (0b0000_0000, 0b0000, 0),
        (0b0000_0100, 0b1000, -0.25),
        (0b1011_1011, 0b1011, -59.6875),
    ],
)
def test_convert_temperature_thermistor(lsb: int, msb: int, temperature: float):
    assert _bytes_to_thermistor_temperature(lsb, msb) == approx(temperature)
