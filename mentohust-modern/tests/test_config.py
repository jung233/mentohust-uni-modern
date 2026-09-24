from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mentohust_modern.config import MentohustConfig


class ConfigTests(unittest.TestCase):
    def test_auto_connect_roundtrip(self) -> None:
        config = MentohustConfig(auto_connect=True, username="user")
        loaded = MentohustConfig.from_dict(config.to_dict())
        self.assertTrue(loaded.auto_connect)
        self.assertEqual(loaded.username, "user")

    def test_save_and_load_json(self) -> None:
        config = MentohustConfig(auto_connect=True, username="user", password="secret", interface_mac="00:11:22:33:44:55")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            config.save_json(path)
            loaded = MentohustConfig.load_json(path)
        self.assertTrue(loaded.auto_connect)
        self.assertEqual(loaded.password, "secret")
        self.assertEqual(loaded.interface_mac, "00:11:22:33:44:55")

    def test_bundled_client_reference_stays_portable_in_json(self) -> None:
        windows_path = r"C:\app\Ruijie Supplicant\8021x.exe"
        linux_path = Path("/opt/app/Ruijie Supplicant/8021x.exe")
        config = MentohustConfig(client_exe=windows_path)
        with patch("mentohust_modern.config.bundled_client_exe", return_value=linux_path):
            self.assertEqual(config.to_dict()["client_exe"], "")
            self.assertEqual(config.to_dict()["dhcp_script"], "")
            self.assertEqual(config.client_exe_path(), linux_path)


if __name__ == "__main__":
    unittest.main()
