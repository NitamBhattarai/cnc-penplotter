import urequests
import machine
import time

uart = machine.UART(2, baudrate=115200, tx=17, rx=16)

BACKEND_URL = "http://cnc-penplotter.onrender.com/gcode"

def wait_for_ok():
    while True:
        if uart.any():
            r = uart.readline()
            if r and b"ok" in r:
                return

def send_line(line):
    uart.write(line + "\n")
    wait_for_ok()

time.sleep(3)
uart.write(b"\r\n\r\n")
time.sleep(2)

r = urequests.get(BACKEND_URL)
gcode = r.text.splitlines()
print("Fetched G-code with",len(gcode), "lines")
r.close()

for line in gcode:
    if line.strip():
        send_line(line)
        time.sleep(0.05)
