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
SYMMETRY_NONE = 'none'
SYMMETRY_PARTIAL = 'partial'
SYMMETRY_FULL = 'full'
POWER_MIN = "Minimum"
POWER_STD = "Standard"
POWER_HIGH = "High"
POWER_MAX = "Maximum"
PART_MIN = 'min'
PART_MAX = 'max'
ROOM_MIN = 'min'
ROOM_MAX = 'max'