TYPE_SM = "Small Ship"
TYPE_LG = "Large Ship"
TYPE_ST = "Station"
TYPE_ABBRS = {TYPE_SM: "sm", TYPE_LG: "lg", TYPE_ST: "st"}
TYPES = set(TYPE_ABBRS.keys())

TYPE_SIZES = {TYPE_SM: TYPE_SM, TYPE_LG: TYPE_LG, TYPE_ST: TYPE_LG}
SIZES = set(TYPE_SIZES.values())

ENCLOSURE_NONE = 'none'
ENCLOSURE_PLATFORM = 'platform'
ENCLOSURE_FULL = 'full'
ENCLOSURE_SEALED = 'sealed'
ENCLOSURE_SCALE = [ENCLOSURE_NONE, ENCLOSURE_PLATFORM, ENCLOSURE_FULL, ENCLOSURE_SEALED]
SYMMETRY_NONE = 'none'
SYMMETRY_PARTIAL = 'partial'
SYMMETRY_FULL = 'full'
POWER_MIN = "minimum"
POWER_STD = "standard"
POWER_HIGH = "high"
POWER_MAX = "maximum"
PART_MIN = 'min'
PART_MAX = 'max'
ROOM_MIN = 'min'
ROOM_MAX = 'max'
FREE_MIN = 'min'
FREE_MAX = 'max'

UP = (0, 0, 1)
DOWN = (0, 0, -1)
SBD = (1, 0, 0)
PORT = (-1, 0, 0)
FWD = (0, -1, 0)
AFT = (0, 1, 0)
ALL_DIRECTIONS = [UP, DOWN, SBD, PORT, FWD, AFT]
SE_DIRECTIONS = {UP: "Up", DOWN: "Down", SBD: "Right", PORT: "Left", FWD: "Forward", AFT: "Backward"}
