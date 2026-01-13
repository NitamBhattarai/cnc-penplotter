from font import FONT  # your existing font dictionary

# ===== CONFIGURATION =====
WORKSPACE_WIDTH = 26
WORKSPACE_HEIGHT = 26
MARGIN = 1

X_START = 1
Y_START = 1
SCALE = 4
FEEDRATE = 800
LETTER_SPACING = 5
LINE_SPACING = 7

PEN_DOWN_CMD = "M3"
PEN_UP_CMD = "M5"

# ===== HELPER =====
def clamp(val, min_v, max_v):
    return max(min_v, min(val, max_v))

# ===== MAIN FUNCTION =====
def text_to_gcode(text):
    gcode = []

    # ---- Header ----
    gcode.append("G21        ; mm units")
    gcode.append("G90        ; absolute positioning")
    gcode.append(PEN_UP_CMD)
    gcode.append(f"G0 X{X_START:.2f} Y{Y_START:.2f}")

    x = X_START
    y = Y_START
    max_x = WORKSPACE_WIDTH - MARGIN
    max_y = WORKSPACE_HEIGHT - MARGIN

    for char in text:
        # ---- New line ----
        if char == "\n":
            x = X_START
            y += LINE_SPACING
            if y > max_y:
                break
            gcode.append(PEN_UP_CMD)
            gcode.append(f"G0 X{x:.2f} Y{y:.2f}")
            continue

        # ---- Space ----
        if char == " ":
            x += LETTER_SPACING
            if x > max_x:
                x = X_START
                y += LINE_SPACING
            continue

        strokes = FONT.get(char, [])
        for stroke in strokes:
            if len(stroke) < 2:
                continue

            # Move to first point (pen up)
            x0, y0 = stroke[0]
            sx0 = clamp(x + x0 * SCALE, MARGIN, max_x)
            sy0 = clamp(y + y0 * SCALE, MARGIN, max_y)

            gcode.append(PEN_UP_CMD)
            gcode.append(f"G0 X{sx0:.2f} Y{sy0:.2f}")
            gcode.append(PEN_DOWN_CMD)

            # Draw stroke
            for px, py in stroke[1:]:
                sx = clamp(x + px * SCALE, MARGIN, max_x)
                sy = clamp(y + py * SCALE, MARGIN, max_y)
                gcode.append(f"G1 X{sx:.2f} Y{sy:.2f} F{FEEDRATE}")

            gcode.append(PEN_UP_CMD)

        # Advance cursor
        x += LETTER_SPACING
        if x > max_x:
            x = X_START
            y += LINE_SPACING
            if y > max_y:
                break

    # ---- Footer ----
    gcode.append(PEN_UP_CMD)
    gcode.append("M30")

    return "\n".join(gcode)