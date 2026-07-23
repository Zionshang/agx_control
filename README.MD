## Install
```bash
sudo apt install ethtool
git submodule update --init --recursive
conda create -n agx_control python=3.10
conda activate agx_control
pip install -e .
```

## Usage
### Can
```bash
# 如果你只有一个can设备
./can/can_activate.sh

# 如果多个的话
./can/find_all_can_port.sh
# 根据找到的 port 地址
./can/can_activate.sh can_agx 1000000 "1-4.1.2:1.0"
```
### Keyboard Control
```bash
keyboard_control
```

### Lcm Server
```bash
arm_lcm_server
```