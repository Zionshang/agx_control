import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "can" / "can_activate.sh"
MOCK_TOOL = r'''
import json
import os
from pathlib import Path
import subprocess
import sys

tool = Path(sys.argv[0]).name
args = sys.argv[1:]
devices = json.loads(os.environ["TEST_CAN_DEVICES"])
if tool == "sudo":
    sys.exit(subprocess.call(args))
if tool == "ethtool":
    bus = devices[args[-1]]
    if bus is None:
        sys.exit(1)
    print("bus-info: " + bus)
elif args == ["-br", "link", "show", "type", "can"]:
    if os.environ.get("TEST_CAN_SCAN_FAIL"):
        sys.exit(1)
    for name in devices:
        print(name + " DOWN")
elif args[:3] == ["-details", "link", "show"]:
    flags = "NOARP,UP,LOWER_UP" if os.environ.get("TEST_CAN_UP") else "NOARP"
    print("2: " + args[-1] + ": <" + flags + "> mtu 16")
    print("    can bitrate " + os.environ.get("TEST_CAN_BITRATE", "500000"))
elif args[:2] == ["link", "show"]:
    sys.exit(0 if args[-1] in devices else 1)
elif args[:2] == ["link", "set"]:
    with open(os.environ["TEST_CAN_LOG"], "a") as log:
        log.write(json.dumps(args) + "\n")
    if os.environ.get("TEST_CAN_FAIL_STEP") in args:
        sys.exit(1)
else:
    raise AssertionError((tool, args))
'''


class CanActivateTests(unittest.TestCase):
    def run_script(self, devices, selection="", args=(), **settings):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for tool in ("ip", "ethtool", "sudo"):
                executable = root / tool
                executable.write_text("#!" + sys.executable + "\n" + MOCK_TOOL)
                executable.chmod(0o755)
            log = root / "commands.jsonl"
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"])
            env.update(TEST_CAN_DEVICES=json.dumps(devices), TEST_CAN_LOG=str(log))
            env.update(settings)
            result = subprocess.run(
                ["bash", str(SCRIPT), *args], input=selection,
                text=True, capture_output=True, env=env, timeout=10,
            )
            commands = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, commands

    def assert_configured(self, commands, interface, target="can_agx", bitrate="1000000"):
        expected = [
            ["link", "set", interface, "down"],
            ["link", "set", interface, "type", "can", "bitrate", bitrate],
        ]
        if interface != target:
            expected.append(["link", "set", interface, "name", target])
        expected.append(["link", "set", target, "up"])
        self.assertEqual(commands, expected)

    def test_selects_only_chosen_device(self):
        result, commands = self.run_script({"can0": "1-1:1.0", "can1": "1-2:1.0"}, "2\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("can1 (USB: 1-2:1.0)", result.stderr)
        self.assert_configured(commands, "can1")

    def test_invalid_choices_retry_before_configuring(self):
        result, commands = self.run_script(
            {"can0": "1-1:1.0", "can1": "1-2:1.0"},
            "0\nabc\n3\n9999999999999999999999999999999\n2\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("编号无效", result.stderr)
        self.assert_configured(commands, "can1")

    def test_single_device_needs_no_selection(self):
        result, commands = self.run_script({"can0": "1-1:1.0"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_configured(commands, "can0")

    def test_no_devices_does_not_configure(self):
        result, commands = self.run_script({})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("未检测到", result.stderr)
        self.assertEqual(commands, [])

    def test_eof_cancels_selection_without_changes(self):
        result, commands = self.run_script({"can0": "1-1:1.0", "can1": "1-2:1.0"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("已取消", result.stderr)
        self.assertEqual(commands, [])

    def test_existing_target_conflict_does_not_change_either_device(self):
        result, commands = self.run_script({"can0": "1-1:1.0", "can_agx": "1-2:1.0"}, "1\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("can_agx 已存在", result.stderr)
        self.assertEqual(commands, [])

    def test_already_configured_device_is_unchanged(self):
        result, commands = self.run_script(
            {"can_agx": "1-1:1.0"}, TEST_CAN_UP="1", TEST_CAN_BITRATE="1000000",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(commands, [])

    def test_preserves_explicit_usb_selection(self):
        result, commands = self.run_script(
            {"can0": "1-1:1.0", "can1": "1-2:1.0"},
            args=("can_test", "250000", "1-2:1.0"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_configured(commands, "can1", "can_test", "250000")

    def test_missing_usb_address_does_not_configure(self):
        result, commands = self.run_script({"can0": "1-1:1.0"}, args=("can_agx", "1000000", "missing"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, [])

    def test_missing_bus_info_still_allows_interface_selection(self):
        result, commands = self.run_script({"can0": None, "can1": "1-2:1.0"}, "1\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("USB: 未知", result.stderr)
        self.assert_configured(commands, "can0")

    def test_configuration_error_stops_without_reporting_success(self):
        result, commands = self.run_script({"can0": "1-1:1.0"}, TEST_CAN_FAIL_STEP="type")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(commands), 2)
        self.assertNotIn("配置完成", result.stdout)

    def test_scan_failure_does_not_configure(self):
        result, commands = self.run_script({"can0": "1-1:1.0"}, TEST_CAN_SCAN_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, [])


if __name__ == "__main__":
    unittest.main()
