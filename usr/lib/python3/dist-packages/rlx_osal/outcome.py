from enum import Enum, auto


class Outcome(Enum):
    NONE = 0
    OK = 1
    ERROR = 2
    UNKNOWN_REQUEST = 3
    PARAMETER_ERROR = 4
    BUSY = 5
    NO_BACKGROUND = 6
    PROCESSING = 7

