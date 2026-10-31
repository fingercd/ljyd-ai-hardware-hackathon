# 环境与构建

## 固定版本

| 项目 | 基线 |
|---|---|
| 厂商 SDK | `8cdf7cb11d92720fd8054b19bdf72d7a7c27a7f6` |
| ESP-IDF | 5.4.1，随厂商源码内置 |
| 本机基础 Python | 3.11.15 |
| Xtensa GCC | 14.2.0 / esp-14.2.0_20241119 |
| CMake / Ninja | 3.30.2 / 1.12.1 |

开发脚本使用 SDK 对应的工具版本，不调用 PATH 中其他 CMake 或另装的 latest IDF。激活本机 SDK 环境时设置真实的 VIRTUAL_ENV 标记，避免 CMD AutoRun 误激活科研 Conda；不修改注册表或全局 Conda 配置。依赖安装使用厂商内置的 `tools.json` 和 Espressif v5.4 约束；Python 包的精确安装清单另在本机验收时保存。

## Windows 入口

```powershell
.\scripts\setup.cmd
.\scripts\build.cmd
.\scripts\ports.cmd
```

setup 安装当前 SDK 的 ESP32-S3 工具并建立项目内 Python 虚拟环境；build 只构建；ports 只列出串口，不打开设备。setup 需要网络并会执行下载的依赖，运行前应审阅脚本和来源。提供这些入口不代表所有机器已验证，实际范围见 [状态](STATUS.md)。

SDK 原始 `dev.bat` 写死作者机器的 Python 3.14 环境目录。本项目不改动它，而用包装入口选择本机独立 Python 3.11 环境；SDK 原始 `build.bat` 会串联烧录/监视，因此不作为无设备编译入口。

## 本机中文目录

维护者指定的真实目录是 `D:\PythonProject\AI硬件`。英文入口 `D:\PythonProject\ljyd-workspace` 为指向它的 NTFS junction，不是源码副本。工具、SDK、日志和资料都留在真实目录下。

若 checkout 是无空格的英文路径，不需要本机覆盖文件。确需覆盖时，创建被忽略的 `.local/environment.cmd`，指定自己的现有英文入口和 Python 可执行文件：

```bat
@echo off
set "LJYD_WORKSPACE=D:\your-ascii-workspace"
set "LJYD_BOOTSTRAP_PYTHON=C:\your-python311\python.exe"
```

不要复制维护者电脑上的用户路径。不要自动修改全局系统语言或科研 Conda。当前 ccache 禁用，是因为它已在真实中文路径上触发异常。`idf.py` 会将联接解析回真实中文路径，另一次尝试在 objcopy 输出处失败；包装入口因此改用显式 CMake ASCII 路径。最终兼容性仍以完整构建结果为准，重新启用缓存前必须实际验证。

## 产物与验证边界

本项目包装入口使用显式 CMake 源目录与输出目录，产物在 `artifacts/build/`。SDK 默认的 `apps/build/` 仅保留早期失败尝试，不能把其中旧产物当作当前验收结果。阶段交付本地保存匹配的应用、bootloader、分区表、ELF、烧录参数和 SHA-256；日常不把二进制放入 Git。

修改 `sdkconfig.defaults` 不会保证覆盖已存在的 `sdkconfig`。改分区、宏或产品身份后检查实际生效配置，不在不明确范围时运行全量清理。构建、刷写、启动和端到端功能分别验收。

官方依据：[Windows 5.4.1 路径与环境限制](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/get-started/windows-setup.html)、[构建系统](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/api-guides/build-system.html)。

## 源码与文档差异

当前锁定源码实际定义 `CONFIG_QM_POSE_SUPPORT=1`、`CONFIG_LJYD_PLAYBACK_SUPPORT=1`，与上游 README 中“默认关闭”的描述不一致。验收和后续裁剪以实际源码及配置为准；当前准备的是未修改厂商基线的构建，不代表已经裁剪成最小语音固件，更不代表已确认运行时 RAM 足够。刷写前必须核对这些功能是否适合本次实物与演示。
