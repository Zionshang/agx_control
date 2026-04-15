#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import List, Optional, Sequence, TypedDict

import lcm
from msg import ArmCartesianCmd, ArmJointCmd, ArmServiceCmd, ArmState


ARM_CARTESIAN_CMD_CHANNEL = "ARM_CARTESIAN_CMD"
ARM_JOINT_CMD_CHANNEL = "ARM_JOINT_CMD"
ARM_SERVICE_CMD_CHANNEL = "ARM_SERVICE_CMD"
ARM_STATE_CHANNEL = "ARM_STATE"
DEFAULT_LCM_URL = "udpm://239.255.76.67:7667?ttl=1"

__all__ = ["ArmLcmClient", "ArmStateDict"]


class ArmStateDict(TypedDict):
    utime: int
    num_joints: int
    joint_pos: List[float]
    tcp_pose: List[float]
    gripper_pos: float


def utime() -> int:
    return int(time.time() * 1_000_000)


class ArmLcmClient:
    def __init__(self, url: str = DEFAULT_LCM_URL) -> None:
        self.lc = lcm.LCM(url)

    def set_cartesian_cmd(
        self,
        tcp_pose: Sequence[float],
        gripper: float = 0.0,
        preview_time: float = 0.0,
    ) -> None:
        msg = ArmCartesianCmd()
        msg.tcp_pose = list(tcp_pose)
        msg.gripper_pos = gripper
        msg.preview_time = preview_time
        self.lc.publish(ARM_CARTESIAN_CMD_CHANNEL, msg.encode())

    def set_joint_cmd(
        self,
        joint_pos: Sequence[float],
        gripper: float = 0.0,
        preview_time: float = 0.0,
    ) -> None:
        msg = ArmJointCmd()
        msg.joint_pos = list(joint_pos)
        msg.num_joints = len(msg.joint_pos)
        msg.gripper_pos = gripper
        msg.preview_time = preview_time
        self.lc.publish(ARM_JOINT_CMD_CHANNEL, msg.encode())

    def set_to_home(self) -> None:
        msg = ArmServiceCmd()
        msg.utime = utime()
        msg.command = ArmServiceCmd.HOME
        self.lc.publish(ARM_SERVICE_CMD_CHANNEL, msg.encode())

    def set_to_passive(self) -> None:
        msg = ArmServiceCmd()
        msg.utime = utime()
        msg.command = ArmServiceCmd.PASSIVE
        self.lc.publish(ARM_SERVICE_CMD_CHANNEL, msg.encode())

    @staticmethod
    def decode_state(data: bytes) -> ArmStateDict:
        state = ArmState.decode(data)
        return {
            "utime": state.utime,
            "num_joints": state.num_joints,
            "joint_pos": list(state.joint_pos),
            "tcp_pose": list(state.tcp_pose),
            "gripper_pos": state.gripper_pos,
        }

    def get_state(self, timeout: float = 1.0) -> Optional[ArmStateDict]:
        result: dict[str, ArmStateDict] = {}

        def on_state(channel: str, data: bytes) -> None:
            result["state"] = self.decode_state(data)

        subscription = self.lc.subscribe(ARM_STATE_CHANNEL, on_state)
        deadline = time.monotonic() + timeout
        try:
            while "state" not in result and time.monotonic() < deadline:
                remain_ms = max(1, int((deadline - time.monotonic()) * 1000))
                self.lc.handle_timeout(min(remain_ms, 100))
        finally:
            self.lc.unsubscribe(subscription)
        return result.get("state")


if __name__ == "__main__":
    import argparse

    def build_parser():
        parser = argparse.ArgumentParser(description="Send simple arm LCM commands.")
        parser.add_argument("--url", default=DEFAULT_LCM_URL)
        subparsers = parser.add_subparsers(dest="cmd", required=True)

        cart = subparsers.add_parser("cartesian")
        cart.add_argument(
            "tcp_pose", nargs=6, type=float, metavar=("X", "Y", "Z", "R", "P", "YAW")
        )
        cart.add_argument("--gripper", type=float, default=0.0)
        cart.add_argument("--preview-time", type=float, default=0.0)

        joint = subparsers.add_parser("joint")
        joint.add_argument(
            "joint_pos", nargs=6, type=float, metavar=("J1", "J2", "J3", "J4", "J5", "J6")
        )
        joint.add_argument("--gripper", type=float, default=0.0)
        joint.add_argument("--preview-time", type=float, default=0.0)

        subparsers.add_parser("home")
        subparsers.add_parser("passive")
        subparsers.add_parser("state")
        return parser

    def print_state(state: ArmStateDict) -> None:
        print(
            f"joints={[round(x, 3) for x in state['joint_pos']]}, "
            f"tcp={[round(x, 3) for x in state['tcp_pose']]}, "
            f"gripper={state['gripper_pos']:.3f}"
        )

    args = build_parser().parse_args()
    client = ArmLcmClient(args.url)

    if args.cmd == "cartesian":
        client.set_cartesian_cmd(args.tcp_pose, args.gripper, args.preview_time)

    elif args.cmd == "joint":
        client.set_joint_cmd(args.joint_pos, args.gripper, args.preview_time)

    elif args.cmd == "home":
        client.set_to_home()

    elif args.cmd == "passive":
        client.set_to_passive()

    elif args.cmd == "state":
        state = client.get_state()
        if state is None:
            print("No state received.")
        else:
            print_state(state)
