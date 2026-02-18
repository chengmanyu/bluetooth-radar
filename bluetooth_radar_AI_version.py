# pip install asyncio matplotlib bleak requests tk
import asyncio
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import numpy as np
from datetime import datetime
import json
import time
import logging
from bleak import BleakScanner
import requests
import tkinter as tk
from tkinter import messagebox

# Setup logging
logging.basicConfig(
    filename='bluetooth_radar.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'  # Explicitly set UTF-8 encoding
)

class EnhancedBluetoothRadar:
    def __init__(self, max_distance=5.0, scan_interval=1.0):
        self.current_devices = {}
        self.device_history = {}
        self.lock = threading.Lock()
        self.max_distance = max_distance  
        self.scan_interval = scan_interval  
        self.fig = plt.figure(figsize=(16, 10))
        self.ax_radar = self.fig.add_subplot(121, projection='polar')
        self.ax_table = self.fig.add_subplot(122)
        self.stop_animation = False
        self.min_rssi = -100
        self.max_history = 20
        self.paused = False
        self.first_pause = True
        self.ai_response = ""
        # Initialize tkinter root (hidden)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main tkinter window

        # Setup control axes
        self.ax_pause = plt.axes([0.1, 0.02, 0.1, 0.04])
        self.ax_rssi = plt.axes([0.25, 0.02, 0.65, 0.03])
        self.ax_distance = plt.axes([0.1, 0.06, 0.15, 0.03])
        self.ax_interval = plt.axes([0.1, 0.1, 0.15, 0.03])
        self.ax_ai_response = plt.axes([0.3, 0.06, 0.6, 0.08])

    async def scan_bluetooth_devices(self):
        """Scan for nearby Bluetooth devices with batching."""
        try:
            devices = await BleakScanner.discover(timeout=2.0)
            current = {}
            timestamp = time.time()
            
            for device in devices:
                rssi = device.rssi if device.rssi is not None else -100
                if rssi >= self.min_rssi:
                    distance = self.rssi_to_distance(rssi)
                    if 0 < distance <= self.max_distance:
                        current[device.address] = (device.name or "Unknown", rssi, distance, timestamp)
                        if device.address not in self.device_history:
                            self.device_history[device.address] = []
                        self.device_history[device.address].append((rssi, distance, timestamp))
                        self.device_history[device.address] = self.device_history[device.address][-self.max_history:]
            
            with self.lock:
                self.current_devices = current
        except Exception as e:
            logging.error(f"Scan error: {e}")
            print(f"Scan error: {e}")

    def rssi_to_distance(self, rssi):
        """Estimate distance from RSSI, capped at max_distance."""
        if rssi >= 0:
            return -1
        tx_power = -69
        n = 2.0
        distance = 10 ** ((tx_power - rssi) / (10 * n))
        return min(distance, self.max_distance)

    def update_plot(self, frame):
        """Update the radar and table visualization."""
        if self.paused:
            return

        with self.lock:
            self.ax_radar.clear()
            self.ax_table.clear()
            self.ax_ai_response.clear()

            self.ax_radar.set_title(f"Bluetooth Radar - {datetime.now().strftime('%H:%M:%S')}", va='bottom')
            self.ax_radar.set_ylim(0, self.max_distance)
            self.ax_radar.set_xticks(np.linspace(0, 2 * np.pi, 12, endpoint=False))
            self.ax_radar.set_xticklabels([f"{i * 30}°" for i in range(12)])
            self.ax_radar.grid(True, alpha=0.3)

            self.ax_radar.plot(0, 0, 'bo', markersize=12, label='Main Device')
            self.ax_radar.text(0, 0.5, "Main Device", ha='center', fontsize=8)

            if not self.current_devices:
                self.ax_radar.text(0, 0, "No devices detected", ha='center', va='center', fontsize=12)
            else:
                for i, (mac, (name, rssi, distance, timestamp)) in enumerate(self.current_devices.items()):
                    angle = (i * 2 * np.pi) / max(len(self.current_devices), 1)
                    color = plt.cm.viridis(rssi / -30)
                    
                    if mac in self.device_history:
                        history = self.device_history[mac]
                        for j, (h_rssi, h_distance, h_time) in enumerate(history):
                            alpha = 0.2 + 0.8 * (j / len(history))
                            self.ax_radar.plot(angle, h_distance, 'o', color=color, markersize=4, alpha=alpha)
                    
                    self.ax_radar.plot(angle, distance, 'o', color=color, markersize=8)
                    self.ax_radar.plot([0, angle], [0, distance], 'k--', alpha=0.3)
                    
                    age = time.time() - timestamp
                    label = f"{name}\n{distance:.2f}m\n{rssi}dBm\n{age:.1f}s"
                    self.ax_radar.text(angle, distance + 0.2, label, ha='center', fontsize=8,
                                     bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

            self.ax_radar.legend(loc='upper right')

            if self.current_devices:
                table_data = [[name, f"{rssi}", f"{distance:.2f}", mac] 
                            for mac, (name, rssi, distance, _) in self.current_devices.items()]
                table = self.ax_table.table(cellText=table_data,
                                         colLabels=['Name', 'RSSI', 'Distance (m)', 'MAC'],
                                         loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.5)
            self.ax_table.axis('off')
            self.ax_table.set_title('Detected Devices')

            # Display AI response (removed from plot, will show in alert)
            self.ax_ai_response.axis('off')
            self.ax_ai_response.text(0.5, 0.5, "The AI response would be generated when the first click is made on the pause button. OvO ", ha='center', va='center', fontsize=10,
                                   wrap=True, bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray'))

    def scan_thread(self):
        """Continuous scanning thread with adaptive interval."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while not self.stop_animation:
            start_time = time.time()
            loop.run_until_complete(self.scan_bluetooth_devices())
            elapsed = time.time() - start_time
            sleep_time = max(0.1, self.scan_interval - elapsed)
            time.sleep(sleep_time)

    def toggle_pause(self, event):
        """Toggle pause state and send radar data to AI on first pause."""
        self.paused = not self.paused
        self.ax_pause.button_label = "Resume" if self.paused else "Pause"

        if self.paused and self.first_pause:
            self.first_pause = True
            self.send_to_ai()

    def send_to_ai(self):
        """Send current radar data to AI and display response in alert."""
        try:
            # Format current device data
            device_data = [
                {"Name": name, "RSSI": rssi, "Distance": f"{distance:.2f}m", "MAC": mac}
                for mac, (name, rssi, distance, _) in self.current_devices.items()
            ]
            question = f"分析以下藍牙裝置數據: {json.dumps(device_data, indent=2)}"
            
            # Send data to AI
            data = {
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": question}],
                "stream": False
            }
            url = "http://localhost:11434/api/chat"
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                response_json = json.loads(response.text)
                self.ai_response = response_json["message"]["content"]
                cleaned_response = self.ai_response.replace("*", "")
                logging.info(f"AI Response: {cleaned_response}")
                print(f"AI Response: {cleaned_response}")
                # Display AI response in tkinter alert
                self.root.after(0, lambda: messagebox.showinfo("AI Response", cleaned_response))
            else:
                self.ai_response = f"Error: AI request failed with status {response.status_code}"
                logging.error(self.ai_response)
                print(self.ai_response)
                # Display error in tkinter alert
                #self.root.after(0, lambda: messagebox.showerror("AI Error", self.ai_response))
        except Exception as e:
            self.ai_response = f"Error sending data to AI: {str(e)}"
            logging.error(self.ai_response)
            print(self.ai_response)
            # Display error in tkinter alert
            #self.root.after(0, lambda: messagebox.showerror("AI Error", self.ai_response))

    def update_rssi(self, val):
        """Update RSSI filter."""
        self.min_rssi = val

    def update_distance(self, val):
        """Update maximum detection distance."""
        self.max_distance = val

    def update_interval(self, val):
        """Update detection scan interval."""
        self.scan_interval = val

    def start_radar(self):
        """Start the enhanced Bluetooth radar."""
        print("Starting Enhanced Bluetooth Radar...")
        print("Close the graph window or click Pause to stop.")

        # Setup controls
        pause_button = Button(self.ax_pause, 'Pause')
        pause_button.on_clicked(self.toggle_pause)
        
        rssi_slider = Slider(self.ax_rssi, 'Min RSSI', -100, -30, valinit=self.min_rssi)
        rssi_slider.on_changed(self.update_rssi)

        distance_slider = Slider(self.ax_distance, 'Max Distance', 1.0, 20.0, valinit=self.max_distance)
        distance_slider.on_changed(self.update_distance)

        interval_slider = Slider(self.ax_interval, 'Scan Interval (s)', 0.5, 5.0, valinit=self.scan_interval)
        interval_slider.on_changed(self.update_interval)

        # Start scanning thread
        self.stop_animation = False
        scan_thread = threading.Thread(target=self.scan_thread)
        scan_thread.daemon = True
        scan_thread.start()

        # Start animation
        ani = FuncAnimation(self.fig, self.update_plot, interval=500)
        plt.tight_layout()
        plt.show()

        # Cleanup
        self.stop_animation = True
        self.root.destroy()  # Clean up tkinter root
        logging.info("Bluetooth Radar stopped")
        print("Bluetooth Radar stopped.")

if __name__ == "__main__":
    radar = EnhancedBluetoothRadar(max_distance=5.0, scan_interval=1.0)
    radar.start_radar()