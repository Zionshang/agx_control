"""Use the Piper-L firmware's zero-force drag mode and print joint angles."""

import argparse
import math
import signal
import time

from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config


def positive_rate(value):
    rate = float(value)
    if not math.isfinite(rate) or rate <= 0:
        raise argparse.ArgumentTypeError("rate must be a finite positive number")
    return rate


def handle_sigterm(signum, frame):
    raise SystemExit(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="can_agx", help="SocketCAN interface")
    parser.add_argument("--rate", type=positive_rate, default=20.0, help="output rate in Hz (default: 20)")
    args = parser.parse_args()

    cfg = create_agx_arm_config(
        robot=ArmModel.PIPER_L,
        firmeware_version=PiperFW.V183,
        channel=args.channel,
    )
    robot = AgxArmFactory.create_arm(cfg)
    gripper = robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)
    connected = False
    previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
    try:
        signal.signal(signal.SIGTERM, handle_sigterm)
        robot.connect()
        connected = True
        while not robot.enable():
            time.sleep(0.01)
        robot.set_speed_percent(100)

        # Gravity compensation is handled by the firmware in leader drag mode.
        robot.set_leader_mode()
        robot.restore_leader_drag_mode()
        print("Piper-L zero-force drag mode. Joint order: J1..J6. Ctrl-C to exit.", flush=True)
        while True:
            started = time.monotonic()
            # Leader mode broadcasts joint commands on its own feedback IDs.
            angles = robot.get_leader_joint_angles()
            if angles is None:
                print("Waiting for leader joint feedback...", flush=True)
            else:
                joints = list(angles.msg)
                radians = ", ".join(f"{angle:+.6f}" for angle in joints)
                degrees = ", ".join(f"{math.degrees(angle):+.3f}" for angle in joints)
                print(f"rad: [{radians}]  deg: [{degrees}]", flush=True)
            time.sleep(max(0.0, 1.0 / args.rate - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nExiting zero-force drag mode.", flush=True)
    finally:
        try:
            if connected:
                # Return home while still in leader mode using its dedicated command.
                robot.move_leader_to_home()
                time.sleep(5.0)
                robot.set_follower_mode()
                time.sleep(0.1)
                robot.set_motion_mode(robot.OPTIONS.MOTION_MODE.J)
                gripper.disable_gripper()
                robot.disable()
                time.sleep(0.1)
        finally:
            try:
                robot.disconnect()
            finally:
                signal.signal(signal.SIGTERM, previous_sigterm_handler)


if __name__ == "__main__":
    main()
