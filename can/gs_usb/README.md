# Jetson 上安装 candleLight `gs_usb` 驱动

## 问题结论

这台 Jetson 能正常枚举 USB-CAN：

```text
ID 1d50:606f OpenMoko, Inc. Geschwister Schneider CAN adapter
Product: candleLight USB to CAN adapter
```

但是 JetPack/L4T 36.4.7 自带的 `5.15.148-tegra` 内核没有启用
`CONFIG_CAN_GS_USB`，系统中也不存在 `gs_usb.ko`。因此设备会出现在
`lsusb` 中，却不会生成 SocketCAN 网络接口。

这里采用外置内核模块方式，只编译并安装 `gs_usb.ko`，不重编译内核、
不修改设备树，也不需要刷机。

## 已验证环境

```text
JetPack/L4T kernel: 5.15.148-tegra
Architecture:       aarch64
USB device:         1d50:606f
Source:             Linux stable v5.15.148 gs_usb.c
```

本机已有以下编译条件：

```text
nvidia-l4t-kernel-headers 5.15.148-tegra-36.4.7
gcc 11.4.0
make
curl
```

## 编译

进入本目录并运行：

```bash
cd ~/python_ws/agx_control/can/gs_usb
./build_gs_usb.sh
```

脚本会完成以下操作：

1. 下载 Linux stable `v5.15.148` 的 `drivers/net/can/usb/gs_usb.c`。
2. 校验源码 SHA-256，避免下载内容意外变化。
3. 使用当前 Jetson 内核头文件单独编译模块。
4. 输出模块的设备别名、依赖和 `vermagic`。

生成文件位于：

```text
build/5.15.148-tegra/gs_usb.ko
```

正确的兼容性信息应包含：

```text
alias:    usb:v1D50p606F...
depends:  can-dev
vermagic: 5.15.148-tegra ... aarch64
```

编译时可能出现 GCC 小版本字符串不同的 warning。本机内核和模块都使用
GCC 11.4.0，这种仅 Ubuntu 包修订号不同的提示不影响模块加载。

## 安装并加载

安装需要管理员密码：

```bash
cd ~/python_ws/agx_control/can/gs_usb
./build_gs_usb.sh --install
```

该命令会把模块安装到：

```text
/lib/modules/5.15.148-tegra/extra/gs_usb.ko
```

随后执行 `depmod` 和 `modprobe gs_usb`。模块安装并建立依赖后，再次插入
USB-CAN 时内核会根据 USB ID 自动加载它，不需要把模块额外写入
`/etc/modules`。

## 验证

```bash
lsmod | grep '^gs_usb'
lsusb -d 1d50:606f
lsusb -t
ip -details link show type can
```

`lsusb -t` 中该设备应显示 `Driver=gs_usb`。Jetson 内置控制器已经占用了
`can0` 和 `can1`，所以 USB-CAN 初次连接时通常会成为 `can2`。为避免和
片上控制器混淆，后续将机械臂的 USB-CAN 重命名为 `can_agx`。

还可以检查最近的内核日志：

```bash
sudo dmesg --color=always | tail -n 50
```

## 启用 CAN 接口

这台 Jetson 上机械臂 USB-CAN 的硬件地址是 `1-4.1.2:1.0`。使用项目脚本将
它重命名为 `can_agx`，设置为 1 Mbit/s 并启用：

```bash
cd ~/python_ws/agx_control
bash ./can/can_activate.sh can_agx 1000000 "1-4.1.2:1.0"
ip -details link show can_agx
candump can_agx
```

CAN 总线上应有匹配波特率的其他节点、正确的 CAN_H/CAN_L 接线，以及总线
两端各一个 120 欧姆终端电阻。没有其他节点应答时持续发送可能导致接口进入
`BUS-OFF`。

## 卸载

先停止使用该 CAN 接口的程序，再执行：

```bash
cd ~/python_ws/agx_control/can/gs_usb
./build_gs_usb.sh --uninstall
```

仅清理本目录中的编译产物：

```bash
./build_gs_usb.sh --clean
```

## 内核升级

内核模块只能加载到与其构建版本匹配的内核。JetPack/L4T 升级后，如果
`uname -r` 不再是 `5.15.148-tegra`，不要强行加载现有模块。应改用新内核
对应的 `gs_usb.c` 和内核头文件重新编译；当前脚本会主动拒绝为其他内核构建，
避免生成看似成功但不兼容的模块。

如果 NVIDIA 后续内核已经自带 `gs_usb.ko`，直接使用系统模块即可，不再需要
本目录中的外置模块。
