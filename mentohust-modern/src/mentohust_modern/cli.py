from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys
import threading

from . import APP_VERSION
from .app_paths import default_profile_path
from .client import MentohustClient
from .config import MentohustConfig
from .elevation import is_admin
from .interfaces import WindowsInterface, find_interface, list_interfaces
from .logging_utils import configure_logging, get_logger
from .runtime_checks import validation_errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MentoHUST 802.1X 命令行客户端（无需图形界面）")
    parser.add_argument("--config", type=Path, default=default_profile_path(), help="与 GUI 通用的 JSON 配置路径")
    parser.add_argument("--interface", help="覆盖 JSON 中的网卡；可填写接口名、描述或 MAC 地址")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list-interfaces", action="store_true", help="列出可用网卡")
    action.add_argument("--init-config", action="store_true", help="创建 JSON 配置模板，不覆盖已有文件")
    action.add_argument("--check", action="store_true", help="检查 JSON、网卡和运行依赖，不启动认证")
    parser.add_argument("--version", action="version", version=f"MentoHUST Modern {APP_VERSION}")
    return parser


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _selected_interface(config: MentohustConfig, override: str | None) -> WindowsInterface | None:
    if override:
        return find_interface(override, override, override)
    return find_interface(config.interface_id, config.interface_description, config.interface_mac)


def _apply_interface(config: MentohustConfig, interface: WindowsInterface) -> None:
    config.interface_id = interface.network_name
    config.interface_description = interface.description
    config.interface_mac = interface.mac


def _run_client(config: MentohustConfig) -> int:
    configure_logging()
    logger = get_logger("cli")
    failed = False
    stopping = threading.Event()

    def log(message: str) -> None:
        nonlocal failed
        print(message, flush=True)
        logger.info(message)
        if "达到失败上限" in message:
            failed = True

    def state(value: str) -> None:
        nonlocal failed
        print(f"[状态] {value}", flush=True)
        logger.info("[状态] %s", value)
        if value == "错误":
            failed = True

    client = MentohustClient(config, log_callback=log, state_callback=state)
    previous_handlers: dict[signal.Signals, object] = {}

    def request_stop(_signum: int, _frame: object) -> None:
        stopping.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, request_stop)
    try:
        client.start()
        while client.thread is not None and client.thread.is_alive() and not stopping.is_set():
            client.thread.join(timeout=0.25)
    except KeyboardInterrupt:
        stopping.set()
    finally:
        client.stop(wait=True)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    args = _parser().parse_args(argv)

    if args.list_interfaces:
        try:
            interfaces = list_interfaces()
        except Exception as exc:
            print(f"无法列出网卡: {exc}", file=sys.stderr)
            return 2
        for interface in interfaces:
            print(f"{interface.network_name}\t{interface.mac}\t{interface.description}")
        return 0

    if args.init_config:
        if args.config.exists():
            print(f"配置已存在，不会覆盖: {args.config}", file=sys.stderr)
            return 2
        config = MentohustConfig()
        if args.interface:
            interface = _selected_interface(config, args.interface)
            if interface is None:
                print(f"找不到网卡: {args.interface}", file=sys.stderr)
                return 2
            _apply_interface(config, interface)
        try:
            args.config.parent.mkdir(parents=True, exist_ok=True)
            args.config.touch(mode=0o600, exist_ok=False)
            config.save_json(args.config)
        except OSError as exc:
            print(f"无法创建配置 {args.config}: {exc}", file=sys.stderr)
            return 2
        print(f"已创建配置: {args.config}")
        return 0

    try:
        config = MentohustConfig.load_json(args.config)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"无法读取配置 {args.config}: {exc}；可先用 --init-config 创建模板。", file=sys.stderr)
        return 2

    interface = _selected_interface(config, args.interface)
    if interface is None:
        print("找不到配置中的网卡；可用 --list-interfaces 查看，再用 --interface 指定。", file=sys.stderr)
        return 2
    _apply_interface(config, interface)

    errors = validation_errors(config)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2
    if args.check:
        print(f"配置有效；认证网卡: {interface.network_name} ({interface.mac})")
        return 0

    if not is_admin():
        print("认证需要管理员/root 权限；Linux 请使用 sudo 运行 CLI。", file=sys.stderr)
        return 2
    return _run_client(config)


if __name__ == "__main__":
    raise SystemExit(main())
