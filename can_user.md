# CAN 模块使用手册

> 本文档介绍 pyAgxArm 在不同平台下的 CAN 配置方法。

> **注意：** 此处的 CAN 模块仅支持机械臂自带的官方 CAN 模块，不支持其它 CAN 模块。

## 目录

- [切换到 English](#can-module-manual)
- [按平台说明](#按平台说明)
- [前置准备](#前置准备)
- [1. 寻找 CAN 模块](#1-寻找-can-模块)
- [2. 激活单个 CAN 模块](#2-激活单个-can-模块)
- [3. 同时激活多个 CAN 模块](#3-同时激活多个-can-模块)

---

## 按平台说明

### Linux（`socketcan`）

- 支持使用仓库中的 `.sh` 脚本（路径：`pyAgxArm/scripts/ubuntu`）。
- Linux 的脚本化流程详见下方 `1`、`2`、`3` 章节。
- 也可手动激活 CAN，例如：
  `sudo ip link set can0 up type can bitrate 1000000`。

### Windows（`agx_cando`）

- 仓库中的 `.sh` 脚本**不适用于 Windows**。
- 使用 `interface="agx_cando"`，`channel` 通常写 `"0"`、`"1"`、`"2"`。
- 使用 SDK 前，需要先安装 `python-can-agx-cando` 插件。

### macOS（`Darwin`，`slcan`）

- 仓库中的 `.sh` 脚本**不适用于 macOS**。
- 使用 `interface="slcan"`，`channel` 通常写 `"/dev/ttyACM0"`。
- 使用默认串口前，先赋予权限：
  `sudo chmod 777 /dev/ttyACM0`。

---

## 前置准备

**脚本路径：** `scripts`

本文档中的 `.sh` 脚本仅适用于 Linux。以 Ubuntu 为例，脚本路径为 `pyAgxArm/scripts/ubuntu`。

```shell
cd pyAgxArm/scripts/ubuntu
```

**安装 CAN 工具：**

```shell
sudo apt update && sudo apt install can-utils ethtool
```

这两个工具用于配置 CAN 模块。

> **提示：** 如果执行 bash 脚本时出现 `ip: command not found`，请安装 ip 命令：`sudo apt-get install iproute2`

---

## 1. 寻找 CAN 模块

执行：

```bash
bash find_all_can_port.sh
```

输入密码后，如果 CAN 模块已插入电脑并被检测到，输出类似如下：

```
Both ethtool and can-utils are installed.
Interface can0 is connected to USB port 3-1.4:1.0
```

如果有多个 CAN 模块，输出类似如下：

```
Both ethtool and can-utils are installed.
Interface can0 is connected to USB port 3-1.4:1.0
Interface can1 is connected to USB port 3-1.1:1.0
```

其中 `can1` 是系统找到的 CAN 模块名称，`3-1.1:1.0` 是该 CAN 模块连接的 USB 端口。

如果之前已激活过 CAN 模块并命名为其它名字（例如 `can_piper`），则输出如下：

```
Both ethtool and can-utils are installed.
Interface can_piper is connected to USB port 3-1.4:1.0
Interface can0 is connected to USB port 3-1.1:1.0
```

如果没有检测到 CAN 模块，则只会输出：

```
Both ethtool and can-utils are installed.
```

---

## 2. 激活单个 CAN 模块

> 使用 `can_activate.sh` 脚本

### 步骤 1：查看 USB 端口硬件地址

拔掉所有 CAN 模块，只将连接到机械臂的 CAN 模块插入 PC，执行：

```shell
bash find_all_can_port.sh
```

记录下 `USB port` 的数值，例如 `3-1.4:1.0`。

### 步骤 2：激活 CAN 设备

假设上面的 `USB port` 数值为 `3-1.4:1.0`，执行：

```bash
bash can_activate.sh can_piper 1000000 "3-1.4:1.0"
```

含义：将硬件编码为 `3-1.4:1.0` 的 USB 端口上的 CAN 设备重命名为 `can_piper`，设定波特率为 `1000000`，并激活。

### 步骤 3：检查是否激活成功

执行 `ifconfig` 查看是否有 `can_piper`，如果有则 CAN 模块设置成功。

### 简化用法（单模块）

如果电脑只插入了一个 CAN 模块，可以直接执行：

```bash
bash can_activate.sh can0 1000000
```

其中 `can0` 可以改为任意名字，`1000000` 为波特率。

---

## 3. 同时激活多个 CAN 模块

> 使用 `can_muti_activate.sh` 脚本

首先确定有多少个官方 CAN 模块被插入到电脑（以下示例假设为 2 个）。

> **提示：** 若当前电脑插入了 5 个 CAN 模块，也可以只激活指定的 CAN 模块。

### 3.1 记录每个 CAN 模块对应的 USB 端口硬件地址

逐个拔插 CAN 模块并一一记录每个模块对应的 USB 端口硬件地址。

在 `can_muti_activate.sh` 中，`USB_PORTS` 参数中元素的数量为预激活的 CAN 模块数量。

**（1）** 将其中一个 CAN 模块单独插入 PC，执行：

```shell
bash find_all_can_port.sh
```

记录下 `USB port` 的数值，例如 `3-1.4:1.0`。

**（2）** 接着插入下一个 CAN 模块（**不可以**与上次插入的 USB 口相同），执行：

```shell
bash find_all_can_port.sh
```

记录下第二个 CAN 模块的 `USB port` 数值，例如 `3-1.1:1.0`。

> **提示：** 如果未曾激活过，则第一个插入的 CAN 模块默认为 `can0`，第二个为 `can1`；若激活过，名字为之前激活过的名称。

### 3.2 预定义 USB 端口、目标接口名称及波特率

假设上面记录的 `USB port` 数值分别为 `3-1.4:1.0` 和 `3-1.1:1.0`，则将 `can_muti_activate.sh` 中的参数修改为：

```bash
USB_PORTS["3-1.4:1.0"]="can_left:1000000"
USB_PORTS["3-1.1:1.0"]="can_right:1000000"
```

含义：`3-1.4:1.0` 端口的 CAN 设备重命名为 `can_left`，波特率 `1000000`，并激活。

### 3.3 激活多个 CAN 模块

执行：

```bash
bash can_muti_activate.sh
```

### 3.4 验证是否设置成功

执行 `ifconfig` 查看是否有 `can_left` 和 `can_right`。
