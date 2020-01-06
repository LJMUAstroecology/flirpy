# ![logo](logo.png)

![coverage](coverage.svg) [![Documentation Status](https://readthedocs.org/projects/flirpy/badge/?version=latest)](https://flirpy.readthedocs.io/en/latest/?badge=latest)

flirpy is a Python library to interact with FLIR thermal imaging cameras and images.

It aims to be a one-stop-shop to:

* Interact and query cameras via serial
* Capture raw images
* Convert FLIR file formats (e.g. seq, fff, tmc, tfc) to geotagged readable images
* Convert raw images to radiometric images
* Extract and plot GPS traces from image sequences (e.g. from drones)

The library has been tested with:

* FLIR Tau (serial only)
* FLIR Boson (serial and image capture)
* FLIR Duo Pro R (image post-processing)
* TeAx Fusion Zoom (image post-processing)
* FLIR Lepton (PureThermal board, capture+telemetry only)

Coming soon

* FLIR Lepton low level (SPI)

**It is strongly recommended that you use Python 3**. I have tried to ensure that certain functions are portable between Python 2 and 3, mainly those involved with camera communication (for example if you want to use flirpy with ROS, most of the important stuff works). However, some file IO is hit and miss on Python 2 due to differences in regexes. Python 2 is effectively end of life and while I'd like to support both, it's a low priority. Submit a PR if you like!

## Library organisation

The library is organised into logical sections:

* `flirpy.camera` contains classes to communicate with FLIR camera cores directly
* `flirpy.io` contains claseses to deal with thermal image formats
* `flirpy.util` contains helper functions e.g. raw conversion

## Utilities

Flirpy includes a convenience utility `split_seqs` for splitting FLIR sequence (SEQ) files.

Once installed, you can run:

```bash
$ split_seqs -h
usage: split_seqs [-h] [-o OUTPUT] -i INPUT [-v VERBOSITY]

Split all files in folder.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output folder
  -i INPUT, --input INPUT
                        Input file mask
  -v VERBOSITY, --verbosity VERBOSITY
                        Logging level
```

`split_seqs` accepts either a directory, a specific filename, or a wildcard string (e.g. `"./my/data/flight_*.SEQ"`). If you use wildcards, be sure to enclose the argument in quotes, otherwise your shell will expand the wildcard before running the program and confuse it. If you specify a directoy, all SEQ files in that diretory will be used.

Files will be extracted to folders with the same base name as the SEQ file, for example `20180101_1030.SEQ` will be extracted to `20180101_1030`, etc. By default the splitter will three kinds of files, separated by subfolder.

* Raw (FFF) files with metadata text files
* Radiometric 16-bit tiff images
* Preview 8-bit RGB representations of the radiometric data

The tiff images will be geotagged if GPS information is present in the raw data.

Output images are numbered. If SEQ file 1 contains 1800 frames, the first frame from SEQ file 2 will be numbered 1800.

## Installation

Flirpy has been tested with Python 3 and _may_ work on Python 2. It is always recommended that you install packages inside a virtualenv or Conda environment.

Simply install using `pip`:

```
pip install flirpy
```

Or you can clone the repository and run:

``` bash
pip install .
```

Or:

``` bash
python setup.py install
```

Using `pip` is preferable, as it will let you uninstall the package if you need.

flirpy is distributed with a copy of [Exiftool](https://sno.phy.queensu.ca/~phil/exiftool/) which is used to extract metadata from certain file formats.

### Installation on ARM (e.g. Raspberry Pi)

Flirpy mostly works well, and has been tested, on the Raspberry Pi. If you're building from scratch, you need to install a few things manually. Try to use Python 3 if you can.

It's recommended that you first install the Python dependencies using `pip` in combination with [piwheels](https://www.piwheels.org/). For whatever reason, `setuptools` does not find these files, so it will fail if e.g. OpenCV isn't installed already. Once you've set up piwheels (it should be automatic on Raspbian if you've installed pip3) run:

``` bash
pip3 install -r requirements.txt
```

You may need to install some dependencies for OpenCV, for example `libjasper-dev`.

You should also install Exiftool manually with `sudo apt install exiftool`.

If you're on a platorm like Arm64 where `opencv-python-headless` is not available, then bad luck, you need to build OpenCV from scratch. This is straightforward nowadays, but it's a bit involved.

## Grab images

Here's a very simple example of grabbing an image using a Boson or Lepton:
    
``` python
from flirpy.camera.lepton import Lepton

camera = Lepton()
image = camera.grab()
camera.close()
```

If you're using a PureThermal Lepton you can also check frame telemetry if enabled:

```python
camera.major_version
camera.minor_version
camera.uptime_ms
camera.status # see datasheet
camera.revision
camera.frame_count
camera.frame_mean # too low?
camera.fpa_temp_k
camera.ffc_temp_k
camera.ffc_elapsed_ms
camera.agc_roi
camera.clip_high
camera.clip_low
camera.video_format
```

Flirpy automatically locates your camera and captures a 16-bit (raw) image:

``` python
from flirpy.camera.boson import Boson

camera = Boson()
image = camera.grab()
camera.close()
```

## Driver problems on Windows

Occasionally Windows can do some bizarre things and forget that USB devices are cameras. This will stop the camera from being discoverable by flirpy (and usable by software including OpenCV).

You can solve this by going to device manager, right clicking on the USB device and selecting "Update Driver". Choose "Browse my computer ... " and then "Let me pick ... ". Choose the "USB Video Device" driver.


## Tests

To run the test suite:

``` bash
pip install pytest pytest-cov
pytest --cov=flirpy test
```

Some tests are hardware dependent, e.g. for cameras, so expect them to fail unless you own and have a camera to try them with. Hardware tests are skipped by default if the requisite camera is not plugged in.

The repository includes some small representative examples of image files (e.g. SEQ). It is tested and is routinely used with flight data from FLIR Duo cameras, so larger files aren't a problem, but they're too large to include in the repository.

If you're testing on Python 2:
```bash
pip install pytest pytest-cov backports.tempfile
pytest --cov=flirpy test
```
