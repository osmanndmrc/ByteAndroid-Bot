"""
Custom Exception Hierarchy for SnapBot Automation System.
"""

from typing import Optional


class SnapBotError(Exception):
    """Base exception for all SnapBot errors."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception

    def __str__(self) -> str:
        if self.original_exception:
            return f"{self.message} (Caused by: {type(self.original_exception).__name__}: {self.original_exception})"
        return self.message


# ADB Exceptions
class ADBError(SnapBotError):
    """Base exception for ADB communication failures."""
    pass


class ADBConnectionError(ADBError):
    """Raised when ADB fails to connect to the ReDroid instance."""
    pass


class ADBCommandError(ADBError):
    """Raised when an ADB shell command returns a non-zero exit code or fails."""
    pass


class ADBTimeoutError(ADBError):
    """Raised when an ADB command exceeds the specified execution timeout."""
    pass


# Device Exceptions
class DeviceError(SnapBotError):
    """Base exception for Android device level failures."""
    pass


class DeviceBootError(DeviceError):
    """Raised when Android has not finished booting."""
    pass


class DeviceOfflineError(DeviceError):
    """Raised when the Android device is offline or unreachable."""
    pass


class DeviceFreezeError(DeviceError):
    """Raised when the Android UI OS appears frozen or un-responsive."""
    pass


# UI Automation Exceptions
class UIAutomationError(SnapBotError):
    """Base exception for UI interaction failures."""
    pass


class ElementNotFoundError(UIAutomationError):
    """Raised when a UI element cannot be located after timeout."""
    pass


class UIWaitTimeoutError(UIAutomationError):
    """Raised when waiting for a UI state transition times out."""
    pass


# Snapchat Specific Exceptions
class SnapchatError(SnapBotError):
    """Base exception for Snapchat application automation failures."""
    pass


class SnapchatLaunchError(SnapchatError):
    """Raised when Snapchat fails to launch or reach main landing activity."""
    pass


class SnapchatCameraError(SnapchatError):
    """Raised when camera initialization or black photo capture fails."""
    pass


class SnapchatRecipientError(SnapchatError):
    """Raised when target recipients cannot be found or selected."""
    pass


class SnapchatSendError(SnapchatError):
    """Raised when pressing send fails or delivery is blocked."""
    pass


class SnapchatVerificationError(SnapchatError):
    """Raised when snap delivery verification fails after sending."""
    pass


# Watchdog & Recovery Exceptions
class WatchdogError(SnapBotError):
    """Base exception for Watchdog engine failures."""
    pass


class RecoveryEscalationMaxedError(WatchdogError):
    """Raised when all recovery tiers have been exhausted without restoring system health."""
    pass


# Database Exceptions
class DatabaseError(SnapBotError):
    """Base exception for SQLite database storage or query failures."""
    pass
