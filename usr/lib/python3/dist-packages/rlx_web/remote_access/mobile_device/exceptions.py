class RemoteAccessAuthException(Exception):
    def __init__(self, message=""):
        self.message = message
        super().__init__(message)

    def __str__(self):
        return self.message

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.message}"


class RemoteAccessTokenException(Exception):
    def __init__(self, message=""):
        self.message = message
        super().__init__(message)

    def __str__(self):
        return self.message

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.message}"


class InvalidMobileDeviceException(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class DuplicateMobileDeviceNameException(InvalidMobileDeviceException):
    def __init__(self):
        super().__init__("A device with that name is already registered")
