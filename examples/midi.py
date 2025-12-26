import time
import board
import busio
import usb_midi
import adafruit_midi
import sys
import time
import board
import busio
import analogio
import usb_midi
import adafruit_midi
import helper

from adafruit_midi.control_change import ControlChange


midi_channel = 1
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=midi_channel - 1)

midi_cc_fader0 = 1  # was const(1)
fader0 = analogio.AnalogIn(board.IO4)


def map_range_constrained_int_analog_midi(x):
    """Map value from analog 0..1023 range to 0..127 - constrain input range."""
    if x < 0:
        x = 0
    elif x > 65536:
        x = 65536
    return int(x * 127 // 65536)


def update_fader():
    value = map_range_constrained_int_analog_midi(fader0.value)
    print(f"{fader0.value:>5d}, {value:>3d}, {(fader0.value * 3.3) / 65536:>0.3f}V")
    midi.send(
        ControlChange(
            midi_cc_fader0,
            value,
        )
    )


def loop():
    update_fader()


def main():
    """Main handling."""
    print(4 * "\n")
    helper.wait_with_print(1)
    print("")
    print(42 * "*")
    print("Python Version: " + sys.version)
    print("board: " + board.board_id)
    print(42 * "*")

    while True:
        loop()
        time.sleep(0.5)


main()

from adafruit_midi.control_change import ControlChange


midi_channel = 1
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=midi_channel - 1)

midi_cc_fader0 = 1  # was const(1)
fader0 = analogio.AnalogIn(board.GP26_A0)


def update_speed_measurement():
    
    midi.send(ControlChange(midi_cc_fader0, fader0.value))

def main():
    update_fader()
    time.sleep(1.0)


while True:
    main()
