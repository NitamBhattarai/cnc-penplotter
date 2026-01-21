import network, time, urequests, machine, gc

SSID = "DIGICOM"
PASSWORD = "123456789"
BACKEND_URL = "http://cnc-penplotter.onrender.com/gcode"

POLL_SECONDS = 2
NOJOB_TOKENS = ("", "NOJOB", "NONE")

# ---------- WiFi ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
if not wifi.isconnected():
    print("Connecting WiFi...")
    wifi.connect(SSID, PASSWORD)
    while not wifi.isconnected():
        time.sleep(1)
print("WiFi connected:", wifi.ifconfig())

# ---------- UART to GRBL ----------
# Add timeouts to reduce fragmented reads
uart = machine.UART(2, baudrate=115200, tx=17, rx=16, timeout=200, timeout_char=20)

def flush_uart(ms):
    """Drain any pending UART bytes for up to `ms` milliseconds."""
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < ms:
        if uart.any():
            _ = uart.read()  # read everything available
        time.sleep_ms(5)

def read_chunk(timeout_ms):
    """
    Read any available bytes (not necessarily a full line).
    This is more robust than readline() when GRBL responses arrive split.
    """
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if uart.any():
            return uart.read()
        time.sleep_ms(5)
    return None

def send_line_wait(line, timeout_ms):
    """
    Send one command and wait for a success/fail response.
    Robust to:
      - split 'o' then 'k'
      - GRBL banner lines
      - [Pgm End]
    """
    line = (line or "").strip()
    if not line:
        return True

    # MicroPython UART expects bytes
    uart.write((line + "\n").encode())

    start = time.ticks_ms()
    buf = b""

    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        r = read_chunk(800)
        if not r:
            continue

        # accumulate raw bytes (lowercased) so split 'ok' is still detected
        buf += r.lower()

        # debug print (best-effort)
        try:
            txt = r.decode(errors="ignore").strip()
            if txt:
                # Can contain partials; still useful for debugging
                print("GRBL>", txt)
        except:
            pass

        # success conditions
        if b"ok" in buf or b"pgm end" in buf:
            return True

        # fail conditions
        if b"alarm" in buf or b"error" in buf:
            return False

    print("Timeout waiting for GRBL")
    return False

def normalize_gcode_line(line):
    line = (line or "").strip()
    if not line:
        return None
    # remove ; comments
    if ";" in line:
        line = line.split(";", 1)[0].strip()
    # skip () comment-only lines
    if not line or line.startswith("("):
        return None
    return line

def grbl_home_and_zero():
    """Home ONCE at boot and establish a known work origin."""
    # Wake GRBL and clear any boot text
    uart.write(b"\r\n\r\n")
    time.sleep(0.5)
    flush_uart(1200)

    # Pen up (avoid dragging)
    if not send_line_wait("M5", 8000):
        print("❌ Pen-up (M5) failed. Halting.")
        while True:
            time.sleep(1)

    # Unlock (GRBL often starts in Alarm lock until $X)
    unlocked = False
    for _ in range(5):
        ok = send_line_wait("$X", 8000)
        if ok:
            unlocked = True
            break
        time.sleep(0.3)

    if not unlocked:
        print("❌ Unlock failed. Halting.")
        while True:
            time.sleep(1)

    # Home
    if not send_line_wait("$H", 90000):
        print("❌ Homing failed. System halted.")
        while True:
            time.sleep(1)

    # Modes + work origin at post-homing pull-off
    send_line_wait("G90", 5000)
    send_line_wait("G21", 5000)
    send_line_wait("G92 X0 Y0", 5000)

def reset_after_job():
    """
    After each job:
      - pen up
      - ensure G90/G21
      - MOVE BACK TO (0,0)
      - re-assert (0,0)
    """
    if not send_line_wait("M5", 8000):
        print("❌ Pen-up (M5) failed after job. Halting.")
        while True:
            time.sleep(1)

    send_line_wait("G90", 5000)
    send_line_wait("G21", 5000)

    # go back to origin (0,0)
    if not send_line_wait("G0 X0 Y0", 30000):
        print("❌ Failed to return to X0 Y0. Halting.")
        while True:
            time.sleep(1)

    # re-assert that this is origin
    send_line_wait("G92 X0 Y0", 5000)

    # clear any leftover uart chatter
    flush_uart(600)

def fetch_job_text():
    try:
        r = urequests.get(BACKEND_URL)
        text = r.text
        r.close()
        if text is None:
            return None
        text = text.strip()
        if text.upper() in NOJOB_TOKENS or len(text) == 0:
            return None
        return text
    except Exception as e:
        print("Fetch error:", e)
        return None

def run_job(gcode_text):
    lines = gcode_text.splitlines()
    print("Running job with", len(lines), "lines")

    for raw in lines:
        line = normalize_gcode_line(raw)
        if line is None:
            continue

        ok = send_line_wait(line, 20000)
        if not ok:
            print("FAILED on:", line)
            print("ALARM/ERROR — stopping. Manual reset needed.")
            while True:
                time.sleep(1)

    print("JOB DONE")
    return True

# ---------- Main ----------
print("Boot: homing + zeroing (once)...")
grbl_home_and_zero()
print("Standby: waiting for jobs...")

while True:
    job = fetch_job_text()
    if job is None:
        time.sleep(POLL_SECONDS)
        continue

    print("New job received!")
    run_job(job)

    print("Post-job: return to X0 Y0 + reset origin...")
    reset_after_job()

    gc.collect()
    time.sleep(POLL_SECONDS)
