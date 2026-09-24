from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import os
import socket

from .app_paths import bundled_client_exe


def default_client_exe() -> str:
    bundled = bundled_client_exe()
    return str(bundled) if bundled is not None else ""


def default_dhcp_script() -> str:
    return "ipconfig /renew" if os.name == "nt" else "dhclient -1"


def _is_bundled_reference(value: str) -> bool:
    parts = value.replace("\\", "/").casefold().split("/")
    return len(parts) >= 2 and parts[-2:] == ["ruijie supplicant", "8021x.exe"]


@dataclass(slots=True)
class MentohustConfig:
    enable: bool = True
    auto_connect: bool = False
    username: str = ""
    password: str = ""
    interface_description: str = ""
    interface_id: str = ""
    interface_mac: str = ""
    ipaddr: str = "0.0.0.0"
    gateway: str = "0.0.0.0"
    mask: str = "255.255.255.0"
    ping: str = "0.0.0.0"
    timeout: int = 8
    interval: int = 30
    wait: int = 15
    fail_number: int = 0
    multicast_address: int = 1
    dhcp_mode: int = 2
    dhcp_script: str = field(default_factory=default_dhcp_script)
    version: str = "5.00"
    dns: str = "0.0.0.0"
    client_exe: str = default_client_exe()

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        if self.dhcp_script.strip().casefold() in {"ipconfig /renew", "dhclient -1"}:
            data["dhcp_script"] = ""
        bundled = bundled_client_exe()
        if self.client_exe and (
            (bundled is not None and Path(self.client_exe) == bundled)
            or (_is_bundled_reference(self.client_exe) and not Path(self.client_exe).is_file())
        ):
            data["client_exe"] = ""
        return data

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MentohustConfig":
        data = cls().to_dict()
        data.update(payload)
        for key in ("enable", "auto_connect"):
            data[key] = bool(data[key])
        for key in ("timeout", "interval", "wait", "fail_number", "multicast_address", "dhcp_mode"):
            data[key] = int(data[key])
        return cls(**data)

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load_json(cls, path: str | Path) -> "MentohustConfig":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def client_exe_path(self) -> Path:
        configured = Path(self.client_exe).expanduser() if self.client_exe else None
        if configured is not None and configured.is_file():
            return configured
        bundled = bundled_client_exe()
        if bundled is not None:
            if configured is None:
                return bundled
            if _is_bundled_reference(self.client_exe):
                return bundled
        return configured if configured is not None else Path("8021x.exe")

    def resolved_ping_host(self) -> str:
        value = self.ping.strip()
        if not value or value == "0.0.0.0":
            return "0.0.0.0"
        try:
            socket.inet_aton(value)
            return value
        except OSError:
            return socket.gethostbyname(value)
