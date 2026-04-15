#!/usr/bin/env python3
import argparse
import time

import lcm
from msg import ArmCartesianCmd, ArmJointCmd, ArmServiceCmd, ArmState
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config


ARM_CARTESIAN_CMD_CHANNEL = "ARM_CARTESIAN_CMD"
ARM_JOINT_CMD_CHANNEL = "ARM_JOINT_CMD"
ARM_SERVICE_CMD_CHANNEL = "ARM_SERVICE_CMD"
ARM_STATE_CHANNEL = "ARM_STATE"
DEFAULT_LCM_URL = "udpm://239.255.76.67:7667?ttl=1"

home = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
tcp_offset = [0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0]
gripper_force = 1.0
gripper_max = 0.1
state_dt = 0.02


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_LCM_URL)
    return parser


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


cfg = create_agx_arm_config(
    robot=ArmModel.PIPER_L,
    firmeware_version=PiperFW.V183,
    channel="can0",
)
robot = AgxArmFactory.create_arm(cfg)
gripper = robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)


def ensure_enabled():
    start_t = time.monotonic()
    while not robot.enable() and time.monotonic() - start_t < 3.0:
        time.sleep(0.01)
    if time.monotonic() - start_t >= 3.0:
        raise RuntimeError("Failed to enable robot within 3 seconds.")


def move_gripper(pos):
    pos = clamp(pos, 0.0, gripper_max)
    gripper.move_gripper_m(value=pos, force=gripper_force)


def publish_state(lc):
    joint_msg = robot.get_joint_angles()
    tcp_msg = robot.get_tcp_pose()
    if joint_msg is None or tcp_msg is None:
        return

    state = ArmState()
    state.utime = int(time.time() * 1_000_000)
    state.joint_pos = list(joint_msg.msg)
    state.num_joints = len(state.joint_pos)
    state.tcp_pose = list(tcp_msg.msg)

    gripper_msg = gripper.get_gripper_status()
    if gripper_msg is not None:
        state.gripper_pos = gripper_msg.msg.value

    lc.publish(ARM_STATE_CHANNEL, state.encode())


def on_cartesian_cmd(channel, data):
    cmd = ArmCartesianCmd.decode(data)
    ensure_enabled()
    robot.move_p(robot.get_tcp2flange_pose(list(cmd.tcp_pose)))
    move_gripper(cmd.gripper_pos)


def on_joint_cmd(channel, data):
    cmd = ArmJointCmd.decode(data)
    if cmd.num_joints != 6:
        print(f"Ignore joint cmd: expected 6 joints, got {cmd.num_joints}")
        return
    ensure_enabled()
    robot.move_j(list(cmd.joint_pos))
    move_gripper(cmd.gripper_pos)


def on_service_cmd(channel, data):
    cmd = ArmServiceCmd.decode(data)
    if cmd.command == ArmServiceCmd.HOME:
        ensure_enabled()
        robot.move_j(home)
        print("Service: HOME")
    elif cmd.command == ArmServiceCmd.PASSIVE:
        robot.disable()
        print("Service: PASSIVE")
    else:
        print(f"Ignore service cmd: unknown command {cmd.command}")


try:
    args = build_parser().parse_args()
    robot.connect()
    ensure_enabled()
    robot.set_speed_percent(100)
    robot.set_tcp_offset(tcp_offset)

    lc = lcm.LCM(args.url)
    lc.subscribe(ARM_CARTESIAN_CMD_CHANNEL, on_cartesian_cmd)
    lc.subscribe(ARM_JOINT_CMD_CHANNEL, on_joint_cmd)
    lc.subscribe(ARM_SERVICE_CMD_CHANNEL, on_service_cmd)

    print("Arm LCM server started.")
    print(f"  url: {args.url}")
    print(f"  {ARM_CARTESIAN_CMD_CHANNEL}: ArmCartesianCmd")
    print(f"  {ARM_JOINT_CMD_CHANNEL}: ArmJointCmd")
    print(f"  {ARM_SERVICE_CMD_CHANNEL}: ArmServiceCmd")
    print(f"  {ARM_STATE_CHANNEL}: ArmState")

    next_state_t = time.monotonic()
    while True:
        lc.handle_timeout(5)
        if time.monotonic() >= next_state_t:
            publish_state(lc)
            next_state_t += state_dt
except KeyboardInterrupt:
    print("")
finally:
    robot.disconnect()
