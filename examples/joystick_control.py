#!/usr/bin/env python3
import time
from math import pi

import pygame
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config


dt = 0.02
pos_step = 0.002
rot_step = 0.01
gripper_step = 0.001
gripper_force = 1.0
gripper_max = 0.1
deadzone = 0.1
home = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
tcp_offset = [0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0]

axis_left_x = 0
axis_left_y = 1
axis_right_x = 3
axis_right_y = 4

button_b = 1
button_x = 2
button_lb = 4
button_rb = 5
button_view = 6


def dz(value):
    return 0.0 if abs(value) < deadzone else value


def get_axis(joy, index):
    return joy.get_axis(index) if joy.get_numaxes() > index else 0.0


def get_button(joy, index):
    return joy.get_button(index) if joy.get_numbuttons() > index else 0


def get_hat(joy):
    return joy.get_hat(0) if joy.get_numhats() > 0 else (0, 0)


def clamp_pose(pose):
    pose[3] = max(-pi, min(pi, pose[3]))
    pose[4] = max(-pi / 2, min(pi / 2, pose[4]))
    pose[5] = max(-pi, min(pi, pose[5]))


def main():
    cfg = create_agx_arm_config(
        robot=ArmModel.PIPER_L,
        firmeware_version=PiperFW.V183,
        channel="can0",
    )
    robot = AgxArmFactory.create_arm(cfg)
    gripper = robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No joystick found")

    joy = pygame.joystick.Joystick(0)
    joy.init()

    try:
        robot.connect()
        start_t = time.monotonic()
        while not robot.enable() and time.monotonic() - start_t < 3.0:
            time.sleep(0.01)
        if time.monotonic() - start_t >= 3.0:
            print("Failed to enable robot within 3 seconds.")
            raise SystemExit(1)
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

        print("Piper-L joystick control")
        print("left stick: x/y, d-pad up/down: z, d-pad left/right: roll")
        print("right stick: pitch/yaw, LB/RB: close/open gripper")
        print("View: home, X/B or Ctrl-C: quit")

        running = True
        home_pressed = False
        while running:
            pygame.event.pump()
            hat_x, hat_y = get_hat(joy)

            if get_button(joy, button_x) or get_button(joy, button_b):
                running = False

            if get_button(joy, button_view) and not home_pressed:
                robot.move_j(home)
                time.sleep(1.0)
                pose_msg = robot.get_tcp_pose()
                if pose_msg is not None:
                    target = list(pose_msg.msg)
            home_pressed = bool(get_button(joy, button_view))

            target[0] += -dz(get_axis(joy, axis_left_y)) * pos_step
            target[1] += -dz(get_axis(joy, axis_left_x)) * pos_step
            target[2] += hat_y * pos_step
            target[3] += hat_x * rot_step
            target[4] += -dz(get_axis(joy, axis_right_y)) * rot_step
            target[5] += -dz(get_axis(joy, axis_right_x)) * rot_step

            gripper_cmd = get_button(joy, button_rb) - get_button(joy, button_lb)

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
        robot.disconnect()
        pygame.quit()


if __name__ == "__main__":
    main()
