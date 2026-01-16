# gcode.py
from HersheyFonts import HersheyFonts

# ===== CONFIGURATION =====
WORKSPACE_WIDTH = 150
WORKSPACE_HEIGHT = 150
MARGIN = 5
FEEDRATE = 1000

# Coordinate safety / orientation
# If your machine axes are mirrored relative to the generated coordinates, flip them here.
FLIP_X = False
FLIP_Y = False

# Absolute clamp bounds in mm (keeps coordinates inside the workspace even after rounding)
CLAMP_COORDS = True
CLAMP_MIN_X = MARGIN
CLAMP_MIN_Y = MARGIN
CLAMP_MAX_X = WORKSPACE_WIDTH
CLAMP_MAX_Y = WORKSPACE_HEIGHT

# Text placement / sizing
# Increase this to make the text bigger (it will still be clamped to fit the workspace)
SCALE_MULTIPLIER = 1.0

# Alignment inside the workspace: "left" or "center" (right not implemented)
H_ALIGN = "left"
# Alignment inside the workspace: "bottom" or "center" (top not implemented)
V_ALIGN = "bottom"

PEN_DOWN_CMD = "M03 S90"
PEN_UP_CMD = "M5"

# Pick a Hershey font (change if you want)
HERSHEY_FONT_NAME = "futural"  # common; if it errors, try "gothiceng"

_hf = HersheyFonts()
_hf.load_default_font(HERSHEY_FONT_NAME)
_hf.normalize_rendering(1.0)


def _bbox_of_segments(segs):
    xs, ys = [], []
    for (x1, y1), (x2, y2) in segs:
        xs += [x1, x2]
        ys += [y1, y2]
    if not xs:
        return 0, 0, 0, 0
    return min(xs), min(ys), max(xs), max(ys)


def _clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def text_to_gcode(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "\n".join(["G21", "G90", PEN_UP_CMD, "M30"])

    lines = text.splitlines()

    # Build segments for each line and stack them vertically
    all_segs = []
    y_cursor = 0.0
    line_gap = 10.0  # spacing between lines in "font units"

    for ln in lines:
        segs = list(_hf.lines_for_text(ln))

        # Normalize this line so its min x/y becomes 0,0
        minx, miny, maxx, maxy = _bbox_of_segments(segs)
        norm = [((x1 - minx, y1 - miny), (x2 - minx, y2 - miny)) for (x1, y1), (x2, y2) in segs]

        # Shift line up by y_cursor
        shifted = [((x1, y1 + y_cursor), (x2, y2 + y_cursor)) for (x1, y1), (x2, y2) in norm]
        all_segs.extend(shifted)

        # advance cursor for next line
        line_height = (maxy - miny) if segs else 0
        y_cursor += line_height + line_gap

    # Compute overall bbox and scale to fit workspace
    minx, miny, maxx, maxy = _bbox_of_segments(all_segs)
    width = maxx - minx
    height = maxy - miny

    avail_w = WORKSPACE_WIDTH - 2 * MARGIN
    avail_h = WORKSPACE_HEIGHT - 2 * MARGIN

    # avoid divide-by-zero
    if width <= 0: width = 1
    if height <= 0: height = 1

    # Base scale to fit within workspace, then optionally enlarge while still clamping to fit
    base_scale = min(avail_w / width, avail_h / height)
    scale = base_scale * SCALE_MULTIPLIER
    # Clamp so we never exceed available space
    scale = min(scale, avail_w / width, avail_h / height)

    # Compute offsets for alignment
    if H_ALIGN == "center":
        x_offset = MARGIN + (avail_w - width * scale) / 2
    else:  # "left"
        x_offset = MARGIN

    if V_ALIGN == "center":
        y_offset = MARGIN + (avail_h - height * scale) / 2
    else:  # "bottom"
        y_offset = MARGIN

    # Generate G-code
    gcode = []
    gcode.append("G21")  # mm
    gcode.append("G90")  # absolute
    gcode.append(PEN_UP_CMD)

    def mmx(x):
        v = x_offset + (x - minx) * scale
        return (WORKSPACE_WIDTH - v) if FLIP_X else v

    def mmy(y):
        v = y_offset + (y - miny) * scale
        return (WORKSPACE_HEIGHT - v) if FLIP_Y else v

    for (x1, y1), (x2, y2) in all_segs:
        x1m, y1m = mmx(x1), mmy(y1)
        x2m, y2m = mmx(x2), mmy(y2)

        if CLAMP_COORDS:
            x1m = _clamp(x1m, CLAMP_MIN_X, CLAMP_MAX_X)
            y1m = _clamp(y1m, CLAMP_MIN_Y, CLAMP_MAX_Y)
            x2m = _clamp(x2m, CLAMP_MIN_X, CLAMP_MAX_X)
            y2m = _clamp(y2m, CLAMP_MIN_Y, CLAMP_MAX_Y)

        # pen up move to start
        gcode.append(PEN_UP_CMD)
        gcode.append(f"G0 X{x1m:.2f} Y{y1m:.2f}")

        # pen down draw to end
        gcode.append(PEN_DOWN_CMD)
        gcode.append(f"G1 X{x2m:.2f} Y{y2m:.2f} F{FEEDRATE}")

    gcode.append(PEN_UP_CMD)
    gcode.append("M30")
    return "\n".join(gcode)