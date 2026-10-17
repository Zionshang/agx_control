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
git submodule update --init --recursive
docker build -f docker/Dockerfile -t agx-control:latest .
```

Docker installs `pyAgxArm` from `third_party/pyAgxArm`.

Enter the Docker shell:

```bash
docker run --rm -it \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  agx-control:latest
```

Run this on the Linux robot host so `--network host` can expose the host
`can_agx` SocketCAN interface and LCM multicast traffic to the container.

Run commands inside the container:

```bash
arm_lcm_server
arm_lcm_server --url "udpm://239.255.76.67:7667?ttl=1"
keyboard_control
joystick_control
```

The robot host should expose and configure `can_agx` before starting the
container. From the project root, run `can_activate.sh` to select and configure
the CAN device, then check the interface:

```bash
./can/can_activate.sh
ip link show can_agx
```

Run examples directly after installing this package outside Docker:

```bash
git submodule update --init --recursive
python -m pip install -e .
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
  agx-control:latest
```

`keyboard_control` uses standard terminal keyboard input and must run in an
interactive TTY. `joystick_control` needs access to the host joystick input
device.

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
print(state["arm_status"], state["target_utime"])
```

`arm_status` reports the Piper controller error code (`-1` means no status
feedback is available). `target_utime` identifies the most recently accepted
motion command (`0` means no target). Match it with the command timestamp when
multiple commands may overlap.
