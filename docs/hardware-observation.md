# 首次串口观察

2026-10-31：系统识别 USB-Enhanced-SERIAL CH343 为 COM3，VID:PID 1A86:55D3，状态 OK。以 115200 8N1、禁用软件和硬件流控，打开前设置 DTR/RTS 为 false，监听约35秒；未发送字节、未主动复位或刷写，捕获0字节并已关闭端口。驱动打开时仍可能出现控制线瞬态，不能保证设备未复位。没有启动日志不能判断设备固件或云连接状态；端口/波特率和固件启动行为尚待核实。原始文件保存在忽略的 logs 目录。

## 一次普通复位后的启动观察
2026-10-31：用户授权后，在唯一匹配的 CH343 COM3 上打开监听，DTR 保持 false，按本机 esptool HardReset 普通串口策略令 RTS true 0.1 秒再 false 一次，随后监听约50秒并关闭。未发送串口字节、未主动进入下载模式、未擦写；原始日志仅存忽略目录。启动日志报告 ESP32-S3 启动组件、16 MB SPI Flash、8 MB PSRAM，应用名 vb701n、版本 25cb6e51；所见 MAC 与用户交接一致。日志出现 MQTT connect success、cloud connected 和 NTP synced；仅说明该次日志记录的连接状态，不证明 Agent、语音或外设功能已验证。未见 DOWNLOAD、panic 或 error 字样。此前拔插后的69字节为 MQTT 心跳类输出，不是启动日志。

## 当前实际联网方式
同一已保存捕获可见 `wifi:mode : sta`、`wifi:state: assoc -> run`、`wifi got ip` 与 `esp_netif_handlers: sta ip`，随后MQTT连接成功。已隐藏SSID、IP与MAC。故可确认当前COM3设备在该次启动中通过Wi-Fi站点方式联网，不是只能依赖蓝牙中转。源码保留BLE配网，不能把支持Wi-Fi等同于“没有蓝牙”；商品/套件是否被厂商称为“蓝牙版”仍应看实物标签。
