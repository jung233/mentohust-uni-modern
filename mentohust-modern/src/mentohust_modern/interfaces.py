from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess

from scapy.all import conf, get_if_addr, get_if_hwaddr
from scapy.error import Scapy_Exception

if os.name == "nt":
    from scapy.arch.windows import get_windows_if_list

from .windows import hidden_subprocess_kwargs


@dataclass(slots=True)
class WindowsInterface:
    index: int
    name: str
    description: str
    guid: str
    network_name: str
    mac: str
    ipv4: str
    nameservers: list[str]


@dataclass(slots=True)
class InterfaceNetworkDetails:
    ipv4: str
    mask: str
    gateway: str
    dns: str


def _first_ipv4(values: list[str]) -> str:
    for item in values:
        try:
            parsed = ipaddress.ip_address(item)
        except ValueError:
            continue
        if parsed.version == 4:
            return str(parsed)
    return "0.0.0.0"


def _prefix_to_mask(prefix_length: int) -> str:
    network = ipaddress.IPv4Network(f"0.0.0.0/{prefix_length}")
    return str(network.netmask)


def list_interfaces() -> list[WindowsInterface]:
    if os.name != "nt":
        return _list_linux_interfaces()

    conf.use_pcap = True
    raw_interfaces = get_windows_if_list()
    pcap_map = {
        getattr(iface, "guid", ""): getattr(iface, "network_name", str(iface))
        for iface in conf.ifaces.values()
    }
    results: list[WindowsInterface] = []
    for item in raw_interfaces:
        description = item.get("description", "")
        if not description or "Npcap Packet Driver" in description or "WFP " in description:
            continue
        mac = item.get("mac", "")
        network_name = pcap_map.get(item.get("guid", ""), "")
        if not mac or not network_name:
            continue
        results.append(
            WindowsInterface(
                index=int(item["index"]),
                name=item.get("name", ""),
                description=description,
                guid=item.get("guid", ""),
                network_name=network_name,
                mac=mac,
                ipv4=_first_ipv4(item.get("ips", [])),
                nameservers=[value for value in item.get("nameservers", []) if ":" not in value],
            )
        )
    return results


def _list_linux_interfaces() -> list[WindowsInterface]:
    results: list[WindowsInterface] = []
    for index, name in socket.if_nameindex():
        if name == "lo":
            continue
        try:
            mac = get_if_hwaddr(name)
            ipv4 = get_if_addr(name)
        except (OSError, ValueError, Scapy_Exception):
            continue
        if not mac or mac == "00:00:00:00:00:00":
            continue
        results.append(
            WindowsInterface(
                index=index,
                name=name,
                description=name,
                guid=name,
                network_name=name,
                mac=mac,
                ipv4=ipv4 or "0.0.0.0",
                nameservers=[],
            )
        )
    return results


def find_interface(interface_id: str = "", description: str = "", mac: str = "") -> WindowsInterface | None:
    normalized_id = interface_id.strip().lower()
    normalized_description = description.strip().lower()
    normalized_mac = mac.strip().lower().replace("-", ":")
    interfaces = list_interfaces()
    for interface in interfaces:
        if normalized_id and interface.network_name.lower() == normalized_id:
            return interface
        if normalized_id and interface.guid.lower() == normalized_id:
            return interface
    for interface in interfaces:
        if normalized_mac and interface.mac.lower().replace("-", ":") == normalized_mac:
            return interface
    for interface in interfaces:
        if normalized_description and interface.description.lower() == normalized_description:
            return interface
        if normalized_description and interface.name.lower() == normalized_description:
            return interface
    return None


def read_network_details(interface: WindowsInterface) -> InterfaceNetworkDetails:
    if os.name != "nt":
        return _read_linux_network_details(interface)

    script = rf"""
$cfg = Get-NetIPConfiguration -InterfaceIndex {interface.index}
$ipv4 = $null
$prefix = $null
if ($cfg.IPv4Address) {{
  $entry = $cfg.IPv4Address | Select-Object -First 1
  $ipv4 = $entry.IPAddress
  $prefix = $entry.PrefixLength
}}
$gateway = $null
if ($cfg.IPv4DefaultGateway) {{
  $gateway = ($cfg.IPv4DefaultGateway | Select-Object -First 1).NextHop
}}
$dns = @()
if ($cfg.DnsServer) {{
  $dns = $cfg.DnsServer.ServerAddresses
}}
[pscustomobject]@{{
  IPv4Address = $ipv4
  PrefixLength = $prefix
  IPv4DefaultGateway = $gateway
  DnsServers = $dns
}} | ConvertTo-Json -Compress -Depth 3
"""
    output = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
        **hidden_subprocess_kwargs(),
    )
    payload = {}
    if output.returncode == 0 and output.stdout.strip():
        payload = json.loads(output.stdout)

    ipv4 = payload.get("IPv4Address") or interface.ipv4 or "0.0.0.0"
    prefix = payload.get("PrefixLength")
    mask = _prefix_to_mask(int(prefix)) if prefix is not None else "255.255.255.0"
    gateway = payload.get("IPv4DefaultGateway") or "0.0.0.0"
    dns_servers = payload.get("DnsServers") or interface.nameservers
    dns = dns_servers[0] if dns_servers else "0.0.0.0"
    return InterfaceNetworkDetails(ipv4=ipv4, mask=mask, gateway=gateway, dns=dns)


def _linux_ip_json(*args: str) -> list[dict[str, object]]:
    try:
        output = subprocess.run(["ip", "-j", "-4", *args], check=False, capture_output=True, text=True)
    except OSError:
        return []
    if output.returncode != 0:
        return []
    try:
        payload = json.loads(output.stdout)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _read_linux_network_details(interface: WindowsInterface) -> InterfaceNetworkDetails:
    ipv4 = interface.ipv4 or "0.0.0.0"
    mask = "255.255.255.0"
    for adapter in _linux_ip_json("addr", "show", "dev", interface.name):
        for entry in adapter.get("addr_info", []):
            if entry.get("family") == "inet":
                ipv4 = entry.get("local") or ipv4
                mask = _prefix_to_mask(int(entry["prefixlen"]))
                break

    gateway = "0.0.0.0"
    for route in _linux_ip_json("route", "show", "default", "dev", interface.name):
        gateway = route.get("gateway") or gateway
        if gateway != "0.0.0.0":
            break

    dns = "0.0.0.0"
    try:
        lines = Path("/etc/resolv.conf").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "nameserver":
            dns = _first_ipv4([parts[1]])
            if dns != "0.0.0.0":
                break
    return InterfaceNetworkDetails(ipv4=ipv4, mask=mask, gateway=gateway, dns=dns)
