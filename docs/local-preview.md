# 本地会话规则与无硬件回放

实现位于 `study_dino/session.py`；使用 Python 标准库，无额外依赖。它处理的是两条流程的**确定性软件规则**，不是视觉分类器、平台 API 或设备驱动。

## 可以验证什么

1. 立约进入学习状态；三类候选可见状态分别处理，并保留 unknown。
2. 持续候选事件先发起询问，合理解释不触发动作；当前保守版本需要明确的 `distracted` 回答才提出反馈意图，不等于最终自动监测方案已经完成。
3. 休息、暂停、明确复归共享同一份任务和提醒模式；暂停会撤掉安全就绪状态，不自动重新武装执行器。
4. 动作独立同意、设备离线、安全未就绪、硬停用、重复事件和未知回执的处理。
5. 输出只表示意图/设备报告，不能把发送成功或输出结束当作实际水花和震动证据。

## 运行

在项目根目录使用 Python 3.11：

```powershell
py -3.11 -m unittest discover -s tests -v
py -3.11 -m study_dino examples/session-preview.jsonl
```

回放每一行都标记 `evidence=local_simulation`、`hardware_executed=false`。示例中的设备就绪和输出结束也是人工测试数据，不代表连接过真实板卡。

本机已执行全部单元测试并保存日志；CI 同时运行这些测试。单元测试数量/通过率不是模型识别准确率，也不是比赛端到端验收。

## 本地测试事件（不是平台协议）

格式：`event_id`（唯一字符串）、`at`（从测试会话开始的单调秒数）、`kind`、`data`。

| kind | data 要点 | 意义 |
|---|---|---|
| start | task, mode；动作模式需要明确同意字段 | 开始约定；mode 为 voice/vibrate/splash |
| observe | posture, confidence | 人工或未来适配器提供的候选分类，不在此进行识别 |
| checkin | answer=legitimate/distracted/break | 已理解意图的枚举；原始自然语言理解由平台负责 |
| break / pause / resume / end | 无 | 休息、暂停、显式复归和结束 |
| revoke | 无 | 撤销执行器同意并请求停止 |
| device | online、vibration_ready、water_ready、emergency_stop | **示例仅模拟**；实际接入时须由受信任适配器提供，不能相信模型/粘贴文本自行武装 |
| receipt | request_id, state=output_finished/failed | 关联设备报告，不是物理效果证明 |
| timeout | request_id | 结果未知、撤掉就绪、不自动重发 |

示例的持续5秒、冷却30秒和置信0.8只用于测试规则路径，**不是经过校准的视觉阈值，也不是执行器运行时长**。实际阈值和驱动上限须后续验证。

## 接入边界

- 不包含摄像头、麦克风、串口或网络访问；无法真的震动、喷水或建立云端 Agent。
- 不定义未经平台核验的 HTTP/MQTT 接口。待真实平台能力确定后，才将平台事件映射到本地意图，或将等价规则配置到工作流。
- 设备驱动仍需独立校验目标、上限、硬停用和供电状态；软件就绪字段不能替代物理检查。
- 本地回放不能完成指定 SPI 摄像头、三类真实识别、真实平台能力调用或硬件闭环的比赛验收。
