from pyAgxArm import create_agx_arm_config, AgxArmFactory, ArmModel, PiperFW

cfg = create_agx_arm_config(robot=ArmModel.PIPER, firmeware_version=PiperFW.DEFAULT, channel="can0")
robot = AgxArmFactory.create_arm(cfg)
robot.connect()

fw = robot.get_firmware()
if fw is not None:
    print(fw)

# 本机器人为PiperFW.V183