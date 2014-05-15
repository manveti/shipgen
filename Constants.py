TYPE_SM = "Small Ship"
TYPE_LG = "Large Ship"
TYPE_ST = "Station"
TYPE_ABBRS = {TYPE_SM: "sm", TYPE_LG: "lg", TYPE_ST: "st"}
TYPES = set(TYPE_ABBRS.keys())

TYPE_SIZES = {TYPE_SM: TYPE_SM, TYPE_LG: TYPE_LG, TYPE_ST: TYPE_LG}
SIZES = set(TYPE_SIZES.values())