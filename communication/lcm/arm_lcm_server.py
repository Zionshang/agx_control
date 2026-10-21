#!/usr/bin/env python3
import argparse
import signal
import time

import lcm
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config

from .msg import ArmCartesianCmd, ArmJointCmd, ArmServiceCmd, ArmState


ARM_CARTESIAN_CMD_CHANNEL = "ARM_CARTESIAN_CMD"
ARM_JOINT_CMD_CHANNEL = "ARM_JOINT_CMD"
ARM_SERVICE_CMD_CHANNEL = "ARM_SERVICE_CMD"
ARM_STATE_CHANNEL = "ARM_STATE"
DEFAULT_LCM_URL = "udpm://239.255.76.67:7667?ttl=1"
SET_SPEED_BASE = 1000

HOME = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
TCP_OFFSET = [0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0]
GRIPPER_FORCE = 2.5
GRIPPER_MAX = 0.1
STATE_DT = 0.02
GRIPPER_DT = 0.05


def handle_sigterm(signum, frame):
    raise SystemExit(0)


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_LCM_URL)
    parser.add_argument("--enable-timeout", type=float, default=15.0)
    return parser


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def status_code(value):
    """Map the Piper uint8 UNKNOWN value to the signed LCM representation."""
    value = int(value)
    return -1 if value == 0xFF else value


class ArmLcmServer:
    def __init__(self, url=DEFAULT_LCM_URL, enable_timeout=15.0):
        self.url = url
        self.lc = None
        self.target_utime = 0
        self.gripper_ramp = None
        if not 0 < enable_timeout < float('inf'):
            raise ValueError('enable_timeout must be positive and finite')
        self.enable_timeout = enable_timeout

        cfg = create_agx_arm_config(
            robot=ArmModel.PIPER_L,
            firmeware_version=PiperFW.V183,
            channel="can_agx",
        )
        self.robot = AgxArmFactory.create_arm(cfg)
        self.gripper = self.robot.init_effector(self.robot.OPTIONS.EFFECTOR.AGX_GRIPPER)

    def run(self):
        connected = False
        previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
        try:
            signal.signal(signal.SIGTERM, handle_sigterm)
            self.robot.connect()
            connected = True
            self.ensure_enabled()
            self.robot.set_speed_percent(100)
            self.robot.set_tcp_offset(TCP_OFFSET)
            self.robot.move_j(HOME)
            print('[ARM][INIT] 使能确认通过，启动 HOME 指令已发送', flush=True)

            self.lc = lcm.LCM(self.url)
            self.lc.subscribe(ARM_CARTESIAN_CMD_CHANNEL, self.on_cartesian_cmd)
            self.lc.subscribe(ARM_JOINT_CMD_CHANNEL, self.on_joint_cmd)
            self.lc.subscribe(ARM_SERVICE_CMD_CHANNEL, self.on_service_cmd)

            self.print_startup_info()
            self.spin()
        except KeyboardInterrupt:
            print("")
        finally:
            try:
                if connected:
                    print('[ARM][EXIT] 发送 HOME：六关节归零', flush=True)
                    self.robot.move_j(HOME)
                    print('[ARM][EXIT] HOME 指令已发送，等待 2 秒后失能', flush=True)
                    time.sleep(2.0)
                    self.gripper.disable_gripper()
                    self.robot.disable()
                    time.sleep(0.1)
            finally:
                try:
                    self.robot.disconnect()
                finally:
                    signal.signal(signal.SIGTERM, previous_sigterm_handler)

    def spin(self):
        next_state_t = time.monotonic()
        while True:
            self.lc.handle_timeout(5)
            self.update_gripper_ramp()
            if time.monotonic() >= next_state_t:
                self.publish_state()
                next_state_t += STATE_DT

    def print_startup_info(self):
        print("Arm LCM server started.")
        print(f"  url: {self.url}")
        print(f"  {ARM_CARTESIAN_CMD_CHANNEL}: ArmCartesianCmd")
        print(f"  {ARM_JOINT_CMD_CHANNEL}: ArmJointCmd")
        print(f"  {ARM_SERVICE_CMD_CHANNEL}: ArmServiceCmd")
        print(f"  {ARM_STATE_CHANNEL}: ArmState")

    def enable_feedback(self):
        states = []
        for joint in range(1, 7):
            message = self.robot.get_driver_states(joint)
            if message is None:
                states.append(f'J{joint}=no_feedback')
                continue
            status = message.msg.foc_status
            flags = [name for name in ('voltage_too_low', 'motor_overheating',
                     'driver_overcurrent', 'driver_overheating', 'collision_status',
                     'driver_error_status', 'stall_status') if getattr(status, name, False)]
            value = 'enabled' if status.driver_enable_status else 'disabled'
            states.append(f'J{joint}={value}' + (f"({','.join(flags)})" if flags else ''))
        return ' '.join(states)

    def ensure_enabled(self):
        start_t = next_report = time.monotonic()
        while True:
            if self.robot.enable():
                print(f'[ARM][ENABLE] 六关节使能已确认，耗时 {time.monotonic()-start_t:.1f}s', flush=True)
                return
            now = time.monotonic()
            if now >= next_report:
                print(f'[ARM][ENABLE] 等待使能反馈 {now-start_t:.1f}/{self.enable_timeout:g}s：'
                      f'{self.enable_feedback()}', flush=True)
                next_report = now + 1.0
            if now-start_t >= self.enable_timeout:
                raise RuntimeError(f'Failed to confirm all six joints enabled within '
                                   f'{self.enable_timeout:g} seconds. {self.enable_feedback()}')
            time.sleep(0.1)

    def move_gripper(self, pos, duration=0.0):
        target = clamp(pos, 0.0, GRIPPER_MAX)
        status = self.gripper.get_gripper_status()
        start = clamp(
            status.msg.value if status is not None else GRIPPER_MAX,
            0.0, GRIPPER_MAX,
        )
        duration = max(0.0, float(duration))
        if duration == 0.0 or target >= start:
            self.gripper_ramp = None
            self.gripper.move_gripper_m(value=target, force=GRIPPER_FORCE)
            return
        now = time.monotonic()
        self.gripper_ramp = (start, target, now, duration, now)

    def update_gripper_ramp(self):
        if self.gripper_ramp is None:
            return
        start, target, started, duration, next_t = self.gripper_ramp
        now = time.monotonic()
        if now < next_t:
            return
        ratio = min(1.0, (now - started) / duration)
        self.gripper.move_gripper_m(
            value=start + (target - start) * ratio,
            force=GRIPPER_FORCE,
        )
        self.gripper_ramp = (start, target, started, duration, now + GRIPPER_DT)
        if ratio >= 1.0:
            self.gripper_ramp = None

    def publish_state(self):
        joint_msg = self.robot.get_joint_angles()
        tcp_msg = self.robot.get_tcp_pose()
        if joint_msg is None or tcp_msg is None:
            return

        state = ArmState()
        state.utime = int(time.time() * 1_000_000)
        state.joint_pos = list(joint_msg.msg)
        state.num_joints = len(state.joint_pos)
        state.tcp_pose = list(tcp_msg.msg)

        gripper_msg = self.gripper.get_gripper_status()
        if gripper_msg is not None:
            state.gripper_pos = gripper_msg.msg.value

        state.arm_status = -1
        state.target_utime = self.target_utime
        arm_status_msg = self.robot.get_arm_status()
        if arm_status_msg is not None:
            state.arm_status = status_code(arm_status_msg.msg.arm_status)

        self.lc.publish(ARM_STATE_CHANNEL, state.encode())

    def register_target(self, command_utime):
        self.target_utime = command_utime or int(time.time() * 1_000_000)

    def on_cartesian_cmd(self, channel, data):
        cmd = ArmCartesianCmd.decode(data)
        self.robot.move_p(self.robot.get_tcp2flange_pose(list(cmd.tcp_pose)))
        self.register_target(cmd.utime)
        self.move_gripper(cmd.gripper_pos, cmd.gripper_duration)

    def on_joint_cmd(self, channel, data):
        cmd = ArmJointCmd.decode(data)
        if cmd.num_joints != 6:
            print(f"Ignore joint cmd: expected 6 joints, got {cmd.num_joints}")
            return
        self.robot.move_j(list(cmd.joint_pos))
        self.register_target(cmd.utime)
        self.move_gripper(cmd.gripper_pos)

    def on_service_cmd(self, channel, data):
        cmd = ArmServiceCmd.decode(data)
        if SET_SPEED_BASE < cmd.command <= SET_SPEED_BASE + 100:
            percent = cmd.command - SET_SPEED_BASE
            self.robot.set_speed_percent(percent)
            print(f"Service: SPEED {percent}%")
        elif cmd.command == ArmServiceCmd.HOME:
            self.robot.move_j(HOME)
            self.register_target(cmd.utime)
            print("Service: HOME")
        elif cmd.command == ArmServiceCmd.PASSIVE:
            self.gripper_ramp = None
            self.gripper.disable_gripper()
            self.robot.disable()
            self.target_utime = 0
            print("Service: PASSIVE")
        else:
            print(f"Ignore service cmd: unknown command {cmd.command}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    ArmLcmServer(url=args.url, enable_timeout=args.enable_timeout).run()


if __name__ == "__main__":
    main()
