#!/usr/bin/env python3
import time
from math import pi

from pynput import keyboard
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config


dt = 0.02
pos_step = 0.001
rot_step = 0.005
gripper_step = 0.001
gripper_force = 1.0
gripper_max = 0.1
home = [0., 0., 0., 0., 0., 0.]
tcp_offset = [0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0]

keys = {
    keyboard.Key.up: False,
    keyboard.Key.down: False,
    keyboard.Key.left: False,
    keyboard.Key.right: False,
    keyboard.Key.page_up: False,
    keyboard.Key.page_down: False,
    keyboard.Key.space: False,
    keyboard.KeyCode.from_char("q"): False,
    keyboard.KeyCode.from_char("a"): False,
    keyboard.KeyCode.from_char("w"): False,
    keyboard.KeyCode.from_char("s"): False,
    keyboard.KeyCode.from_char("e"): False,
    keyboard.KeyCode.from_char("d"): False,
    keyboard.KeyCode.from_char("r"): False,
    keyboard.KeyCode.from_char("f"): False,
}
running = True


def norm_key(key):
    if isinstance(key, keyboard.KeyCode) and key.char:
        return keyboard.KeyCode.from_char(key.char.lower())
    return key


def on_press(key):
    global running
    key = norm_key(key)
    if key == keyboard.Key.esc:
        running = False
        return False
    if key in keys:
        keys[key] = True
    return None


def on_release(key):
    key = norm_key(key)
    if key in keys:
        keys[key] = False
    return None


def axis(pos_key, neg_key):
    return int(keys[pos_key]) - int(keys[neg_key])


def clamp_pose(pose):
    pose[3] = max(-pi, min(pi, pose[3]))
    pose[4] = max(-pi / 2, min(pi / 2, pose[4]))
    pose[5] = max(-pi, min(pi, pose[5]))


def main():
    global running

    cfg = create_agx_arm_config(
        robot=ArmModel.PIPER_L,
        firmeware_version=PiperFW.V183,
        channel="can0",
    )
    robot = AgxArmFactory.create_arm(cfg)
    gripper = robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)

    try:
        robot.connect()
        while not robot.enable():
            time.sleep(0.01)
        robot.set_speed_percent(100)
        robot.set_tcp_offset(tcp_offset)
        robot.move_j(home)
        time.sleep(1.0)

        pose_msg = None
        while pose_msg is None:
            pose_msg = robot.get_tcp_pose()
            time.sleep(0.01)
        target = list(pose_msg.msg)

        gripper_pos = 0.0
        gripper_status = gripper.get_gripper_status()
        if gripper_status is not None:
            gripper_pos = max(0.0, min(gripper_max, gripper_status.msg.value))

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        print("Piper-L keyboard teleop")
        print("arrows: x/y, page up/down: z, q/a: roll, w/s: pitch, e/d: yaw")
        print("r/f: open/close gripper, space: home, esc or ctrl-c: quit")

        while running:
            if keys[keyboard.Key.space]:
                robot.move_j(home)
                time.sleep(1.0)
                pose_msg = robot.get_tcp_pose()
                if pose_msg is not None:
                    target = list(pose_msg.msg)
                keys[keyboard.Key.space] = False

            target[0] += axis(keyboard.Key.up, keyboard.Key.down) * pos_step
            target[1] += axis(keyboard.Key.left, keyboard.Key.right) * pos_step
            target[2] += axis(keyboard.Key.page_up, keyboard.Key.page_down) * pos_step
            target[3] += (
                axis(keyboard.KeyCode.from_char("q"), keyboard.KeyCode.from_char("a"))
                * rot_step
            )
            target[4] += (
                axis(keyboard.KeyCode.from_char("w"), keyboard.KeyCode.from_char("s"))
                * rot_step
            )
            target[5] += (
                axis(keyboard.KeyCode.from_char("e"), keyboard.KeyCode.from_char("d"))
                * rot_step
            )
            gripper_cmd = axis(
                keyboard.KeyCode.from_char("r"), keyboard.KeyCode.from_char("f")
            )

            clamp_pose(target)
            robot.move_p(robot.get_tcp2flange_pose(target))
            if gripper_cmd:
                gripper_pos += gripper_cmd * gripper_step
                gripper_pos = max(0.0, min(gripper_max, gripper_pos))
                gripper.move_gripper_m(value=gripper_pos, force=gripper_force)
            print(
                (
                    f"tcp target: {[round(x, 3) for x in target]}, "
                    f"gripper: {gripper_pos:.3f}m"
                ),
                end="\r",
            )
            time.sleep(dt)
    except KeyboardInterrupt:
        print("")
    finally:
        running = False
        robot.disconnect()


if __name__ == "__main__":
    main()
