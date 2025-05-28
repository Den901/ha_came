"""Exceptions for ETI/Domo."""
from typing import Optional


class ETIDomoError(Exception):
    """Generic ETI/Domo exception."""

    def __init__(self, status: str, errno: Optional[int] = None):
        """Initialize."""
        super().__init__(status)
        self.status = status
        self.errno = errno


class ETIDomoConnectionError(ETIDomoError):
    """ETI/Domo connection exception."""


class ETIDomoConnectionTimeoutError(ETIDomoConnectionError, TimeoutError):
    """ETI/Domo connection Timeout exception."""


class ETIDomoUnmanagedDeviceError(ETIDomoError):
    """ETI/Domo exception for unmanaged device."""

    def __init__(
        self, status: str = "This device is unmanageable", errno: Optional[int] = None
    ):
        """Initialize."""
        super().__init__(status, errno)
