from font import FONT

# Configuration
X_START = 10
Y_START = 10
SCALE = 10
FEEDRATE = 800
LETTER_SPACING = 12
LINE_SPACING = 15

PEN_UP = 5
PEN_DOWN = 0

def text_to_gcode(text):
    gcode = []

    # --- G-code header ---
    gcode.append("G21        ; set units to mm")
    gcode.append("G90        ; absolute positioning")
    gcode.append(f"G0 Z{PEN_UP}")
    gcode.append(f"G0 X{X_START} Y{Y_START}")

    x = X_START
    y = Y_START

    for char in text:
        # New line
        if char == "\n":
            x = X_START
            y += LINE_SPACING
            gcode.append(f"G0 Z{PEN_UP}")
            gcode.append(f"G0 X{x} Y{y}")
            continue

        # Space
        if char == " ":
            x += LETTER_SPACING
            continue

        char = char if char in FONT else ' '
        strokes = FONT[char]

        for stroke in strokes:
            if len(stroke) != 2:
                continue

            (x0, y0), (x1, y1) = stroke

            # scale and translate
            sx0 = x + x0 * SCALE
            sy0 = y + y0 * SCALE
            sx1 = x + x1 * SCALE
            sy1 = y + y1 * SCALE

            # Move pen up → go to start → pen down → draw
            gcode.append(f"G0 Z{PEN_UP}")
            gcode.append(f"G0 X{sx0:.2f} Y{sy0:.2f}")
            gcode.append(f"G1 Z{PEN_DOWN} F300")
            gcode.append(f"G1 X{sx1:.2f} Y{sy1:.2f} F{FEEDRATE}")

        x += LETTER_SPACING

    # --- Footer ---
    gcode.append(f"G0 Z{PEN_UP}")
    gcode.append("M2")

    return "\n".join(gcode)
