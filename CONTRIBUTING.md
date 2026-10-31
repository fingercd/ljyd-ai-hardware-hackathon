# 团队协作

## 工作方式

1. 开始前查看 `git status --short`，更新 main 只用 `git pull --ff-only`；存在分叉先比较，不盲目覆盖。
2. 新功能开短期分支，例如 `feat/voice-agent`、`fix/serial-logging`、`docs/demo-guide`。一个 PR 解决一件事，说明测试和未覆盖范围。
3. 代码、文档和必要配置随功能一起小粒度提交。示例：`build: add isolated Windows SDK setup`、`docs: document first board bring-up`。
4. 提交前运行公开内容检查及 `git diff --check`；固件改动还需编译，行为改动补实板测试或标明未验证。
5. 每个成员保留本人作者身份。助手替维护者提交时使用 fingercd 的已核验身份，不伪造队友署名。
6. 合并前 review diff，main 保持可用；发布演示里程碑再打新的 annotated tag，不覆盖已共享版本。

## SDK 是受控依赖

`ljyd-sdk/` 是显式 submodule，固定厂商 commit。获取时使用 `git clone --recurse-submodules`，已有 checkout 使用 `git submodule update --init --recursive`。

不要把 SDK 的未提交修改当作已经保存在主仓库里，也不要提交一个其他成员无法从远端获取的新 gitlink。需要改 SDK 时，先讨论将改动作为可审查补丁还是放到可访问的团队开发远端；不复制整套第三方代码，不擅自改许可证。

## 公开前检查

```powershell
py -3.11 scripts/check_public_tree.py
git diff --check
git diff --cached --stat
git diff --cached
```

检查器只提供有限的路径与常见凭据模式检查，不替代人工审查、GitHub 的安全扫描或凭据轮换。

禁止提交真实产品密钥、Wi-Fi 密码、设备证书、NVS/Flash dump、原始串口日志、用户语音/图像和未获转载许可的赛事资料。使用忽略的 `.local/` 保存本机配置；分享 `.example` 或脱敏说明。

## PR 中说明

- 为什么修改，用户会看到什么变化。
- 编译/脚本检查结果；使用的板型与固件版本。
- 真机验证做了什么、没有做什么。
- 是否影响引脚、供电、分区、产品身份或已有配网数据。
- 回退方法，以及需要同步更新的文档。

高影响操作（整片擦除、解绑重置、eFuse、永久安全配置、公共历史改写）不能从一次普通代码 review 推导授权。
