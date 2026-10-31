# 开发约定的依据与取舍

本项目在 2026-10-31 按用户要求，由 **1 个 Sol 与 5 个 Luna** 分别研究开发规划、Git、Windows 环境、设备安全、Agent 测试和外设集成，再由主助手结合本机真实状态整理。下列是工程依据和项目选择，不表示平台或实物功能已验证。

原始研究笔记保留在本机 `docs/research/`；公开版只保留适用结论、来源和边界。项目执行规则以 [AGENTS.md](../AGENTS.md) 为准。

## 采纳的原则

| 原则 | 为什么适用于本项目 | 主要一手依据 |
|---|---|---|
| 编译、刷写、启动、功能分别验收 | 没有实板时也能准备环境，但不能声称设备已工作 | [ESP-IDF 5.4.1 入门](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/get-started/windows-start-project.html) |
| 固定 SDK 与工具版本 | 不同时升级框架、换板配置和改业务，便于定位问题 | [构建系统](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/api-guides/build-system.html) |
| 实际配置与 defaults 分开看 | 已有 sdkconfig 不会因修改 defaults 自动全部覆盖 | [自定义默认配置](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/api-guides/build-system.html#custom-sdkconfig-defaults) |
| 保留匹配的构建与调试材料 | 只有应用 bin 或 tag 不足以恢复、诊断全部镜像 | [镜像描述与 ELF 哈希](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/api-reference/system/app_image_format.html#application-description) |
| Windows 环境保持局部与可核验 | 项目含中文路径，不能以安装完代替实际构建成功 | [5.4.1 Windows 路径限制](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/get-started/windows-setup.html) |
| SDK 作为明确的固定依赖 | 让队友获取同一基线，不把第三方整树复制进新历史 | [Git submodule](https://git-scm.com/docs/gitsubmodules) |
| 不公开密钥、原始日志和备份 | 忽略当前文件不等于历史没有泄露，泄露后需要轮换 | [GitHub secrets](https://docs.github.com/en/get-started/learning-to-code/storing-your-secrets-safely)、[敏感历史处理](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) |
| 刷前确认身份、容量和写入范围 | 串口可能复位，分区/镜像/加密状态会限制恢复 | [esptool 基本命令](https://docs.espressif.com/projects/esptool/en/release-v4/esp32s3/esptool/basic-commands.html)、[启动模式](https://docs.espressif.com/projects/esptool/en/release-v4/esp32s3/advanced-topics/boot-mode-selection.html) |
| 永久安全配置单独授权 | eFuse 和安全启动并不是普通上手必需步骤 | [ESP32-S3 eFuse](https://docs.espressif.com/projects/esp-idf/en/v5.4.1/esp32s3/api-reference/system/efuse.html) |
| 物理动作成功需要设备结果 | MQTT 连接/发送/代理确认与真实执行是不同层次 | [ESP-MQTT 事件](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-reference/protocols/mqtt.html)、[MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html) |
| 提示词不是设备权限系统 | 网页、检索文档及模型输出不能越过工具授权边界 | [OWASP 提示注入防护](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) |
| 外设一次一个，按板级资料核对 | 同芯片不等于同引脚；I2C 电平、上拉和启动引脚需要明确 | [ESP32-S3 硬件检查表](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)、[I2C](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/api-reference/peripherals/i2c.html) |

MPU6050 的芯片供电/逻辑电平必须与具体模块原理图区分，不能因模块上有稳压器就推断所有信号兼容。相关芯片来源：[TDK 产品规格](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet.pdf)、[TDK 寄存器手册](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf)。它们是芯片资料，不能替代用户手上模块版本确认。

## 没有一律强制的事项

- 不要求每次小改动都读出整片 Flash；按本次写入范围、原状保留需求和读取限制决定。
- 不强制初期训练自己的模型、实现 OTA、引入完整后端/消息中台或复杂幂等系统。
- 不把主机 mock、CI 绿灯、网页预览或“设备在线”当作完整实板验收。
- 不以公开仓库为由公开赛事全文、账户截图、个人语音/图像或未知许可证素材。
- 不把公开仓库等同于已声明统一开源许可。第三方组件各自许可不变，新增内容的统一许可尚未确定。

## README 的组织参考

阅读公开项目时只借鉴信息顺序，不复制文案/美术、不移植对方的获奖和完成状态：

- [G-Exo](https://github.com/Lain-Ego0/G-Exo)：真实演示入口、状态与证据靠前。
- [ExtendAble](https://github.com/nathanqiuUCSB/ExtendAble)：清楚交代交互方式、实现限制和技术栈。
- [Kritrim](https://github.com/Baksheeshs/ourobonics-kritrim_SIH_2025_Winner)：硬件、架构、Quickstart 与团队分开组织。

本项目采用简洁首屏、少量状态徽章、目标链路图、可执行入口和团队链接。尚未有实物演示时直接写明，不用占位视频冒充成果。

AGENTS.md 的位置与用途参考 [OpenAI 官方项目指引说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。本文件是规则的解释与来源索引，不会自动增加用户未授权的设备或账户操作。
