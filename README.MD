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

### Gravity Compensation / Joint Angles

```bash
python -m examples.gravity_compensation --channel can_agx --rate 20
# 重新执行 pip install -e . 后也可使用：
gravity_compensation --channel can_agx --rate 20
```

适用于 Piper-L V1.8.3：使能后进入固件提供的 Leader 零力拖动模式（重力补偿由固件完成），默认以 20 Hz 输出 J1～J6 当前关节角度，包含弧度（rad）和角度（deg）。读取 Leader 模式关节反馈；尚未收到反馈时输出等待提示。`--rate` 控制输出频率。

Ctrl-C 或 SIGTERM 退出时先发送 Leader 专用回零指令（`move_leader_to_home`），等待 2 秒，再切回 Follower 模式；等待 0.1 秒后发送普通关节位置模式指令，分别发送夹爪失能和机械臂关节失能指令，等待 0.1 秒后断开连接。退出流程只发送指令并固定等待，不检查到位反馈。启动时不回 home。

`keyboard_control`、`joystick_control` 和 `arm_lcm_server` 启动时自动使能并回到 home（六个关节角均为 0）；退出时发送 home 指令，等待 2 秒，分别发送夹爪失能和机械臂关节失能指令，等待 0.1 秒后断开连接。支持正常退出、Ctrl-C 和 SIGTERM。

LCM 的 `PASSIVE` 命令也会同时失能夹爪与机械臂，并取消尚未完成的夹爪运动。

`arm_lcm_server` 与键盘控制一样，仅在启动时等待使能；收到关节、笛卡尔或 home 命令时直接发送运动指令，不重复使能。
