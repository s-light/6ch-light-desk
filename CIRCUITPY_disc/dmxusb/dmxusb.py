# SPDX-FileCopyrightText: 2025 Stefan Krüger s-light.eu
#
# SPDX-License-Identifier: MIT
#
# based
# https://github.com/DaAwesomeP/dmxusb/
# by Perry Naseck (DaAwesomeP)

"""
`s-light_dmxusb`
====================================================

CircuitPython module for the
TLC59711 or TLC5971 16-bit 12 channel LED PWM driver.
See examples/tlc59711_simpletest.py for a demo of the usage.

* Author(s): Tony DiCola, Stefan Kruger

Implementation Notes
--------------------

**Hardware:**

* Adafruit `12-Channel 16-bit PWM LED Driver - SPI Interface - TLC59711
  <https://www.adafruit.com/product/1455>`_ (Product ID: 1455)
  or TLC5971

**Software and Dependencies:**

* The API is mostly compatible to the DotStar / NeoPixel Libraries
    and is therefore also compatible with FancyLED.

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/s-light/CircuitPython_DMXUSB.git"

import time
import struct
import binascii
import microcontroller

from micropython import const

import usb_cdc

try:
    from typing import Dict, List, Optional, Tuple
    from collections.abc import Callable
except ImportError:
    pass

DEVICE_EMULATED_ULTRA_DMX_MICRO = {
    "NAME": b"emulated Ultra DMX Micro",
    "ESTA_ID": 0x6A6B,
    "DEVICE_ID": 0x3,
    "UNIVERSE_OUT": 1,
    "UNIVERSE_IN": 0,
}
DEVICE_EMULATED_DMXKING_UltraDMXPro = {
    "NAME": b"emulated DMXKing UltraDMXPro",
    "ESTA_ID": 0x6A6B,
    "DEVICE_ID": 0x2,
    "UNIVERSE_OUT": 2,
    "UNIVERSE_IN": 0,
}
DEVICE_DMXUSB = {
    "NAME": b"DMXUSB",
    "ESTA_ID": 0x7FF7,
    "DEVICE_ID": 0x42,
    "UNIVERSE_OUT": 3,
    "UNIVERSE_IN": 0,
}

# Byte order for Enttec/DMXKing protocol
STATE_START = const(0)
STATE_LABEL = const(1)
STATE_LEN_LSB = const(2)
STATE_LEN_MSB = const(3)
STATE_DATA = const(4)
STATE_END = const(5)

MSG_STARTMARK = 0x7E  # 126 0x7E '~'
MSG_ENDMARK = 0xE7  # 231 0xE7 'ç'

LABEL_UNDEFINED = const(-1)
LABEL_ESTA_ID_REQUEST = const(77)  # 0x4d 'M'
LABEL_DEVICE_ID_REQUEST = const(78)  # 0x4e 'N'
LABEL_SERIAL_NUMBER_REQUEST = const(10)  # 0xa '\n'
LABEL_WIDGET_PARAMETER_REQUEST = const(3)  # 0x03
LABEL_WIDGET_PARAMETER_EXTENDED_REQUEST = const(53)  # 0x35 '5'
LABEL_DMX_DATA = const(6)  # 0x06
LABEL_DMX_DATA2 = const(100)  # 0x64 'd'

LABEL_Lookup = {
    -1: "LABEL_UNDEFINED",
    77: "LABEL_ESTA_ID_REQUEST",
    78: "LABEL_DEVICE_ID_REQUEST",
    10: "LABEL_SERIAL_NUMBER_REQUEST",
    3: "LABEL_WIDGET_PARAMETER_REQUEST",
    53: "LABEL_WIDGET_PARAMETER_EXTENDED_REQUEST",
    6: "LABEL_DMX_DATA",
    100: "LABEL_DMX_DATA2",
}

MAX_CHANNELS = 512


def format_bytearray_as_int_string(bytearray_in: bytearray) -> string:
    in_as_str_array = [f"{x:>3d}" for x in bytearray_in]
    return f"[{
        ', '.join(
        in_as_str_array
        )
    }]"


class DMXUSB:
    """DMXUSB API

    :param ~busio.UART uart: An instance of the UART bus connected to the chip.
    :param int callback_dmxin: callback function - called every time a dmx transmission is received. fn(universe, buffer) (default=4)
    :param int universes_out: number of output universes (default=1)
    :param int serial_number: device serial number '0xAABBCCDD' (default=microcontroller.cpu.uid[2:] last 4 elements from uid)
    """

    def __init__(
        self,
        *,
        uart: UART,
        callback_dmxin: Callable[[int, bytearray], None],
        universes_out: int | None = None,
        serial_number: bytearray = None,
        mode=DEVICE_EMULATED_ULTRA_DMX_MICRO,
        # universes_in=1,
        debug=False,
    ):
        """Init."""
        self._debug = debug
        self._uart = uart
        self._mode = mode
        self._callback_dmxin = callback_dmxin

        self._universes_out = universes_out
        self._universes_in = 0
        if self._universes_out is None:
            self._universes_out = self._mode["UNIVERSE_OUT"]
        if self._debug:
            print(f"  _universes_out: {self._universes_out}")

        self._serial_number = serial_number
        if serial_number is None:
            self._serial_number = bytes(microcontroller.cpu.uid[2:])

        # self._state = STATE_START
        # self._label = LABEL_UNDEFINED
        # self._msg_length = 0
        # self._buffer_data_clear()
        # self._last_action = time.monotonic()
        self._buffer_data = bytearray(MAX_CHANNELS)
        # print("self._buffer_data", self._buffer_data)
        self._reset_receive_statemanschine()

        # usb_cdc.console.timeout = 1.0

    def _send_message(self, label, data: bytearray) -> None:
        _data = [
            MSG_STARTMARK,
            label,
            (len(data) & 0xFF),
            ((len(data) + 1) >> 8),
        ]
        _data.extend(data)
        _data.append(MSG_ENDMARK)
        send_bytes = self._uart.write(bytearray(_data))
        if self._debug:
            print(f"send '{LABEL_Lookup[label]}' ({send_bytes})")
        return send_bytes

    def _send_ESTA_ID(self) -> None:
        data = []
        data.extend(bytes(divmod(self._mode["ESTA_ID"], 0x100)))
        data.extend(b"DMXUSB")
        self._send_message(LABEL_ESTA_ID_REQUEST, data)

    def _send_DEVICE_ID(self) -> None:
        data = []
        data.extend(bytes(divmod(self._mode["DEVICE_ID"], 0x100)))
        data.extend(self._mode["NAME"])
        self._send_message(LABEL_DEVICE_ID_REQUEST, data)

    def _send_SERIAL_NUMBER(self) -> None:
        data = []
        data.extend(self._serial_number)
        self._send_message(LABEL_SERIAL_NUMBER_REQUEST, data)

    def _send_WIDGET_PARAMETER(self) -> None:
        data = [
            # firmware version LSB: 3 (v0.0.4)
            0x03,
            # firmware version MSB: 0
            0x00,
            # DMX output break time in 10.67 microsecond units: 9 (TODO: CALCUALTE WITH BAUDRATE)
            0x09,
            # DMX output Mark After Break time in 10.67 microsecond units: 1 (TODO: CALCUALTE WITH BAUDRATE)
            0x01,
            # DMX output rate in packets per second: 40 (TODO: CALCUALTE WITH BAUDRATE)
            0x28,
        ]
        self._send_message(LABEL_WIDGET_PARAMETER_REQUEST, data)

    def _send_WIDGET_PARAMETER_EXTENDED(self) -> None:
        data = [
            self._universes_out,  # universes_out
            self._universes_in,  # universes_in
        ]
        self._send_message(LABEL_WIDGET_PARAMETER_EXTENDED_REQUEST, data)

    def _handle_DMX_data_received(self) -> None:
        if self._debug:
            print("_handle_DMX_data_received()")
            print(f"  data: {format_bytearray_as_int_string(self._buffer_data)}")
        if (
            self._label == LABEL_DMX_DATA
            and self._mode == DEVICE_EMULATED_ULTRA_DMX_MICRO
        ):
            self._callback_dmxin(universe=0, data=self._buffer_data)
        elif (
            self._label == LABEL_DMX_DATA
            and self._mode == DEVICE_EMULATED_DMXKING_UltraDMXPro
        ):
            self._callback_dmxin(universe=0, data=self._buffer_data)
            self._callback_dmxin(universe=1, data=self._buffer_data)
        elif self._label == LABEL_DMX_DATA and self._mode == DEVICE_DMXUSB:
            for universe_index in range(self._universes_out):
                self._callback_dmxin(universe=universe_index, data=self._buffer_data)
        elif (
            self._label == LABEL_DMX_DATA2
            and self._mode == DEVICE_EMULATED_DMXKING_UltraDMXPro
        ):
            self._callback_dmxin(universe=0, data=self._buffer_data)
        elif (
            self._label == LABEL_DMX_DATA2 + 1
        ) and self._mode == DEVICE_EMULATED_DMXKING_UltraDMXPro:
            self._callback_dmxin(universe=1, data=self._buffer_data)
        elif self._mode == DEVICE_DMXUSB:
            self._callback_dmxin(
                universe=self._label - LABEL_DMX_DATA2, data=self._buffer_data
            )

    def _buffer_data_clear(self) -> None:
        self._buffer_data_index = 0
        self._buffer_data[:] = bytearray(len(self._buffer_data))

    def _label_is_DMX_receive(self) -> bool:
        return self._label == LABEL_DMX_DATA or (
            self._label >= LABEL_DMX_DATA2
            and self._label < LABEL_DMX_DATA2 + self.universes_out
        )

    def _reset_receive_statemanschine(self):
        if self._debug:
            print(f"_reset_receive_statemanschine...")
        self._state = STATE_START
        self._label = LABEL_UNDEFINED
        self._msg_length = 0
        self._buffer_data_clear()
        self._last_action = time.monotonic()

    def _parse(self) -> None:
        # if self._debug:
        #     print(
        #         f"parse: label: '{self._label}' {LABEL_Lookup[self._label]} _msg_length: '{self._msg_length}'"
        #         # f" _data_rest_count: '{self._data_rest_count}' "
        #     )
        if self._label is LABEL_ESTA_ID_REQUEST:
            self._send_ESTA_ID()
        elif self._label is LABEL_DEVICE_ID_REQUEST:
            self._send_DEVICE_ID()
        elif self._label is LABEL_SERIAL_NUMBER_REQUEST:
            self._send_SERIAL_NUMBER()
        elif self._label is LABEL_WIDGET_PARAMETER_REQUEST:
            self._send_WIDGET_PARAMETER()
        elif self._label is LABEL_WIDGET_PARAMETER_EXTENDED_REQUEST:
            self._send_WIDGET_PARAMETER_EXTENDED()
        elif self._label_is_DMX_receive():
            self._handle_DMX_data_received()

    def _receive_and_parse(self, b: byte) -> None:
        # if self._debug:
        #     print(f"{self._state} - b: {b}")

        if self._state is STATE_START:
            if b[0] == MSG_STARTMARK:
                self._state = STATE_LABEL
            else:
                # ?? this should never happen?!
                pass
        elif self._state is STATE_LABEL:
            self._label = b[0]
            if self._label_is_DMX_receive():
                self._buffer_data_clear()
            self._state = STATE_LEN_LSB
        elif self._state is STATE_LEN_LSB:
            self._msg_length = b[0]
            self._state = STATE_LEN_MSB
        elif self._state is STATE_LEN_MSB:
            self._msg_length |= b[0] << 8
            if self._msg_length > 0:
                self._state = STATE_DATA
            else:
                self._state = STATE_END
            self._data_rest_count = self._msg_length
        elif self._state is STATE_DATA:
            if self._buffer_data_index <= len(self._buffer_data):
                if self._buffer_data_index > 0:
                    # add dmx data to buffer.
                    # DMX channels start at 1. buffer starts at 0
                    self._buffer_data[self._buffer_data_index - 1] = b[0]
                self._buffer_data_index += 1
            # decrease expected rest data
            self._data_rest_count = self._data_rest_count - 1
            if self._data_rest_count == 0:
                self._state = STATE_END
        elif self._state is STATE_END:
            if b[0] == MSG_ENDMARK:
                self._parse()
                self._state = STATE_START
            else:
                # ?? this should never happen?!
                pass
        else:
            self._state = STATE_START

    def update(self) -> None:
        """listen for incoming dmx data.

        - check serial for new data
        - if available add to buffer
        - if package finished parse
        """

        available = self._uart.in_waiting
        while available:
            b = self._uart.read(1)
            self._last_action = time.monotonic()
            self._receive_and_parse(b)
            available = self._uart.in_waiting
        if self._state is not STATE_START and (
            time.monotonic() - self._last_action > 0.1
        ):
            self._reset_receive_statemanschine()

        available = usb_cdc.console.in_waiting
        while available:
            raw = usb_cdc.console.read(1)
            # print(raw)
            if raw != b"\r":
                send_bytes = self._uart.write(raw)
                print("send", raw)
            else:
                print()
            available = usb_cdc.console.in_waiting

        # if available:
        #     raw = usb_cdc.console.readline()
        #     text = raw.decode("utf-8")
        #     print(text)
        #     if text.startswith("!"):
        #         print("found !. sending rest to uart..")
        #         send_bytes= self._uart.write(text[1:])
        #         print("send_bytes:", send_bytes)
