import network
import time

SSID = "YOUR_WIFI_NAME"
PASSWORD = "YOUR_WIFI_PASSWORD"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

if not wifi.isconnected():
    wifi.connect("rautsantosh_fbrtn", "CLED02FB37")
    while not wifi.isconnected():
        time.sleep(1)

print("WiFi connected:", wifi.ifconfig())
