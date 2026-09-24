# mentohust-uni-modern 子项目说明

这个子项目是当前维护中的 Windows/Linux GUI 与 CLI 客户端实现。它复用了 `MentoHUST-OpenWrt-ipk` 的认证流程，使用 `Scapy` 进行二层 EAPOL 抓发；Windows 使用 Npcap，Linux 使用 libpcap。项目介绍、发行包使用和完整 JSON 字段说明见[根目录 README](../README.md)。

## 开发与运行

安装可编辑包：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\mentohust-modern[build]
```

从虚拟环境启动 GUI：

```powershell
.\.venv\Scripts\mentohust-win-modern.exe
```

CLI 入口为 `mentohust-modern-cli`，使用和 GUI 相同的 JSON 格式；运行 `--help` 可查看参数。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\mentohust-modern\tests -t .\mentohust-modern
```

## 打包

构建可分发版本：

```powershell
pwsh.exe -File .\mentohust-modern\tools\build_exe.ps1
```

默认输出目录：

```text
dist\MentoHUST Win Modern\
```

构建脚本会自动使用仓库根目录下独立的 `.build-venv/`；如果发现它不可用或引用了其他机器上的 Python，会自动重建后再执行打包。

Linux amd64 / arm64 需要在对应架构的 Linux 上分别构建：

```bash
sudo apt install python3-venv python3-tk libpcap-dev iproute2 isc-dhcp-client
bash mentohust-modern/tools/build_linux.sh
sudo -E "./dist/MentoHUST Modern/MentoHUST Modern"
```

Linux 构建同时输出 GUI `dist/MentoHUST Modern/` 和无图形依赖的 CLI `dist/mentohust-modern-cli/`。CLI 可用 `--init-config --config PATH` 创建 JSON、`--list-interfaces` 查看网卡、`--interface IFACE` 覆盖配置网卡、`--check` 检查环境。认证时以 root 权限运行；默认 DHCP 使用 `dhclient -1 <所选网卡>`。GUI 从图形会话启动时需保留 `DISPLAY` 等环境变量。

## 配置说明

- `官方 8021x.exe`：留空使用发行包内置参考文件，也可填写自定义路径。
- `客户端版本`：填写对应 `8021x.exe` 的文件版本号，可在 Windows 文件属性中查看。
- `DHCP 模式`：
  - `0`：不使用 DHCP。
  - `1`：二次认证时执行 DHCP。
  - `2`：认证成功后执行 DHCP。
  - `3`：认证前执行 DHCP。
- JSON 中的 `dhcp_script` 留空表示使用当前平台默认 DHCP 命令；`interface_mac` 可用于跨系统匹配同一网卡。旧 JSON 中的平台专用内置参考文件路径也会解析到当前发行包。

## 运行注意事项

- Windows 启动时会请求管理员权限，连接前需要安装 `Npcap`。
- Linux 需要 root 权限、`libpcap` 和 `iproute2`；默认 DHCP 模式还需要 `dhclient`。GUI 需要图形运行库且没有托盘功能；CLI 无需图形界面，收到终止信号时会尽力发送 Logoff。
- 官方 `Ruijie Supplicant\8021x.exe` 仅作为兼容性参考文件。
- 发布 `--onedir` 版本时，请分发对应的整个 GUI 或 CLI 目录。
- 建议在目标架构的干净系统中验证发布包启动，并在真实网络环境中验证认证。
- 像 `hlaccount.json`、`.venv/` 和 `.build-venv/` 这样的本地文件不应提交到仓库。
