class code:
    def __init__(self, code = 0, cmd_bytes = 0, reply_bytes = 0):
        self.code = code
        self.cmd_bytes = cmd_bytes
        self.reply_bytes = reply_bytes

# General Commands

NO_OP = code(0x00, 0, 0)
SET_DEFAULTS = code(0x01, 0, 0)
CAMERA_RESET = code(0x02, 0, 0)
RESTORE_FACTORY_DEFAULTS = code(0x03, 0, 0)
SERIAL_NUMBER = code(0x04, 0, 8)
GET_REVISION = code(0x05, 0, 8)

# Gain Commands

GET_GAIN_MODE = code(0x0A, 0, 2)
SET_GAIN_MODE = code(0x0A, 2, 2)

# FFC Commands

GET_FFC_MODE = code(0x0B, 0, 2)
SET_FFC_MODE = code(0x0B, 2, 2)

GET_FFC_NFRAMES = code(0x0B, 4, 2)
SET_FFC_NFRAMES = code(0x0B, 4, 2)

DO_FFC_SHORT = code(0x0C, 0, 0)
DO_FFC = code(0x0C, 2, 2)

GET_FFC_PERIOD = code(0x0D, 0, 4)
SET_FFC_PERIOD_LOW_GAIN = code(0x0D, 2, 2)
SET_FFC_PERIOD_HIGH_GAIN = code(0x0D, 2, 2)
SET_FFC_PERIOD = code(0x0D, 4, 4)

GET_FFC_TEMP_DELTA = code(0x0E, 0, 4)
SET_FFC_TEMP_DELTA_LOW_GAIN = code(0x0E, 2, 2)
SET_FFC_TEMP_DELTA_HIGH_GAIN = code(0x0E, 2, 2)
SET_FFC_TEMP_DELTA = code(0x0E, 4, 4)

# Video Mode Commands
GET_VIDEO_MODE = code(0x0F, 0, 2)
SET_VIDEO_MODE = code(0x0F, 2, 2)

GET_VIDEO_SYMBOLOGY_DIGITAL = code(0x0F, 4, 2)
SET_VIDEO_SYMBOLOGY_DIGITAL = code(0x0F, 4, 4)
GET_VIDEO_SYMBOLOGY_ANALOG = code(0x0F, 4, 2)
SET_VIDEO_SYMBOLOGY_ANALOG = code(0x0F, 4, 4)

GET_VIDEO_PALETTE = code(0x10, 0, 2)
SET_VIDEO_PALETTE = code(0x10, 2, 2)

GET_VIDEO_ORIENTATION = code(0x11, 0, 2)
SET_VIDEO_ORIENTATION = code(0x11, 2 ,2)

GET_DIGITAL_OUTPUT_MODE = code(0x12, 0, 2)
SET_DIGITAL_OUTPUT_MODE = code(0x12, 2, 2)

SET_CONTRAST = code(0x14, 0, 2)
GET_CONTRAST = code(0x14, 2, 2)

SET_BRIGHTNESS = code(0x15, 0, 2)
GET_BRIGHTNESS = code(0x15, 2, 2)

SET_BRIGHTNESS_BIAS = code(0x18, 0, 2)
GET_BRIGHTNESS_BIAS = code(0x18, 2, 2)

SET_AGC_TAIL_SIZE = code(0x1B, 0, 2)
GET_AGC_TAIL_SIZE = code(0x1B, 2, 2)

SET_AGC_ACE_CORRECT = code(0x1C, 0, 2)
GET_AGC_ACE_CORRECT = code(0x1C, 2, 2)

# AGC

GET_AGC_ALGORITHM = code(0x13, 0, 2)
SET_AGC_ALGORITHM = code(0x13, 2, 2)

GET_AGC_THRESHOLD = code(0x13, 2, 2)
SET_AGC_THRESHOLD = code(0x13, 4, 0)

GET_AGC_OPTIMISATION_PERCENT = code(0x13, 2, 2)
SET_AGC_OPTIMISATION_PERCENT = code(0x13, 4, 0)

# Lens

SET_LENS_NUMBER = code(0x1E, 0, 2)
GET_LENS_NUMBER = code(0x1E, 2, 2)

GET_LENS_GAIN_SWITCH = code(0x1E, 2, 2)
SET_LENS_GAIN_SWITCH = code(0x1E, 4, 4)

GET_LENS_GAIN_MAPPING = code(0x1E, 2, 2)
SET_LENS_GAIN_MAPPING = code(0x1E, 4, 4)

# Spot Meter

SET_SPOT_METER_MODE = code(0x1F, 0, 2)
GET_SPOT_METER_MODE = code(0x1F, 2, 2)

# Onboard sensors

READ_SENSOR_TEMPERATURE = code(0x20, 2, 2)
READ_SENSOR_ACCELEROMETER = code(0x20, 2, 8)
READ_SENSOR_STATUS = code(0x20, 2, 2)

# Sync

GET_EXTERNAL_SYNC = code(0x21, 0, 2)
SET_EXTERNAL_SYNC = code(0x21, 2, 2)

# Isotherm

GET_ISOTHERM = code(0x22, 0, 2)
SET_ISOTHERM = code(0x22, 2, 2)

GET_ISOTHERM_THRESHOLD = code(0x23, 0, 6)
SET_ISOTHERM_THRESHOLD = code(0x23, 6, 6)

GET_ISOTHERM_THRESHOLD_FOUR = code(0x23, 4, 4)
SET_ISOTHERM_THRESHOLD_FOUR = code(0x23, 4, 4)

# Test Pattern

GET_TEST_PATTERN = code(0x25, 0, 2)
SET_TEST_PATTERN = code(0x25, 2, 2)

SET_VIDEO_COLOR_MODE = code(0x26, 0, 2)
GET_VIDEO_COLOR_MODE = code(0x26, 2, 2)

# Shutter

GET_SHUTTER_POSITION = code(0x79, 0, 2)
SET_SHUTTER_POSITION = code(0x79, 2, 2)

# Frame transfer

TRANSFER_FRAME = code(0x82, 4, 4)

GET_MEMORY_ADDRESS = code(0xD6, 4, 8)
GET_NV_MEMORY_SIZE = code(0xD5, 2, 8)

READ_MEMORY_256 = code(0xD2, 6, 256)

ERASE_BLOCK = code(0xD4, 2, 2)

MEMORY_STATUS = code(0xC4, 0, 2)

# Radiometry

GET_PLANCK_COEFFICIENTS = code(0xB9, 0, 16)
SET_PLANCK_COEFFICIENTS = code(0xB9, 18, 18)