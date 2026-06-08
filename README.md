# GCP Manager v7.2

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green.svg)](https://pypi.org/project/PyQt6/)

GCP Manager 是一个 Windows 桌面端的 Google Cloud Platform 批量实例管理工具，基于 PyQt6 开发，面向需要批量导入账号、批量创建/管理 VM、配置防火墙、查看哪吒监控状态、远程执行 SSH 命令的使用场景。

当前仓库已从旧版 v3.4 升级到 v7.2，本版本重点增强了创建后自动执行命令、代理兼容、SSH 稳定性、中文编码、图标打包以及默认禁用 Google Cloud Ops Agent 自动安装等功能。

## 主要功能

### 账号管理

- 支持导入 GCP 服务账号 JSON 密钥。
- 支持保存账号邮箱、项目 ID、JSON 路径、代理配置等信息。
- 支持账号列表搜索、勾选、多账号批量操作。
- 支持删除选中账号。
- 支持拖拽/选择 JSON 文件导入。
- 使用本地 SQLite 数据库保存账号数据。

### 代理支持

支持为账号配置代理访问 Google Cloud API，适合不同网络环境。

支持格式包括：

```text
IP:PORT
IP:PORT:USER:PASS
http:IP:PORT
https:IP:PORT
socks:IP:PORT
socks5:IP:PORT
http:IP:PORT:USER:PASS
https:IP:PORT:USER:PASS
socks:IP:PORT:USER:PASS
socks5:IP:PORT:USER:PASS
http://USER:PASS@IP:PORT
https://USER:PASS@IP:PORT
socks://USER:PASS@IP:PORT
socks5://USER:PASS@IP:PORT
```

说明：

- HTTP/HTTPS 代理依赖 `requests` 原生支持。
- SOCKS/SOCKS5 代理需要安装 `PySocks`。
- 程序启动时会检测 SOCKS5 依赖是否可用。

### 批量创建实例

- 支持按账号批量创建 Google Compute Engine VM。
- 支持选择区域和创建数量。
- 支持免费区/付费区模式。
- 支持多线程并发执行创建任务。
- 支持创建后自动刷新实例列表。
- 默认系统镜像为 Ubuntu Minimal 22.04 LTS。
- 默认机器类型、磁盘大小等参数在代码常量中维护。
- 创建实例时默认禁用 Google Cloud Ops Agent 自动安装，避免控制台默认开启 Ops Agent 导致额外组件安装。

### 登录模式

创建实例时支持两种登录方式。

#### SSH 密钥模式

- 选择本地 SSH 公钥文件。
- 创建实例时写入 SSH 公钥元数据。
- 适合使用私钥登录服务器的场景。
- 创建后命令执行模式下，程序会尝试使用系统 SSH key 或 ssh-agent 进行认证。

#### Root 密码模式

- 支持用户自定义 Root 密码。
- 支持自动随机生成 Root 密码。
- 创建实例时通过 startup-script 自动：
  - 设置 Root 密码。
  - 解锁 Root 账号。
  - 开启 SSH 密码认证。
  - 允许 Root SSH 登录。
  - 重启 SSH 服务。
- Root 密码会在实例列表/日志中显示，便于复制和后续连接。

### 创建后自动执行命令

v7.2 增加了创建完成后自动执行 SSH 命令的流程。

适合场景：

- 创建 VM 后自动安装环境。
- 自动部署脚本。
- 自动执行初始化命令。
- 自动配置业务服务。

特性：

- 创建实例成功后等待 SSH 端口可用。
- 等待 SSH 认证可用后再执行命令。
- 支持多台实例并发执行。
- 支持输出日志实时回显。
- 支持空闲超时和总超时控制。
- 支持手动停止执行。

依赖：

```bash
pip install paramiko
```

如果未安装 `paramiko`，普通创建仍可使用，但创建后自动执行命令不可用。

### 普通 SSH 命令执行

对已有实例也可以执行命令。

- 在实例列表中选择目标实例。
- 切换到普通执行模式。
- 输入命令后执行。
- 支持多实例并发执行。
- 支持 Shift + Enter 换行。
- 支持 Enter 快速执行。
- 支持日志输出和执行结果列显示。
- 支持 TCP Keepalive，降低长命令被 NAT/防火墙断开的概率。
- 支持命令空闲超时和总超时保护。

### 实例列表管理

- 展示实例名称、IP、可用性、哪吒监控名称、Root 密码、执行结果等信息。
- 支持刷新实例列表。
- 支持按账号/项目获取实例。
- 支持双击复制常用字段，例如 IP、Root 密码等。
- 支持记录创建后的 Root 密码缓存。
- 支持记录创建后命令执行结果。

### 防火墙配置

- 支持对选中账号一键配置全开放防火墙规则。
- 支持入站/出站规则处理。
- 适合批量初始化测试项目网络环境。

注意：全开放防火墙会放开较大网络访问范围，仅建议在明确知道风险的场景使用。

### 哪吒监控面板集成

- 支持填写哪吒面板地址。
- 支持填写 Token。
- 支持保存配置到本地。
- 支持测试连接。
- 支持刷新服务器列表。
- 支持根据实例 IP 匹配哪吒监控名称。

本地配置保存位置：

```text
%APPDATA%\XiaoLong\nezha_config.json
```

发布包不会内置个人面板地址或 Token。请在本机运行后自行填写。

### 日志系统

- 程序底部提供实时日志窗口。
- 创建、刷新、防火墙、SSH 执行、哪吒刷新等操作都会输出日志。
- 便于判断每个账号、实例、命令的执行状态。

### UI 与打包

- PyQt6 桌面界面。
- Windows 任务栏/窗口图标已更新。
- PyInstaller 多文件模式打包。
- `console=False`，运行时不显示控制台黑框。
- 运行时资源通过 `resource_path()` 兼容源码运行和 PyInstaller 打包运行。

## v7.2 更新内容

相比旧版 v3.4，本版本主要变化：

- 主程序升级为 `GCP_Manager_v7.2.py`。
- 新增创建后自动执行命令能力。
- 增强 SSH 命令执行稳定性。
- 增强代理格式解析。
- 默认禁用 Ops Agent 自动安装。
- 修复中文字符串/注释编码显示异常。
- 更新程序图标和 PyInstaller spec。
- 清理发布包中的本地面板地址、Token 等个人配置。
- README 已按 v7.2 功能重新整理。

## 下载使用

推荐直接下载 Release 中的 Windows 多文件包：

- [GCP Manager v7.2 Release](https://github.com/shenping1200/GCP-Manager-V3.4/releases/tag/v7.2)

下载后解压，运行：

```text
GCP_Manager_v7.2\GCP_Manager_v7.2.exe
```

不要只单独复制 exe，当前发布包是多文件模式，exe 需要和 `_internal` 目录放在一起运行。

## 从源码运行

### 环境要求

- Windows 10/11
- Python 3.13 或兼容版本
- 可访问 Google Cloud API 的网络环境

### 安装依赖

```bash
pip install PyQt6 requests google-cloud-compute google-api-core paramiko PySocks
```

说明：

- `paramiko` 用于 SSH 命令执行和创建后自动执行命令。
- `PySocks` 用于 SOCKS/SOCKS5 代理。
- 如果不使用 SOCKS5 或 SSH 命令执行，可按需减少依赖。

### 启动源码版

```bash
python GCP_Manager_v7.2.py
```

## 打包说明

仓库包含 PyInstaller 配置：

```text
GCP_Manager_v7.2.spec
```

执行：

```bash
python -m PyInstaller --noconfirm --clean GCP_Manager_v7.2.spec
```

输出目录：

```text
dist\GCP_Manager_v7.2\
```

运行文件：

```text
dist\GCP_Manager_v7.2\GCP_Manager_v7.2.exe
```

## 快速开始

### 1. 准备 GCP 服务账号

1. 登录 Google Cloud Console。
2. 创建或选择项目。
3. 创建服务账号。
4. 为服务账号授予 Compute Engine 相关权限，例如 Compute Instance Admin。
5. 下载服务账号 JSON 密钥。

### 2. 导入账号

1. 打开程序。
2. 在账号管理区域添加或导入账号。
3. 填写账号邮箱、项目 ID、JSON 文件路径。
4. 如有需要，填写代理。
5. 勾选需要参与操作的账号。

### 3. 配置创建参数

1. 选择免费区或付费区。
2. 选择具体区域。
3. 设置创建数量。
4. 选择登录模式：
   - SSH 密钥模式：选择公钥文件。
   - Root 密码模式：填写自定义密码或使用随机密码。
5. 如需创建后执行命令，切换到创建后执行模式并输入命令。

### 4. 开始创建

点击创建按钮后，程序会：

1. 按选中账号批量创建实例。
2. 自动应用登录配置和启动脚本。
3. 默认阻止 Ops Agent 自动安装。
4. 等待实例创建完成。
5. 如启用创建后命令，等待 SSH 可用后执行命令。
6. 刷新实例列表并输出日志。

### 5. 管理实例

可在实例列表中：

- 查看实例 IP。
- 查看哪吒监控名称。
- 查看 Root 密码。
- 查看命令执行结果。
- 刷新实例列表。
- 选择实例执行命令。

## 哪吒监控使用

1. 在实例列表区域填写面板地址。
2. 填写 Token。
3. 点击保存。
4. 点击测试确认连接正常。
5. 点击刷新获取服务器列表。
6. 程序会根据实例公网 IP 匹配哪吒中的服务器名称。

Token 支持直接填写 JWT，也支持从 `nz-jwt=...` Cookie 中提取。

## 本地数据与隐私说明

程序会在本机保存必要运行数据：

```text
accounts.db
%APPDATA%\XiaoLong\nezha_config.json
%APPDATA%\XiaoLong\GCP_Manager_v6.9.ini
```

说明：

- `accounts.db` 是本地账号数据库，不应上传到 GitHub。
- `nezha_config.json` 保存本机哪吒面板地址和 Token，不应上传或打包进公开发布包。
- 发布前请确认仓库和 dist 中不包含个人 Token、面板地址、服务账号密钥等敏感信息。

## 安全提醒

- 服务账号 JSON 密钥具有较高权限，请妥善保管。
- 不要把 JSON 密钥、Token、数据库文件提交到公开仓库。
- Root 密码模式会开启 Root SSH 登录，请只在可控环境使用。
- 全开放防火墙风险较高，请谨慎使用。
- 批量创建实例可能产生云资源费用，请确认配额和计费状态。

## 常见问题

### 运行时没有界面或闪退

优先从命令行运行源码版查看错误：

```bash
python GCP_Manager_v7.2.py
```

检查依赖是否安装完整。

### SOCKS5 代理不可用

安装 PySocks：

```bash
pip install PySocks
```

### 创建后命令不执行

检查：

- 是否安装 `paramiko`。
- 实例安全组/防火墙是否允许 22 端口。
- Root 密码或 SSH key 是否可用。
- startup-script 是否已完成。
- 日志中是否出现 SSH 端口未就绪或认证失败。

### 哪吒面板匹配不到实例

检查：

- 面板地址是否正确。
- Token 是否有效。
- 哪吒服务器列表中的公网 IP 是否与 GCP 实例公网 IP 一致。
- 点击测试和刷新查看日志。

## 许可证

本项目使用 MIT License，详见 [LICENSE](LICENSE)。

## v7.4 更新说明

在 v7.3 的基础上继续增量更新，保留 v7.2/v7.3 的全部能力，并增加以下默认创建行为：

- 默认开放 HTTP 流量：创建实例时自动添加 `http-server` 网络标签。
- 默认开放 HTTPS 流量：创建实例时自动添加 `https-server` 网络标签。
- 创建实例初期自动配置全开放防火墙规则：
  - `allow-all-ingress`：入站 `0.0.0.0/0` 全协议放行。
  - `allow-all-egress`：出站 `0.0.0.0/0` 全协议放行。
  - 如果规则已存在，会按全开放规则更新。
- 保留 v7.3 的数据保护无备份设置：启动盘不绑定快照时间表或备份资源策略。
- 保留 v7.2 的 Ops Agent 禁用设置，避免默认安装可观测性 Agent。

### v7.4 使用提醒

v7.4 会在创建实例时自动放开网络访问。该行为方便快速部署和测试，但会扩大实例公网暴露面。请确认实例内服务、SSH 密码、密钥和系统安全配置满足你的使用场景。

## v7.6 更新说明

v7.6 在 v7.4 的默认创建策略基础上，新增面向 AI 和自动化工具的本地任务接口，重点解决“导入账号后自动创建实例、自动执行安装命令、自动反馈结果”的批量流程。

### 核心能力

- 本地 API 服务：程序启动后在 `127.0.0.1:18765` 提供 HTTP JSON 接口，只允许本机访问。
- 自动任务模板：可以先设置 Root 密码、安装命令、验证命令、并发数、重试次数等参数。
- 新账号监听：程序每 3 秒检测本地账号库，发现新导入的 JSON 账号后自动加入任务队列。
- 任务队列：支持陆续导入账号，也支持一次性导入多个账号。
- 高并发后台执行：创建实例、等待 SSH、执行命令、验证结果全部放到后台 worker，不阻塞 GUI。
- 并发上限优化：`max_workers` 最高支持 `20`，适合多账号批量处理。
- 结果报告：可通过接口查看每个账号、每台实例的执行状态和失败原因。

### 自动任务流程

1. 打开 `GCP_Manager_v7.6.exe`。
2. 通过本地 API 设置自动任务模板。
3. 在软件中导入新的 GCP 服务账号 JSON。
4. 程序检测到新增账号后自动创建实例。
5. 实例创建成功后等待 SSH 就绪。
6. 执行预设安装命令。
7. 可选执行验证命令。
8. 通过任务报告接口查看最终结果。

### API 接口

基础地址：

```text
http://127.0.0.1:18765
```

常用接口：

- `GET /api/status`：查看程序版本、账号数量、实例数量和最近任务。
- `GET /api/accounts`：查看已导入账号列表，不返回 JSON 密钥内容。
- `GET /api/logs?since=0&limit=200`：读取程序日志。
- `GET /api/tasks`：读取最近任务状态。
- `GET /api/task_report`：读取任务汇总报告。
- `GET /api/automation`：查看自动任务配置和队列状态。
- `POST /api/automation`：设置自动任务模板。
- `POST /api/automation/stop`：停止自动任务监听并清空待处理队列。
- `POST /api/automation/run_existing`：对当前已导入账号手动加入任务队列。

### 设置自动任务示例

```powershell
$body = @{
  enabled = $true
  max_workers = 20
  count = 1
  use_free_regions = $true
  root_password = "你的Root密码"
  post_command = "你的安装命令"
  verify_command = "docker ps"
  retry_count = 2
  command_timeout = 1800
  ssh_timeout = 300
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:18765/api/automation" `
  -ContentType "application/json" `
  -Body $body
```

设置完成后，只要继续导入新的 JSON 账号，程序就会自动按该模板执行。

### 一次性处理已有账号

如果账号已经导入，可以设置 `run_existing = $true`，或单独调用：

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:18765/api/automation/run_existing" `
  -ContentType "application/json" `
  -Body "{}"
```

### 并发说明

- `max_workers` 控制同时处理的账号任务数，最高 `20`。
- 每个账号任务独立执行，互不影响。
- 创建失败、SSH 未就绪、命令失败都会记录到任务结果中。
- 建议根据本机网络、GCP API 配额和账号数量设置合理并发。
- 20 并发适合快速批量处理，但如果遇到 GCP 限流或资源不足，可降低并发后重试。

### 安全说明

- API 只绑定 `127.0.0.1`，不对外网开放。
- `/api/accounts` 不返回服务账号 JSON 密钥内容。
- 自动任务会按照你设置的 Root 密码和安装命令执行，请确认命令来源可信。
- 全开放防火墙适合快速部署场景，但会扩大公网暴露面，请自行评估风险。
- 不要把 Root 密码、Token、服务账号 JSON、`accounts.db` 上传到公开仓库。

### v7.6 发布包

发布页提供 `GCP_Manager_v7.6.zip`，解压后运行：

```text
GCP_Manager_v7.6\GCP_Manager_v7.6.exe
```

该版本仍为多文件模式，不需要打包成单文件 exe。
