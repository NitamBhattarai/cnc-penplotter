# hershey_gcode_cli.py
# Install: pip install Hershey-Fonts
# Run:     python hershey_gcode_cli.py
# Type any text -> prints Hershey stroke-based G-code to the terminal.
#
# Updated behavior:
# - Fixed font size: capital-letter height ≈ 0.5 cm (5 mm)
# - Text is anchored from TOP-LEFT of the workspace (with margin)
# - Multi-line supported (real newlines). Lines go DOWN from the top.

from HersheyFonts import HersheyFonts

# ===== Plotter / workspace config (mm) =====
WORKSPACE_WIDTH_MM  = 150
WORKSPACE_HEIGHT_MM = 150
MARGIN_MM           = 5
FEEDRATE            = 1500

# Target "capital letter height" (0.5 cm = 5 mm)
TARGET_CAP_HEIGHT_MM = 5.0

# Extra gap between lines, as a fraction of cap height
LINE_GAP_CAP_MULT = 0.35  # 0.2 tighter, 0.6 looser

# Pen commands (match your GRBL setup)
PEN_DOWN_CMD = "M03 S45\nG4 P0.2"
PEN_UP_CMD   = "M5\nG4 P0.2"

# HersheyFonts includes italic variants such as: "timesi" (Times Italic), "rowmani" (Roman Italic).
# Use one of these for italic handwriting-like output.
HERSHEY_FONT_NAME = "timesi"  # italic font (alternatives: "rowmani", "scriptc")

# Axis flips (if your machine is mirrored)
FLIP_X = False
FLIP_Y = False

# Clamp into workspace (safer)
CLAMP_COORDS = True


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def bbox_of_segments(segs):
    xs, ys = [], []
    for (x1, y1), (x2, y2) in segs:
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), min(ys), max(xs), max(ys)


def segments_for_multiline_text_down(hf: HersheyFonts, text: str, line_gap_units: float):
    """
    Build segments for multi-line text in font units.
    Each line is normalized so its TOP is y=0 and LEFT is x=0.
    Lines are stacked downward.
    """
    lines = text.splitlines() or [""]

    all_segs = []
    y_cursor = 0.0  # start at top line, then move DOWN (negative y)

    for ln in lines:
        segs = list(hf.lines_for_text(ln))
        if not segs:
            y_cursor -= line_gap_units
            continue

        minx, miny, maxx, maxy = bbox_of_segments(segs)

        # Normalize line: left = 0, top = 0
        norm = [((x1 - minx, y1 - maxy), (x2 - minx, y2 - maxy)) for (x1, y1), (x2, y2) in segs]

        # Shift line down by y_cursor
        shifted = [((x1, y1 + y_cursor), (x2, y2 + y_cursor)) for (x1, y1), (x2, y2) in norm]
        all_segs.extend(shifted)

        # Advance cursor down by line height + gap
        height = maxy - miny
        y_cursor -= (height + line_gap_units)

    return all_segs


def compute_mm_per_unit_for_cap_height(hf: HersheyFonts):
    """Compute mm-per-font-unit so that capital 'H' height == TARGET_CAP_HEIGHT_MM."""
    segs = list(hf.lines_for_text("H"))
    if not segs:
        return 0.35
    _, miny, _, maxy = bbox_of_segments(segs)
    cap_height_units = maxy - miny
    if cap_height_units <= 0:
        return 0.35
    return TARGET_CAP_HEIGHT_MM / cap_height_units


def units_to_mm_top_left(segs_units, mm_per_unit):
    """
    Convert font-unit segments to mm and anchor the WHOLE text block to top-left.
    Text block's top-left (minx,maxy) maps to (MARGIN_MM, WORKSPACE_HEIGHT_MM - MARGIN_MM).
    """
    if not segs_units:
        return []

    minx, miny, maxx, maxy = bbox_of_segments(segs_units)

    anchor_x = MARGIN_MM
    anchor_y = WORKSPACE_HEIGHT_MM - MARGIN_MM

    out = []
    for (x1, y1), (x2, y2) in segs_units:
        X1 = (x1 - minx) * mm_per_unit + anchor_x
        Y1 = (y1 - maxy) * mm_per_unit + anchor_y
        X2 = (x2 - minx) * mm_per_unit + anchor_x
        Y2 = (y2 - maxy) * mm_per_unit + anchor_y

        if FLIP_X:
            X1 = WORKSPACE_WIDTH_MM - X1
            X2 = WORKSPACE_WIDTH_MM - X2
        if FLIP_Y:
            Y1 = WORKSPACE_HEIGHT_MM - Y1
            Y2 = WORKSPACE_HEIGHT_MM - Y2

        if CLAMP_COORDS:
            X1 = clamp(X1, MARGIN_MM, WORKSPACE_WIDTH_MM - MARGIN_MM)
            X2 = clamp(X2, MARGIN_MM, WORKSPACE_WIDTH_MM - MARGIN_MM)
            Y1 = clamp(Y1, MARGIN_MM, WORKSPACE_HEIGHT_MM - MARGIN_MM)
            Y2 = clamp(Y2, MARGIN_MM, WORKSPACE_HEIGHT_MM - MARGIN_MM)

        out.append(((X1, Y1), (X2, Y2)))

    return out


def to_gcode(segs_mm):
    out = []
    out.append("G21")  # mm
    out.append("G90")  # absolute
    out.append(PEN_UP_CMD)
    out.append(f"F{FEEDRATE}")

    # Safe/robust: lift between every segment (verbose but reliable)
    for (x1, y1), (x2, y2) in segs_mm:
        out.append(PEN_UP_CMD)
        out.append(f"G0 X{x1:.3f} Y{y1:.3f}")
        out.append(PEN_DOWN_CMD)
        out.append(f"G1 X{x2:.3f} Y{y2:.3f}")
        out.append(PEN_UP_CMD)

    out.append("M30")
    return "\n".join(out)


def text_to_hershey_gcode(text: str):
    text = (text or "").rstrip("\n")
    if not text.strip():
        return "\n".join(["G21", "G90", PEN_UP_CMD, "M30"])

    hf = HersheyFonts()
    hf.load_default_font(HERSHEY_FONT_NAME)
    hf.normalize_rendering(1.0)

    mm_per_unit = compute_mm_per_unit_for_cap_height(hf)

    # Convert one cap-height (mm) back into units for spacing
    cap_height_units = TARGET_CAP_HEIGHT_MM / mm_per_unit
    line_gap_units = cap_height_units * LINE_GAP_CAP_MULT

    segs_units = segments_for_multiline_text_down(hf, text, line_gap_units=line_gap_units)
    segs_mm = units_to_mm_top_left(segs_units, mm_per_unit=mm_per_unit)

    return to_gcode(segs_mm)


def main():
    print(f"Hershey font: {HERSHEY_FONT_NAME}")
    print(f"Target capital height: {TARGET_CAP_HEIGHT_MM} mm (0.5 cm)")
    print("Anchored: TOP-LEFT (with margin). Multi-line: paste text with real new lines.\n")

    while True:
        try:
            s = input("Text> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not s.strip():
            break

        gcode = text_to_hershey_gcode(s)
        print("\n--- GCODE START ---")
        print(gcode)
        print("--- GCODE END ---\n")


if __name__ == "__main__":
    main()