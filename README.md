# ![logo](logo.png)

![coverage](coverage.svg)

flirpy is a Python library to interact with FLIR thermal imaging cameras and images.

It aims to be a one-stop-shop to:

* Interact and query cameras via serial interface
* Capture raw images
* Convert FLIR file formats (e.g. seq, fff, tmc, tfc) to readable images
* Convert raw images to radiometric images
* Extract and plot GPS traces from image sequences (e.g. from drones)

The library has been tested with:

* FLIR Tau (serial only)
* FLIR Boson (serial and image capture)
* FLIR Duo Pro R (image post-processing)
* TeAx Fusion Zoom (image post-processing)

Support for the Lepton is coming soon, but will probably be limited to the Raspberry Pi for the time being.

## Library

The library is organised into logical sections:

* `flirpy.camera` contains classes to communicate with FLIR camera cores directly
* `flirpy.io` contains claseses to deal with thermal image formats
* `flirpy.util` contains helper functions e.g. raw conversion

## Installation

Simply run 

``` bash
pip install -r requirements.txt
python setup.py install
```

flirpy is distributed with a copy of [Exiftool](https://sno.phy.queensu.ca/~phil/exiftool/) which is used to extract metadata from certain file formats. 

## Tests

Some tests are hardware dependent, e.g. for cameras, so expect them to fail unless you own and have a camera to try them with. Others require files for testing things like extraction, these are quite large currently so are not distributed with the repo. You can use any .SEQ file, in principle.

