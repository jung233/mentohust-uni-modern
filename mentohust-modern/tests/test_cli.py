from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from mentohust_modern.cli import _run_client, main
from mentohust_modern.config import MentohustConfig
from mentohust_modern.interfaces import WindowsInterface, find_interface


class CliTests(unittest.TestCase):
    def test_help_works_with_legacy_console_encoding(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"
        process = subprocess.run(
            [sys.executable, "-m", "mentohust_modern.cli", "--help"],
            env=environment,
            check=False,
            capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("--init-config", process.stdout.decode("utf-8"))

    def test_import_cli_does_not_import_gui(self) -> None:
        process = subprocess.run(
            [sys.executable, "-c", "import sys, mentohust_modern.cli; assert 'mentohust_modern.gui' not in sys.modules"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_init_config_uses_shared_json_schema_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.json"
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--config", str(path), "--init-config"]), 0)
            config = MentohustConfig.load_json(path)
            self.assertEqual(config.username, "")
            self.assertIn("interface_mac", config.to_dict())
            self.assertEqual(main(["--config", str(path), "--init-config"]), 2)

    def test_init_config_can_store_portable_interface_mac(self) -> None:
        interface = WindowsInterface(2, "enp1s0", "wired", "enp1s0", "enp1s0", "00:11:22:33:44:55", "0.0.0.0", [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.json"
            with patch("mentohust_modern.cli.find_interface", return_value=interface), redirect_stdout(StringIO()):
                self.assertEqual(main(["--config", str(path), "--init-config", "--interface", "enp1s0"]), 0)
            saved = MentohustConfig.load_json(path)
        self.assertEqual(saved.interface_mac, "00:11:22:33:44:55")
        self.assertEqual(saved.dhcp_script, "")
        self.assertEqual(saved.client_exe, "")

    def test_check_applies_interface_override_without_root(self) -> None:
        interface = WindowsInterface(2, "enp1s0", "wired", "enp1s0", "enp1s0", "00:11:22:33:44:55", "0.0.0.0", [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.json"
            MentohustConfig(username="user", password="secret").save_json(path)
            with patch("mentohust_modern.cli.find_interface", return_value=interface) as find, patch(
                "mentohust_modern.cli.validation_errors", return_value=[]
            ), patch("mentohust_modern.cli.is_admin", side_effect=AssertionError("check should not need root")):
                with redirect_stdout(StringIO()) as output:
                    result = main(["--config", str(path), "--interface", "enp1s0", "--check"])
        self.assertEqual(result, 0)
        find.assert_called_once_with("enp1s0", "enp1s0", "enp1s0")
        self.assertIn("enp1s0", output.getvalue())

    def test_mac_finds_adapter_when_saved_platform_id_is_stale(self) -> None:
        interface = WindowsInterface(2, "enp1s0", "wired", "enp1s0", "enp1s0", "00:11:22:33:44:55", "0.0.0.0", [])
        with patch("mentohust_modern.interfaces.list_interfaces", return_value=[interface]):
            selected = find_interface("\\Device\\NPF_{OLD}", "Windows Ethernet", "00:11:22:33:44:55")
        self.assertIs(selected, interface)

    def test_run_stops_client_when_worker_finishes(self) -> None:
        client = Mock()
        client.thread.is_alive.side_effect = [True, False]
        with patch("mentohust_modern.cli.MentohustClient", return_value=client), patch(
            "mentohust_modern.cli.configure_logging"
        ), patch("mentohust_modern.cli.get_logger"):
            result = _run_client(MentohustConfig())
        self.assertEqual(result, 0)
        client.start.assert_called_once()
        client.stop.assert_called_once_with(wait=True)


if __name__ == "__main__":
    unittest.main()
