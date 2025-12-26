import usb_midi
import usb_hid

# disable hid so we have some free endpoints for midi...
usb_hid.disable()
usb_midi.enable()
