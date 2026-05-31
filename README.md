# GCP Manager v7.2

GCP 批量管理工具，当前仓库已更新到 v7.2。

## 本次更新

- 升级主程序到 `GCP_Manager_v7.2.py`。
- 创建实例流程默认禁用 Google Cloud Ops Agent 自动安装。
- 修复中文字符串/注释编码显示问题。
- 支持无黑框的 PyInstaller 多文件模式打包。
- 更新程序任务栏/窗口图标资源。
- 清理发布包中的本地面板地址、Token 等运行时个人配置。

## 运行源码

```bash
python GCP_Manager_v7.2.py
```

## 打包

```bash
python -m PyInstaller --noconfirm --clean GCP_Manager_v7.2.spec
```

打包结果位于：

```text
dist/GCP_Manager_v7.2/GCP_Manager_v7.2.exe
```

## 配置说明

程序运行时会在用户目录下保存本地配置，例如：

```text
%APPDATA%/XiaoLong/nezha_config.json
%APPDATA%/XiaoLong/GCP_Manager_v6.9.ini
```

这些运行时配置不应提交到仓库或发布包。
