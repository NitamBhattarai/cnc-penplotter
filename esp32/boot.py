import network
import time

SSID = "rautsantosh_fbrtn"
PASSWORD = "CLED02FB37"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

if not wifi.isconnected():
    wifi.connect(SSID, PASSWORD)
    while not wifi.isconnected():
        time.sleep(1)

print("WiFi connected:", wifi.ifconfig())
