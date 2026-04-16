#!/usr/bin/env python3
import argparse
import time

import lcm
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config

from .msg import ArmCartesianCmd, ArmJointCmd, ArmServiceCmd, ArmState


ARM_CARTESIAN_CMD_CHANNEL = "ARM_CARTESIAN_CMD"
ARM_JOINT_CMD_CHANNEL = "ARM_JOINT_CMD"
ARM_SERVICE_CMD_CHANNEL = "ARM_SERVICE_CMD"
ARM_STATE_CHANNEL = "ARM_STATE"
DEFAULT_LCM_URL = "udpm://239.255.76.67:7667?ttl=1"

HOME = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
TCP_OFFSET = [0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0]
GRIPPER_FORCE = 1.0
GRIPPER_MAX = 0.1
STATE_DT = 0.02


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_LCM_URL)
    return parser


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


class ArmLcmServer:
    def __init__(self, url=DEFAULT_LCM_URL):
        self.url = url
        self.lc = None

        cfg = create_agx_arm_config(
            robot=ArmModel.PIPER_L,
            firmeware_version=PiperFW.V183,
            channel="can0",
        )
        self.robot = AgxArmFactory.create_arm(cfg)
        self.gripper = self.robot.init_effector(self.robot.OPTIONS.EFFECTOR.AGX_GRIPPER)

    def run(self):
        try:
            self.robot.connect()
            self.ensure_enabled()
            self.robot.set_speed_percent(100)
            self.robot.set_tcp_offset(TCP_OFFSET)

            self.lc = lcm.LCM(self.url)
            self.lc.subscribe(ARM_CARTESIAN_CMD_CHANNEL, self.on_cartesian_cmd)
            self.lc.subscribe(ARM_JOINT_CMD_CHANNEL, self.on_joint_cmd)
            self.lc.subscribe(ARM_SERVICE_CMD_CHANNEL, self.on_service_cmd)

            self.print_startup_info()
            self.spin()
        except KeyboardInterrupt:
            print("")
        finally:
            self.robot.disconnect()

    def spin(self):
        next_state_t = time.monotonic()
        while True:
            self.lc.handle_timeout(5)
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

    def ensure_enabled(self):
        start_t = time.monotonic()
        while not self.robot.enable() and time.monotonic() - start_t < 3.0:
            time.sleep(0.01)
        if time.monotonic() - start_t >= 3.0:
            raise RuntimeError("Failed to enable robot within 3 seconds.")

    def move_gripper(self, pos):
        pos = clamp(pos, 0.0, GRIPPER_MAX)
        self.gripper.move_gripper_m(value=pos, force=GRIPPER_FORCE)

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

        self.lc.publish(ARM_STATE_CHANNEL, state.encode())

    def on_cartesian_cmd(self, channel, data):
        cmd = ArmCartesianCmd.decode(data)
        self.ensure_enabled()
        self.robot.move_p(self.robot.get_tcp2flange_pose(list(cmd.tcp_pose)))
        self.move_gripper(cmd.gripper_pos)

    def on_joint_cmd(self, channel, data):
        cmd = ArmJointCmd.decode(data)
        if cmd.num_joints != 6:
            print(f"Ignore joint cmd: expected 6 joints, got {cmd.num_joints}")
            return
        self.ensure_enabled()
        self.robot.move_j(list(cmd.joint_pos))
        self.move_gripper(cmd.gripper_pos)

    def on_service_cmd(self, channel, data):
        cmd = ArmServiceCmd.decode(data)
        if cmd.command == ArmServiceCmd.HOME:
            self.ensure_enabled()
            self.robot.move_j(HOME)
            print("Service: HOME")
        elif cmd.command == ArmServiceCmd.PASSIVE:
            self.robot.disable()
            print("Service: PASSIVE")
        else:
            print(f"Ignore service cmd: unknown command {cmd.command}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    ArmLcmServer(url=args.url).run()


if __name__ == "__main__":
    main()
