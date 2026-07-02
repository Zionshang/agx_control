## Install
```bash
sudo apt install ethtool
conda create -n agx_control python=3.10
conda activate agx_control
pip install -e .
```

## Usage
### Can
```bash
# 如果你只有一个can设备
./can/can_activate.sh
```
### Keyboard Control
```bash
keyboard_control
```

### Lcm Server
```bash
arm_lcm_server
```