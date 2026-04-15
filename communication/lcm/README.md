# Arm LCM

Default URL: `udpm://239.255.76.67:7667?ttl=1`

Generate Python message classes:

```bash
cd communication/lcm
lcm-gen -p defs/*.lcm
```

Run server on the robot:

```bash
cd communication/lcm
python arm_lcm_server.py
```

Send with the helper client:

```bash
python arm_lcm_client.py home
python arm_lcm_client.py passive
python arm_lcm_client.py joint 0 0 0 0 0 0 --gripper 0
python arm_lcm_client.py cartesian 0.3 0 0.5 0 0 0 --gripper 0.05
```

Send from your own Python code:

```python
import lcm
from msg import ArmCartesianCmd, ArmJointCmd, ArmServiceCmd

lc = lcm.LCM("udpm://239.255.76.67:7667?ttl=1")

cmd = ArmCartesianCmd()
cmd.tcp_pose = [0.3, 0.0, 0.5, 0.0, 0.0, 0.0]
cmd.gripper_pos = 0.05
cmd.preview_time = 0.0
lc.publish("ARM_CARTESIAN_CMD", cmd.encode())
```

Other messages:

```python
cmd = ArmJointCmd()
cmd.num_joints = 6
cmd.joint_pos = [0, 0, 0, 0, 0, 0]
cmd.gripper_pos = 0.0
cmd.preview_time = 0.0
lc.publish("ARM_JOINT_CMD", cmd.encode())
```

```python
cmd = ArmServiceCmd()
cmd.command = ArmServiceCmd.HOME      # or ArmServiceCmd.PASSIVE
lc.publish("ARM_SERVICE_CMD", cmd.encode())
```
