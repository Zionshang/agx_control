#!/usr/bin/env python3
from pyAgxArm import AgxArmFactory, ArmModel, PiperFW, create_agx_arm_config
import time

cfg = create_agx_arm_config(robot=ArmModel.PIPER_L, firmeware_version=PiperFW.V183)
robot = AgxArmFactory.create_arm(cfg)
gripper = robot.init_effector(robot.OPTIONS.EFFECTOR.AGX_GRIPPER)
robot.set_tcp_offset([0.0, 0.0, 0.13, 0.0, -1.57079632679, 0.0])

try:
    robot.connect()
    while not robot.enable():
        time.sleep(0.01)
    joint_angles = robot.get_joint_angles()
    flange_pose = robot.get_flange_pose()
    tcp_pose = robot.get_tcp_pose()
    gripper_status = gripper.get_gripper_status()

    print("joint_angles:", joint_angles.msg if joint_angles else None)
    print("flange_pose:", flange_pose.msg if flange_pose else None)
    print("tcp_pose:", tcp_pose.msg if tcp_pose else None)
    print("gripper_status:", gripper_status.msg.value if gripper_status else None)
finally:
    robot.disconnect()
