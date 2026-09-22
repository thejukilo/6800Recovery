from typing import Any
from rlx_osal.outcome import Outcome


class OSALException(BaseException):
    """Base class for osal errors"""


class OSALCallError(OSALException):
    """OSAL call error"""

    def __init__(self, ret: Any):
        self.ret = ret

    def __str__(self) -> str:
        return f"OSALCallError: {self.ret.errorMessage}"

    def __repr__(self) -> str:
        return str(self)


class UnknownOSALMethodError(OSALException, AttributeError):
    pass

class OSALMethodInvalidParameterError(OSALException):
    pass

class OSALError(OSALException):
    """Error from OSAL"""

    def __init__(self, ret = Outcome.ERROR.value, message: str = None):
        self.ret = ret
        self.message = f"OSALError: {self.ret}\n{message}"
        super().__init__(self.message)

class OSALParameterError(OSALException):
    """Parameter Error from OSAL"""

    def __init__(self, ret = Outcome.PARAMETER_ERROR.value, message: str = None):
        self.ret = ret
        self.message = f"OSALParameterError: {self.ret}\n{message}"
        super().__init__(self.message)


class OSALNoneError(OSALException):
    """None Error from OSAL"""

    def __init__(self, ret = Outcome.NONE.value, message: str = None):
        self.ret = ret
        self.message = message if message else f"OSALNoneError: {self.ret}\n{message}"
        super().__init__(self.message)


class OSALUnknownRequestError(OSALException):
    """Unknown Request Error from OSAL"""

    def __init__(self, ret = Outcome.UNKNOWN_REQUEST.value, message: str = None):
        self.ret = ret
        self.message = f"OSALUnknownRequestError: {self.ret}\n{message}"
        super().__init__(self.message)


class OSALBusyError(OSALException):
    """Busy Error from OSAL"""

    def __init__(self, ret = Outcome.BUSY.value, message: str = None):
        self.ret = ret
        self.message = f"OSALBusyError: {self.ret}\n{message}"
        super().__init__(self.message)


class OSALNoBackgroundError(OSALException):
    """No Background Error from OSAL"""

    def __init__(self, ret = Outcome.NO_BACKGROUND.value, message: str = None):
        self.ret = ret
        self.message = f"OSALNoBackGroundError: {self.ret}\n{message}"
        super().__init__(self.message)


class OSALProcessingError(OSALException):
    """Processing Error from OSAL"""

    def __init__(self, ret = Outcome.PROCESSING.value, message: str = None):
        self.ret = ret
        self.message = f"OSALProcessingError: {self.ret}\n{message}"
        super().__init__(self.message)
