# BF3901第一张真实图像：诊断与复现

2026-10-31，用户明确要求启动测试拍照后，已在唯一匹配的COM3设备上完成一次相机诊断APP更新和真实单帧采集。**不是内置bus.jpg，不是电脑自带摄像头，不是生成图片。**

## 已验证

- 目标ESP32-S3、16MB Flash及设备标识匹配；写前备份了原应用、实际分区表和OTA数据。
- 原应用前3,118,544字节哈希与25cb基线归档匹配；OTA有效条目seq1/state2，活动ota0为0x20000。
- 独立25cb诊断源码：关闭POSE固定图示例，启用CAMERA；启动只跑相机，不初始化原网络/音频或执行器业务。
- 候选706,288字节，SHA-256 `baf7d916b3e12c8d7aa459d5a41fc3f1d49109551dad4709622baa291ab3b51a`；生成分区表与设备备份对应字节一致。
- 仅写0x20000应用，esptool返回Hash of data verified。没有执行erase_flash，没有烧写bootloader/分区表/OTA数据/NVS/模型分区。
- 先开始接收，再一次普通RTS复位，捕获226,262字节；串口已关闭。
- 驱动识别BF3901 PID=0x3901，实际格式240×320、UYVY（0x59565955）。
- 实际帧153,600字节，结束标记、长度与FNV-1a `89e71072`通过；PC离线解码为PNG。
- 采集后CAMDIAG_STOP，程序已关流。

## 当前限制

图像可辨强光源，明显过曝/偏色；光照、镜头朝向、保护膜、曝光/白平衡与像素解码仍需正常目标图复核。只证明本次基本采集链路成功，不代表全部电气接法、长时间稳定性、画质或推理已经验收。

**设备目前运行临时相机专用诊断版 `25cb-camera-diag1`，不是原联网/语音基线，也不是最终监督程序。** 该程序每次启动尝试一帧，传输完成后停流；不以诊断期间未连云判断故障。原配网分区未被本次烧录覆盖，旧应用备份保存在本机忽略目录，可以按明确恢复操作回退。

未运行真实帧YOLO，未打开水路。该次接线视频未能全部目视核准，用户知风险明确要求启动；不得倒写成启动前已经人工确认所有针脚。

## 原始证据（本机私有，不入Git）

- 原始串口：`logs/camera-diagnostic-capture-20261031-170906.bin`。
- 原图、原始YUV和校验元数据：`artifacts/camera-first-photo-20261031/`。
- 写前备份：`.local/backups/camera-pretest-20261031-164726/`。
- 编译、候选与设备结果：`artifacts/camera-diagnostic-*.json`及相应logs。

原图不上传公开仓库；对话中展示的是实际采集原图。

## 编译复现（不自动烧录）

SDK基线为25cb6e5120b37282a01d048883ccc85b6c1350ed。保持原参考目录只读；新建独立worktree `.local/camera-diagnostic-sdk`，应用 `patches/0001-camera-diagnostic.patch`（零上下文补丁，`git apply --unidiff-zero`），然后运行 `scripts/build-camera-diagnostic.cmd`。SDK所需独立工具链沿用本项目安装结果。

产物位于 `artifacts/camera-diagnostic-build/`。包装脚本保持ASCII路径；生成Ninja/response文件由normalize_build_paths处理，最终app编译对象使用response文件避免Windows命令行过长。首次冷构建需要编译SDK组件，后续增量构建可复用，不应为一次修改重复全量清理。

解码工具为 `scripts/camera_frame_decode.py`，先验证长度/FNV和帧结束再接受图像。转换图像需已有OpenCV/NumPy；本机使用现有环境读取，没有往科研环境新装依赖。单帧通过115200串口传输，只用于诊断，不是实时视频方案。

## 下一步

将镜头固定朝正常光照下的书本或桌面，避开灯具，不动杜邦线，再拍一张验证画质与方向；通过后再开发持续采集、实时YOLO与语音/网络并发。物理喷水仍保持未实现/未启用。
