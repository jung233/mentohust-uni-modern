# mentohust-uni-modern

`mentohust-uni-modern` 是用于校园网有线 802.1X 认证的跨平台客户端，提供图形界面（GUI）和命令行界面（CLI）。目前发布 Windows x64、Linux amd64 和 Linux arm64 版本。CLI 可在没有桌面环境的设备上运行，例如 ARM 开发板。

本项目基于 [huangli2006920-coder/mentohust-win-modern](https://github.com/huangli2006920-coder/mentohust-win-modern) 继续开发。感谢原项目作者提供 Windows 图形客户端和认证实现的基础；相关参考项目及致谢见[项目来源与致谢](#项目来源与致谢)。

## 功能与适用范围

- 通过所选网卡发送和接收 EAPOL 认证报文。Wi-Fi 与有线网络可以同时连接；普通上网流量走哪张网卡由操作系统路由决定。
- GUI 和 CLI 使用相同的 JSON 配置格式。CLI 支持列出网卡、生成配置、检查运行环境和前台认证。
- Windows 支持托盘和启动时自动连接；Linux GUI 需要图形会话，Linux CLI 不需要图形环境。
- 发行包包含锐捷官方 `8021x.exe` 参考文件。程序只读取其中的数据来计算兼容性校验，Linux 不执行该 EXE，也不需要 Wine。

本项目适用于使用兼容认证流程的校园网。认证参数因学校而异，CI 的启动检查不能代替在目标校园网进行的认证测试。

## 下载与运行要求

从 [Releases](https://github.com/jung233/mentohust-uni-modern/releases/latest) 下载与系统和架构匹配的压缩包，并**完整解压整个目录**。只复制主程序会漏掉 `_internal` 中的 Python 运行库和其他文件。

项目名称是 `mentohust-uni-modern`；现有发行包目录和可执行文件仍沿用历史名称 `MentoHUST Modern` / `mentohust-modern-cli`。

| 系统 | GUI 包 | CLI 包 |
| --- | --- | --- |
| Windows x64 | `*-windows-x64.zip` | `*-windows-x64-cli.zip` |
| Linux amd64 | `*-linux-amd64.tar.gz` | `*-linux-amd64-cli.tar.gz` |
| Linux arm64 | `*-linux-arm64.tar.gz` | `*-linux-arm64-cli.tar.gz` |

每个压缩包旁边都有对应的 `.sha256` 校验文件。Linux 发行包在 Ubuntu 22.04 上构建，CI 检查包内 ELF 文件的 GLIBC 符号需求不超过 **2.35**；运行环境还需满足下列系统依赖。

| 系统 | 运行要求 |
| --- | --- |
| Windows | 管理员权限、[Npcap](https://npcap.com/) |
| Linux CLI | root 权限、`libpcap`、`iproute2`；使用默认 DHCP 流程时还需要 `dhclient`（通常由 `isc-dhcp-client` 提供） |
| Linux GUI | Linux CLI 的依赖，以及 Tk/X11 图形运行环境；从图形会话启动时需保留 `DISPLAY` 等环境变量 |

还需要可用的校园网账号和已连接到校园网认证端口的有线网卡。

## CLI 使用

以下示例在**解压目录的上一级**执行。命令中的 `eth0` 只是示例，请换成实际接网线的接口；Windows 则使用 `--list-interfaces` 显示的接口名。

### Linux amd64 / arm64

```bash
# 解压对应架构的 CLI 包；以 arm64 为例
tar -xzf MentoHUST-Modern-v1.0.2-linux-arm64-cli.tar.gz

# 查看接口名和 MAC 地址
./mentohust-modern-cli/mentohust-modern-cli --list-interfaces

# 创建 JSON 配置，自动写入所选网卡信息；已有文件不会被覆盖
./mentohust-modern-cli/mentohust-modern-cli --config ./config.json --init-config --interface eth0

# 编辑 config.json 中的 username 和 password，然后检查配置及系统依赖
./mentohust-modern-cli/mentohust-modern-cli --config ./config.json --check

# 在前台开始认证
sudo ./mentohust-modern-cli/mentohust-modern-cli --config "$(pwd)/config.json"
```

以 Ubuntu 22.04 为例，缺少系统依赖时可安装 `libpcap0.8`、`iproute2` 和 `isc-dhcp-client`。其他发行版请使用对应的软件包名。按 `Ctrl+C` 停止前台认证；收到 `SIGINT` 或 `SIGTERM` 时，客户端会尽力发送 Logoff。

### Windows x64

在**管理员 PowerShell** 中进入解压目录的上一级：

```powershell
.\mentohust-modern-cli\mentohust-modern-cli.exe --list-interfaces
.\mentohust-modern-cli\mentohust-modern-cli.exe --config .\config.json --init-config --interface "以太网"
# 编辑 config.json 中的 username 和 password
.\mentohust-modern-cli\mentohust-modern-cli.exe --config .\config.json --check
.\mentohust-modern-cli\mentohust-modern-cli.exe --config .\config.json
```

`--interface eth0` 或 `--interface "以太网"` 可以在 `--check` 和认证时**临时覆盖** JSON 中选定的网卡，但不会写回已有配置。若要持久保存，编辑 JSON，或在创建新配置时使用 `--init-config --interface ...`。

不指定 `--config` 时，CLI 使用与 GUI 相同的默认配置文件：Windows 为 `%LOCALAPPDATA%\MentoHUST Win Modern\profiles\default.json`，Linux 为 `${XDG_CONFIG_HOME:-~/.config}/mentohust-modern/profiles/default.json`。

### Linux：注册为 systemd 守护进程

先按上面的步骤完成 JSON 配置，并确认前台认证能正常工作。下面假设发行包完整解压在 `/root/mentohust-modern-cli/`，配置文件位于 `/root/config.json`；如果你使用其他目录，请同步修改服务文件中的绝对路径。若配置已保存在 root 用户的默认路径 `/root/.config/mentohust-modern/profiles/default.json`，也可从 `ExecStart` 省略 `--config /root/config.json`。服务默认以 root 身份运行，以便抓发 EAPOL 报文。

```bash
# 先检查配置和依赖，并限制明文密码配置文件的读取权限
chmod 600 /root/config.json
/root/mentohust-modern-cli/mentohust-modern-cli --config /root/config.json --check

sudo tee /etc/systemd/system/mentohust.service >/dev/null <<'EOF'
[Unit]
Description=mentohust-uni-modern wired 802.1X authentication
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/mentohust-modern-cli
ExecStart=/root/mentohust-modern-cli/mentohust-modern-cli --config /root/config.json
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemd-analyze verify /etc/systemd/system/mentohust.service
sudo systemctl daemon-reload
sudo systemctl enable --now mentohust.service
```

这里使用 `After=network.target`，使服务在网络管理组件启动后运行。认证可能是获得可用网络的前提，因此不等待 `network-online.target`；若进程因接口未就绪等原因退出，`Restart=always` 会在 5 秒后重新启动。关于两个 target 的区别，参见 [systemd 的网络启动说明](https://wiki.freedesktop.org/www/Software/systemd/NetworkTarget/)。

```bash
# 查看状态和实时日志
systemctl status mentohust.service
journalctl -u mentohust.service -f

# 修改配置后重启；修改服务文件后还需先执行 daemon-reload
sudo systemctl restart mentohust.service

# 停止并取消开机自启
sudo systemctl disable --now mentohust.service
```

`systemctl stop` 或关机时会向 CLI 发送 `SIGTERM`；客户端会尽力发送 Logoff。若服务反复重启，请先用 `journalctl -u mentohust.service -n 100 --no-pager` 查看报错，并确认网卡名、账号、系统依赖及配置路径。

## GUI 使用

### Windows

1. 安装 Npcap，完整解压 Windows GUI 包，运行 `MentoHUST Win Modern\MentoHUST Win Modern.exe`。程序需要管理员权限。
2. 输入校园网用户名、密码，从“网卡”下拉框中选择**插有校园网网线**的接口。
3. Release 包内已附带 `8021x.exe` 参考文件，“官方 8021x.exe”可以留空；按学校要求调整客户端版本、组播地址和 DHCP 模式。
4. 点击“连接”，在状态栏和运行日志中查看认证结果。点击“断开”结束认证。可按需启用“启动时自动连接”。

Windows 版关闭主窗口时会最小化到托盘；可以从托盘恢复或退出。界面修改会自动保存到默认 JSON，也可用“保存 JSON 配置”导出。

### Linux

在图形桌面会话中完整解压 Linux GUI 包，然后以 root 权限启动。例如：

```bash
sudo -E "./MentoHUST Modern/MentoHUST Modern"
```

`-E` 用于保留图形会话的环境变量。配置步骤与 Windows 相同。Linux 版没有托盘，关闭窗口会退出程序。GUI 还提供“刷新网卡”“加载 JSON 配置”“导入 OpenWrt 配置”和“打开日志目录”等操作。

## JSON 配置文件

GUI 与 CLI 共用 `MentohustConfig` 格式。下面是一份 Linux `eth0` 示例；请替换账号、密码、接口名和 MAC，其他参数可先保持示例值，再根据学校要求调整：

```json
{
  "enable": true,
  "auto_connect": false,
  "username": "你的校园网账号",
  "password": "你的校园网密码",
  "interface_description": "eth0",
  "interface_id": "eth0",
  "interface_mac": "aa:bb:cc:dd:ee:ff",
  "ipaddr": "0.0.0.0",
  "gateway": "0.0.0.0",
  "mask": "0.0.0.0",
  "ping": "0.0.0.0",
  "timeout": 8,
  "interval": 30,
  "wait": 15,
  "fail_number": 0,
  "multicast_address": 1,
  "dhcp_mode": 2,
  "dhcp_script": "",
  "version": "5.00",
  "dns": "0.0.0.0",
  "client_exe": ""
}
```

| 字段 | 说明 |
| --- | --- |
| `username`、`password` | 校园网认证账号和密码；密码以明文保存在 JSON 中，请限制文件读取权限，例如 Linux 上执行 `chmod 600 config.json`。 |
| `interface_id`、`interface_description`、`interface_mac` | 认证网卡的接口名、描述和 MAC。Linux 上通常前两项都是 `eth0` 一类名称；可从 `--list-interfaces` 的三列输出依次取得。查找时优先匹配 ID，再匹配 MAC，最后匹配描述。 |
| `client_exe` | Release 包中留空即可使用内置 `8021x.exe`；仅在需要指定其他参考文件时填写路径。Linux 把它当作数据文件读取，不执行它。 |
| `version` | 向认证服务器声明的客户端版本，默认 `5.00`；应按目标校园网要求设置。 |
| `ipaddr`、`gateway`、`mask`、`dns` | 填 `0.0.0.0` 时读取所选网卡的当前网络信息；需要固定值时填写对应 IPv4 地址。 |
| `ping` | 认证报文中的 Ping 目标；`0.0.0.0` 表示不指定。 |
| `timeout`、`interval`、`wait` | 分别为认证超时、心跳间隔和重试等待时间，单位为秒。 |
| `fail_number` | 连续认证失败上限；`0` 表示不设置上限。 |
| `multicast_address` | 寻找服务器的地址模式：`0` 标准、`1` 锐捷、`2` 赛尔。 |
| `dhcp_mode` | `0` 不执行 DHCP；`1` 二次认证时执行；`2` 认证成功后执行；`3` 认证前执行。 |
| `dhcp_script` | 留空使用平台默认命令：Windows 为 `ipconfig /renew`，Linux 为 `dhclient -1`。默认命令只更新所选网卡；自定义命令按填写内容执行。 |
| `enable`、`auto_connect` | GUI 的“启用配置”和“启动时自动连接”选项；CLI 前台启动由命令行控制。 |

例如 Linux 的网卡列表若显示 `eth0  aa:bb:cc:dd:ee:ff  eth0`，就填写 `"interface_id": "eth0"`、`"interface_description": "eth0"` 和 `"interface_mac": "aa:bb:cc:dd:ee:ff"`。请确认该接口确实连接校园网；`wlan0`、`docker0` 等名称可能也出现在列表中。

## 开发与构建

仓库中的 `mentohust-modern/` 是当前 Python GUI、CLI、测试和打包脚本所在目录；`MentoHUST-OpenWrt-ipk/` 保留参考源码。需要 Python 3.12 或更新版本。从仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\mentohust-modern[build]
.\.venv\Scripts\python.exe -m unittest discover -s .\mentohust-modern\tests -t .\mentohust-modern
pwsh.exe -File .\mentohust-modern\tools\build_exe.ps1
```

Linux 本地构建使用 `bash mentohust-modern/tools/build_linux.sh`，需在目标 CPU 架构的 Linux 上运行。GitHub Actions 在 `main` 更新时构建和测试 Windows x64、Linux amd64、Linux arm64；推送 `v*` 标签后发布 GUI、CLI 压缩包及 SHA-256 校验文件。

## 项目来源与致谢

- **项目来源**：[huangli2006920-coder/mentohust-win-modern](https://github.com/huangli2006920-coder/mentohust-win-modern)。感谢原项目作者开发并开放 Windows 图形客户端。本项目在此基础上增加 Linux 支持、无图形环境 CLI、网卡绑定、跨平台配置和自动发布流程。
- **原项目的参考项目**：[KyleRicardo/MentoHUST-OpenWrt-ipk](https://github.com/KyleRicardo/MentoHUST-OpenWrt-ipk)。感谢其维护者提供可对照的认证流程和配置实现；仓库中保留相应参考源码。
- 感谢 [HustLion/mentohust](https://github.com/hustlion/mentohust) 及更早的 MentoHUST 开发者为相关协议实现打下基础，也感谢 OpenWrt 参考项目文档中提到的 [802.1X Evasi0n](https://github.com/KyleRicardo/802.1X-Evasi0n) 项目。

本仓库遵循根目录 [LICENSE](LICENSE) 中的许可条款。使用时请遵守所在网络的接入规定。
