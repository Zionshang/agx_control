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
# 自动扫描 CAN 设备，多个时输入编号选择，只有一个时自动配置
./can/can_activate.sh
```

默认设置为 `can_agx`，比特率为 `1000000`。也可指定名称和比特率：`./can/can_activate.sh can_agx 500000`。
### Keyboard Control
```bash
keyboard_control
```

### Lcm Server
```bash
arm_lcm_server
```

`keyboard_control` 和 `arm_lcm_server` 启动时自动使能并回到 home（六个关节角均为 0）；退出时发送 home 指令，等待 2 秒，再切换到 passive（失能），最后断开连接。支持正常退出、Ctrl-C 和 SIGTERM。

`arm_lcm_server` 与键盘控制一样，仅在启动时等待使能；收到关节、笛卡尔或 home 命令时直接发送运动指令，不重复使能。
