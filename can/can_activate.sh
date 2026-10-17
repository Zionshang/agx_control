#!/bin/bash
set -euo pipefail

# Usage: ./can_activate.sh [CAN_NAME] [BITRATE] [USB_ADDRESS]
# Without USB_ADDRESS, select a detected CAN device interactively.
DEFAULT_CAN_NAME="${1:-can_agx}"
DEFAULT_BITRATE="${2:-1000000}"
USB_ADDRESS="${3:-}"

if [ ${#DEFAULT_CAN_NAME} -gt 15 ]; then
    echo "错误: CAN 接口名称不能超过 15 字节。" >&2
    exit 1
fi
if [[ ! "$DEFAULT_BITRATE" =~ ^[1-9][0-9]*$ ]]; then
    echo "错误: 比特率必须为正整数。" >&2
    exit 1
fi

for tool in ip ethtool; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "错误: 缺少 $tool，请先安装: sudo apt install iproute2 ethtool" >&2
        exit 1
    fi
done

sudo_cmd=()
if [ "$EUID" -ne 0 ]; then
    sudo_cmd=(sudo)
fi

can_links=$(ip -br link show type can)
mapfile -t interfaces < <(awk 'NF {print $1}' <<< "$can_links")
if [ ${#interfaces[@]} -eq 0 ]; then
    echo "错误: 未检测到 CAN 设备，请检查连接和驱动。" >&2
    exit 1
fi

entries=()
INTERFACE_NAME=""
for iface in "${interfaces[@]}"; do
    bus_info=$("${sudo_cmd[@]}" ethtool -i "$iface" 2>/dev/null |
        awk '$1 == "bus-info:" {print $2}') || bus_info=""
    entries+=("$iface (USB: ${bus_info:-未知})")
    if [ -n "$USB_ADDRESS" ] && [ "$bus_info" = "$USB_ADDRESS" ]; then
        INTERFACE_NAME="$iface"
    fi
done

if [ -n "$USB_ADDRESS" ]; then
    if [ -z "$INTERFACE_NAME" ]; then
        echo "错误: 未找到 USB 地址为 $USB_ADDRESS 的 CAN 设备。" >&2
        exit 1
    fi
elif [ ${#interfaces[@]} -eq 1 ]; then
    INTERFACE_NAME="${interfaces[0]}"
    echo "检测到唯一 CAN 设备: ${entries[0]}"
else
    echo "检测到 ${#interfaces[@]} 个 CAN 设备:"
    PS3="请选择 CAN 设备编号: "
    select entry in "${entries[@]}"; do
        if [ -n "$entry" ]; then
            INTERFACE_NAME="${interfaces[10#$REPLY-1]}"
            break
        fi
        echo "编号无效，请重新选择。" >&2
    done
    if [ -z "$INTERFACE_NAME" ]; then
        echo "未选择设备，已取消配置。" >&2
        exit 1
    fi
fi

if [ "$INTERFACE_NAME" != "$DEFAULT_CAN_NAME" ] &&
    ip link show "$DEFAULT_CAN_NAME" >/dev/null 2>&1; then
    echo "错误: 接口 $DEFAULT_CAN_NAME 已存在，请选择该设备或指定其他接口名称。" >&2
    exit 1
fi

echo "配置 $INTERFACE_NAME → $DEFAULT_CAN_NAME，比特率 $DEFAULT_BITRATE"
link_details=$(ip -details link show "$INTERFACE_NAME")
current_bitrate=$(awk '{for (i=1; i<NF; i++) if ($i == "bitrate") {print $(i+1); exit}}' <<< "$link_details")
if [ "$INTERFACE_NAME" = "$DEFAULT_CAN_NAME" ] &&
    [ "$current_bitrate" = "$DEFAULT_BITRATE" ] &&
    grep -Eq '<([^>]*,)?UP(,|>)' <<< "$link_details"; then
    echo "$DEFAULT_CAN_NAME 已启用，无需修改。"
    exit 0
fi

"${sudo_cmd[@]}" ip link set "$INTERFACE_NAME" down
"${sudo_cmd[@]}" ip link set "$INTERFACE_NAME" type can bitrate "$DEFAULT_BITRATE"
if [ "$INTERFACE_NAME" != "$DEFAULT_CAN_NAME" ]; then
    "${sudo_cmd[@]}" ip link set "$INTERFACE_NAME" name "$DEFAULT_CAN_NAME"
fi
"${sudo_cmd[@]}" ip link set "$DEFAULT_CAN_NAME" up
echo "配置完成: $DEFAULT_CAN_NAME，比特率 $DEFAULT_BITRATE，已启用。"
