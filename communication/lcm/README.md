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

Build Docker image:

```bash
docker build -f docker/Dockerfile -t agx-control-arm-lcm .
```

The build needs network access because `pyAgxArm` is installed from GitHub.

Enter the Docker shell:

```bash
docker run --rm -it \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  agx-control-arm-lcm
```

Run this on the Linux robot host so `--network host` can expose the host
`can0` SocketCAN interface and LCM multicast traffic to the container.

Run commands inside the container:

```bash
arm_lcm_server
arm_lcm_server --url "udpm://239.255.76.67:7667?ttl=1"
keyboard_control
joystick_control
```

The robot host should expose and configure `can0` before starting the
container. For example, use the scripts in `can/` or check it with:

```bash
ip link show can0
```

Run examples directly after installing this package outside Docker:

```bash
keyboard_control
joystick_control
```

For joystick control in Docker, pass the host input device when entering the
container:

```bash
docker run --rm -it \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  --device /dev/input \
  agx-control-arm-lcm
```

`keyboard_control` depends on Linux desktop keyboard input support, and
`joystick_control` needs access to the host joystick input device.

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
