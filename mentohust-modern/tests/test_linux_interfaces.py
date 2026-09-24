import sys
import unittest
from unittest.mock import patch

from mentohust_modern.interfaces import WindowsInterface, list_interfaces, read_network_details


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux only")
class LinuxInterfaceTests(unittest.TestCase):
    def test_list_interfaces_uses_linux_names_for_packet_binding(self) -> None:
        with patch("mentohust_modern.interfaces.socket.if_nameindex", return_value=[(1, "lo"), (2, "enp1s0")]), patch(
            "mentohust_modern.interfaces.get_if_hwaddr", return_value="00:11:22:33:44:55"
        ), patch("mentohust_modern.interfaces.get_if_addr", return_value="192.0.2.8"):
            interfaces = list_interfaces()

        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].name, "enp1s0")
        self.assertEqual(interfaces[0].network_name, "enp1s0")

    def test_network_details_use_selected_linux_interface(self) -> None:
        interface = WindowsInterface(2, "enp1s0", "enp1s0", "enp1s0", "enp1s0", "00:11:22:33:44:55", "0.0.0.0", [])
        addr = [{"addr_info": [{"family": "inet", "local": "192.0.2.8", "prefixlen": 24}]}]
        route = [{"gateway": "192.0.2.1"}]
        with patch("mentohust_modern.interfaces._linux_ip_json", side_effect=[addr, route]) as ip, patch(
            "mentohust_modern.interfaces.Path.read_text", return_value="nameserver 192.0.2.53\n"
        ):
            details = read_network_details(interface)

        self.assertEqual(ip.call_args_list[0].args, ("addr", "show", "dev", "enp1s0"))
        self.assertEqual(ip.call_args_list[1].args, ("route", "show", "default", "dev", "enp1s0"))
        self.assertEqual((details.ipv4, details.mask, details.gateway, details.dns), ("192.0.2.8", "255.255.255.0", "192.0.2.1", "192.0.2.53"))


if __name__ == "__main__":
    unittest.main()
