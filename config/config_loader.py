"""
Configuration loader module using YAML, environment variable overrides, and Pydantic for validation.
"""

import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class ADBConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5555
    connect_timeout_seconds: int = Field(default=15, ge=1)
    command_timeout_seconds: int = Field(default=30, ge=1)
    max_reconnect_attempts: int = Field(default=3, ge=1)

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"


class ReDroidConfig(BaseModel):
    container_name: str = "redroid"
    docker_socket: str = "unix:///var/run/docker.sock"
    docker_service_name: str = "docker"


class SnapchatConfig(BaseModel):
    package_name: str = "com.snapchat.android"
    activity_name: str = "com.snap.snapchat.LandingPageActivity"
    launch_timeout_seconds: int = Field(default=25, ge=5)
    element_timeout_seconds: int = Field(default=10, ge=1)
    recipients: List[str] = Field(default_factory=list)


class TimeWindowConfig(BaseModel):
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")

    @field_validator("start_time", "end_time")
    def validate_time_format(cls, v: str) -> str:
        hours, minutes = map(int, v.split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"Invalid time format: {v}. Must be between 00:00 and 23:59.")
        return v


class ScheduleConfig(BaseModel):
    time_windows: List[TimeWindowConfig] = Field(default_factory=list)
    max_retries: int = Field(default=3, ge=0)
    retry_delay_seconds: int = Field(default=300, ge=10)


class WatchdogConfig(BaseModel):
    check_interval_seconds: int = Field(default=60, ge=5)
    max_tier: int = Field(default=5, ge=1, le=5)
    enable_host_reboot: bool = False


class DatabaseConfig(BaseModel):
    path: str = "data/snapbot.db"


class LoggingConfig(BaseModel):
    log_level: str = "INFO"
    rotation: str = "10 MB"
    retention: str = "30 days"


class ScreenshotConfig(BaseModel):
    directory: str = "screenshots"
    retention_days: int = Field(default=30, ge=1)


class AppConfig(BaseModel):
    adb: ADBConfig = Field(default_factory=ADBConfig)
    redroid: ReDroidConfig = Field(default_factory=ReDroidConfig)
    snapchat: SnapchatConfig = Field(default_factory=SnapchatConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    watchdog: WatchdogConfig = Field(default_factory=WatchdogConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    screenshot: ScreenshotConfig = Field(default_factory=ScreenshotConfig)


class ConfigLoader:
    """Loads and validates application configuration from YAML files with environment overrides."""

    @staticmethod
    def load(config_path: str | Path = "config/config.yaml") -> AppConfig:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found at: {path.absolute()}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Environment variable overrides
        if "adb" not in data:
            data["adb"] = {}
        if os.getenv("ADB_HOST"):
            data["adb"]["host"] = os.getenv("ADB_HOST")
        if os.getenv("ADB_PORT"):
            data["adb"]["port"] = int(os.getenv("ADB_PORT"))

        if "redroid" not in data:
            data["redroid"] = {}
        if os.getenv("REDROID_CONTAINER_NAME"):
            data["redroid"]["container_name"] = os.getenv("REDROID_CONTAINER_NAME")

        return AppConfig(**data)
