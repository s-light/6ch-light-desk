# 6ch-light-desk
6ch light dmx theater control desk.

simple circuitpython based 6ch-light-desk

> [!WARNING]
> WIP
> currently the following points are just targets.

## usage
the device works in two modes:
the mode is selected by the slide-switch at the back of the device.


### standalone
some sort of mapping between the 7 faders and 6 buttons and the dmx output is programmed.
this mapping is configured in the file `mapping.py`

### interface
the fader and buttons are used to control [QLC+](https://www.qlcplus.org/) on an computer via USB-MIDI.
<!-- or USB-Network-Interface -->
additionally the device can be used as DMX-output interface.
for this it emulates the ENTTEC DMX USB Pro Widget API Specification 1.44

based loosely on 
- https://github.com/DaAwesomeP/dmxusb/blob/master/src/DMXUSB.cpp#L104
- https://github.com/OpenLightingProject/rgbmixer


## HW

- controller [CYTRON MAKER PI RP2040](https://github.com/CytronTechnologies/MAKER-PI-RP2040)
- motor 
    - [TT Motor All-Metal Gearbox - 1:90 Gear Ratio, Input 3VDC up to 6VDC](https://eckstein-shop.de/TTMotorAll-MetalGearbox-13A90GearRatio2CInput3VDCupto6VDC)
    - [Adafruit 3777](https://www.adafruit.com/product/3777) ([shop](https://eckstein-shop.de/AdafruitDCGearboxMotor-22TTMotor22-200RPM-3to6VDC))
    - or similar
- 38KHz IR receiver [VISHAY TSOP 31238](https://www.vishay.com/docs/82492/tsop312.pdf) ([shop](https://www.reichelt.de/de/de/shop/produkt/ir-empfaenger-module_38khz_90_side-view-107210))