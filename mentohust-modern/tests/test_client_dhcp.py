import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mentohust_modern.client import MentohustClient
from mentohust_modern.config import MentohustConfig
from mentohust_modern.interfaces import WindowsInterface


class ClientDhcpTests(unittest.TestCase):
    def test_default_renew_targets_selected_adapter(self) -> None:
        client = MentohustClient(MentohustConfig())
        client.interface = WindowsInterface(
            index=7,
            name="Ethernet 2",
            description="Wired adapter",
            guid="guid",
            network_name="pcap-name",
            mac="00:11:22:33:44:55",
            ipv4="0.0.0.0",
            nameservers=[],
        )
        client._load_runtime_network = Mock(return_value=SimpleNamespace(ipaddr="192.0.2.10"))  # type: ignore[method-assign]
        client._switch_state = Mock()  # type: ignore[method-assign]

        with patch("mentohust_modern.client.subprocess.run") as run, patch(
            "mentohust_modern.client.time.sleep"
        ), patch("mentohust_modern.client.build_fill_buffer", return_value=bytearray()):
            client._renew_ip()

        expected = ["ipconfig", "/renew", "Ethernet 2"] if os.name == "nt" else ["dhclient", "-1", "Ethernet 2"]
        self.assertEqual(run.call_args.args[0], expected)
        self.assertFalse(run.call_args.kwargs["shell"])


if __name__ == "__main__":
    unittest.main()
