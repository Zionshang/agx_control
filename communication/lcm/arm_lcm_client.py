#!/usr/bin/env python3
import argparse
import time

import lcm
from msg import ArmCartesianCmd, ArmJointCmd, ArmServiceCmd


ARM_CARTESIAN_CMD_CHANNEL = "ARM_CARTESIAN_CMD"
ARM_JOINT_CMD_CHANNEL = "ARM_JOINT_CMD"
ARM_SERVICE_CMD_CHANNEL = "ARM_SERVICE_CMD"
DEFAULT_LCM_URL = "udpm://239.255.76.67:7667?ttl=1"


def utime():
    return int(time.time() * 1_000_000)


def build_parser():
    parser = argparse.ArgumentParser(description="Send simple arm LCM commands.")
    parser.add_argument("--url", default=DEFAULT_LCM_URL)
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    cart = subparsers.add_parser("cartesian")
    cart.add_argument("tcp_pose", nargs=6, type=float, metavar=("X", "Y", "Z", "R", "P", "YAW"))
    cart.add_argument("--gripper", type=float, default=0.0)
    cart.add_argument("--preview-time", type=float, default=0.0)

    joint = subparsers.add_parser("joint")
    joint.add_argument("joint_pos", nargs=6, type=float, metavar=("J1", "J2", "J3", "J4", "J5", "J6"))
    joint.add_argument("--gripper", type=float, default=0.0)
    joint.add_argument("--preview-time", type=float, default=0.0)

    subparsers.add_parser("home")
    subparsers.add_parser("passive")
    return parser


def main():
    args = build_parser().parse_args()
    lc = lcm.LCM(args.url)

    if args.cmd == "cartesian":
        msg = ArmCartesianCmd()
        msg.tcp_pose = args.tcp_pose
        msg.gripper_pos = args.gripper
        msg.preview_time = args.preview_time
        lc.publish(ARM_CARTESIAN_CMD_CHANNEL, msg.encode())

    elif args.cmd == "joint":
        msg = ArmJointCmd()
        msg.num_joints = len(args.joint_pos)
        msg.joint_pos = args.joint_pos
        msg.gripper_pos = args.gripper
        msg.preview_time = args.preview_time
        lc.publish(ARM_JOINT_CMD_CHANNEL, msg.encode())

    elif args.cmd == "home":
        msg = ArmServiceCmd()
        msg.utime = utime()
        msg.command = ArmServiceCmd.HOME
        lc.publish(ARM_SERVICE_CMD_CHANNEL, msg.encode())

    elif args.cmd == "passive":
        msg = ArmServiceCmd()
        msg.utime = utime()
        msg.command = ArmServiceCmd.PASSIVE
        lc.publish(ARM_SERVICE_CMD_CHANNEL, msg.encode())


if __name__ == "__main__":
    main()
