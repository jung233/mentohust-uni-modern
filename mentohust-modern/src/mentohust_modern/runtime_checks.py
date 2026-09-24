from __future__ import annotations

import ctypes.util
import os
from pathlib import Path
import shutil

from .config import MentohustConfig, default_dhcp_script


def npcap_installed() -> bool:
    candidates = [
        Path(r"C:\Windows\System32\Npcap\wpcap.dll"),
        Path(r"C:\Windows\SysWOW64\Npcap\wpcap.dll"),
        Path(r"C:\Program Files\Npcap\wpcap.dll"),
    ]
    return any(path.exists() for path in candidates)


def validation_errors(config: MentohustConfig) -> list[str]:
    errors: list[str] = []
    if os.name == "nt":
        if not npcap_installed():
            errors.append("未检测到 Npcap，请先安装 Npcap 再尝试连接。")
    else:
        if ctypes.util.find_library("pcap") is None:
            errors.append("未检测到 libpcap，请先安装 libpcap。")
        if shutil.which("ip") is None:
            errors.append("未检测到 iproute2 的 ip 命令。")
        if config.dhcp_mode and config.dhcp_script.strip().casefold() in {"", default_dhcp_script(), "ipconfig /renew", "dhclient -1"}:
            if shutil.which("dhclient") is None:
                errors.append("默认 DHCP 模式需要 dhclient；请安装 isc-dhcp-client 或填写自定义 DHCP 命令。")
    if not config.client_exe_path().exists():
        errors.append(f"找不到官方客户端文件: {config.client_exe_path()}")
    if not config.username.strip():
        errors.append("用户名不能为空。")
    if not config.password:
        errors.append("密码不能为空。")
    return errors
