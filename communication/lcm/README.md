# Arm LCM

Default URL: `udpm://239.255.76.67:7667?ttl=1`

Generate Python message classes:

```bash
cd communication/lcm
lcm-gen -p defs/*.lcm
```

Run server on the robot:

```bash
arm_lcm_server
```

Send with the helper client:

```bash
python arm_lcm_client.py home
python arm_lcm_client.py passive
python arm_lcm_client.py joint 0 0 0 0 0 0 --gripper 0
python arm_lcm_client.py cartesian 0.3 0 0.5 0 0 0 --gripper 0.05
python arm_lcm_client.py state
```

Send from your own Python code:

```python
from arm_lcm_client import ArmLcmClient

client = ArmLcmClient()
client.set_to_home()
client.set_to_passive()
client.set_joint_cmd([0, 0, 0, 0, 0, 0], gripper=0.0)
client.set_cartesian_cmd([0.3, 0.0, 0.5, 0.0, 0.0, 0.0], gripper=0.05)
```

Receive state:

```python
state = client.get_state()
print(state["joint_pos"], state["tcp_pose"], state["gripper_pos"])
```
