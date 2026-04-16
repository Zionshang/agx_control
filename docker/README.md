# Docker

Init submodules:

```bash
git submodule update --init --recursive
```

Build image:

```bash
docker build \
  --network=host \
  --build-arg HTTP_PROXY=http://127.0.0.1:7890 \
  --build-arg HTTPS_PROXY=http://127.0.0.1:7890 \
  -f docker/Dockerfile \
  -t agx-control:latest \
  .
```

The image installs `pyAgxArm` through `pyproject.toml` from
`third_party/pyAgxArm`, not from a remote Git URL.

Export image:

```bash
docker save agx-control:latest -o agx-control.tar
gzip agx-control.tar
```

Copy `agx-control.tar.gz` to another computer.

Load image on the other computer:

```bash
gunzip agx-control.tar.gz
docker load -i agx-control.tar
```

Enter container:

```bash
docker run --rm -it \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  agx-control:latest
```

Run inside container:

```bash
arm_lcm_server
keyboard_control
joystick_control
```

For joystick:

```bash
docker run --rm -it \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  --device /dev/input \
  agx-control:latest
```
