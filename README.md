# Bluetooth Radar

An enhanced Bluetooth device scanner and radar visualization tool using Python.

## Features

- Real-time polar radar chart showing nearby Bluetooth devices
- Distance estimation based on RSSI
- Device history trail visualization
- Matplotlib interactive GUI with sliders (min RSSI, max distance, scan interval)
- Two versions:
  - AI version: sends device data to local LLM (Ollama llama3.1:8b) for analysis
  - No-AI version: pure visualization without AI

## Requirements

```text
Python 3.8+
pip install asyncio matplotlib bleak requests
# For AI version also need:
# Ollama running locally with llama3.1:8b model (or Any Large Language Model)
# tkinter (usually comes with Python)
```

## Usage

1. Make sure Bluetooth is enabled on your computer
2. Run the desired version:

``` bash
python bluetooth_radar_AI_version.py
# or
python bluetooth_radar_No_AI.py
```
3. Use sliders to adjust:
    - Min RSSI filter
    - Max detection distance
    - Scan interval

Click Pause button → AI version will send current devices to local LLM and show analysis

## Screenshots
(之後你可以把執行畫面截圖上傳到仓库，再用 screenshot 加入)

## Notes
- Distance is estimated using free-space path loss model (very approximate!)
- Log file bluetooth_radar.log is created for debugging
- AI feature requires Ollama server running at http://localhost:11434

## License
MIT License
