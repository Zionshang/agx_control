import curses
import sys
import time
from math import pi

from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config


dt = 0.01
pos_step = 0.001
rot_step = 0.005
gripper_step = 0.001
gripper_force = 1.0
gripper_max = 0.1
home = [0., 0., 0., 0., 0., 0.]
tcp_offset = [0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0]


def clamp_pose(pose):
    pose[3] = max(-pi, min(pi, pose[3]))
    pose[4] = max(-pi / 2, min(pi / 2, pose[4]))
    pose[5] = max(-pi, min(pi, pose[5]))


def add_status_line(screen, row, text):
    height, width = screen.getmaxyx()
    if row >= height:
        return
    screen.move(row, 0)
    screen.clrtoeol()
    screen.addnstr(row, 0, text, max(0, width - 1))


def draw_status(screen, target, gripper_pos):
    add_status_line(screen, 0, "Piper-L keyboard teleop")
    add_status_line(
        screen,
        1,
        "arrows: x/y, page up/down: z, q/a: roll, w/s: pitch, e/d: yaw",
    )
    add_status_line(screen, 2, "r/f: open/close gripper, space: home, esc or ctrl-c: quit")
    add_status_line(
        screen,
        4,
        f"tcp target: {[round(x, 3) for x in target]}, gripper: {gripper_pos:.3f}m",
    )
    screen.refresh()


def apply_key(key, target):
    if key == curses.KEY_UP:
        target[0] += pos_step
    elif key == curses.KEY_DOWN:
        target[0] -= pos_step
    elif key == curses.KEY_LEFT:
        target[1] += pos_step
    elif key == curses.KEY_RIGHT:
        target[1] -= pos_step
    elif key == curses.KEY_PPAGE:
        target[2] += pos_step
    elif key == curses.KEY_NPAGE:
        target[2] -= pos_step
    elif key == ord("q"):
        target[3] += rot_step
    elif key == ord("a"):
        target[3] -= rot_step
    elif key == ord("w"):
        target[4] += rot_step
    elif key == ord("s"):
        target[4] -= rot_step
    elif key == ord("e"):
        target[5] += rot_step
    elif key == ord("d"):
        target[5] -= rot_step


def run_teleop(screen, robot, gripper, target, gripper_pos):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    try:
        curses.set_escdelay(25)
    except AttributeError:
        pass
    screen.keypad(True)
    screen.nodelay(True)
    screen.clear()
    draw_status(screen, target, gripper_pos)

    running = True
    while running:
        home_requested = False
        gripper_cmd = 0

        while True:
            key = screen.getch()
            if key == -1:
                break
            if key in (27, 3):
                running = False
                break
            if 0 <= key < 256:
                key = ord(chr(key).lower())
            if key == ord(" "):
                home_requested = True
            elif key == ord("r"):
                gripper_cmd += 1
            elif key == ord("f"):
                gripper_cmd -= 1
            else:
                apply_key(key, target)

        if not running:
            break

        if home_requested:
            robot.move_j(home)
            time.sleep(1.0)
            pose_msg = robot.get_tcp_pose()
            if pose_msg is not None:
                target[:] = list(pose_msg.msg)

        clamp_pose(target)
        robot.move_p(robot.get_tcp2flange_pose(target))
        if gripper_cmd:
            gripper_pos += gripper_cmd * gripper_step
            gripper_pos = max(0.0, min(gripper_max, gripper_pos))
            gripper.move_gripper_m(value=gripper_pos, force=gripper_force)
        draw_status(screen, target, gripper_pos)
        time.sleep(dt)

    return gripper_pos


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("keyboard_control requires an interactive terminal.")

    cfg = create_agx_arm_config(
        robot=ArmModel.PIPER_L,
        firmeware_version=PiperFW.V183,
        channel="can_agx",
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

        curses.wrapper(run_teleop, robot, gripper, target, gripper_pos)
    except KeyboardInterrupt:
        print("")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
