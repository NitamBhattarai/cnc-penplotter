# gcode.py
from font import FONT

# Configuration
X_START = 10      # starting X position
Y_START = 10      # starting Y position
SCALE = 10        # scale factor for letter size
FEEDRATE = 800    # G-code feedrate
LETTER_SPACING = 12  # space between letters

def text_to_gcode(text):
    gcode = []
    x = X_START
    y = Y_START

    for char in text:
        char = char if char in FONT else ' '  # fallback
        strokes = FONT[char]
        for stroke in strokes:
            if len(stroke) != 2:
                continue
            (x0, y0), (x1, y1) = stroke
            # scale and translate
            x0 = x + x0 * SCALE
            y0 = y + y0 * SCALE
            x1 = x + x1 * SCALE
            y1 = y + y1 * SCALE
            gcode.append(f"G0 X{x0:.2f} Y{y0:.2f}")  # move to start of stroke
            gcode.append(f"G1 X{x1:.2f} Y{y1:.2f} F{FEEDRATE}")  # draw line
        x += LETTER_SPACING  # move to next letter
    return "\n".join(gcode)
