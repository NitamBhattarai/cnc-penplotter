# hershey_gcode_cli_fixed_size_top_right.py
# pip install Hershey-Fonts
# Run: python hershey_gcode_cli_fixed_size_top_right.py
#
# Behavior:
# - Fixed font size: capital-letter height ≈ 0.5 cm (5 mm)
# - Text is anchored to START from TOP-RIGHT of the workspace (with margin)
# - Multi-line supported (real newlines). Lines go DOWN from the top.

from HersheyFonts import HersheyFonts

# ===== Plotter / workspace config (mm) =====
WORKSPACE_WIDTH_MM  = 150
WORKSPACE_HEIGHT_MM = 150
MARGIN_MM           = 5
FEEDRATE            = 1500

# Target "capital letter height" (0.5 cm = 5 mm)
TARGET_CAP_HEIGHT_MM = 5.0

# Extra gap between lines, in "cap-height" multiples
LINE_GAP_CAP_MULT = 0.35  # tweak: 0.2 tighter, 0.6 looser

# Pen commands (match your GRBL setup)
PEN_DOWN_CMD = "M03 S45\nG4 P0.2"
PEN_UP_CMD   = "M5\nG4 P0.2"

# Italic variants: "timesi" (Times Italic), "rowmani" (Roman Italic). You can also try "scriptc" for a cursive look.
HERSHEY_FONT_NAME = "timesi"

# Optional flips (if your machine is mirrored)
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
    Anchoring is NOT applied here; we just stack lines downward.
    """
    lines = text.splitlines() or [""]

    all_segs = []
    y_cursor = 0.0  # start at top line, then move DOWN (negative y)

    for ln in lines:
        segs = list(hf.lines_for_text(ln))
        if not segs:
            y_cursor -= line_gap_units
            continue

        # Normalize this line so it starts at x=0 (left), and its TOP is y=0
        minx, miny, maxx, maxy = bbox_of_segments(segs)

        # Make line's top = 0 by subtracting maxy; make left = 0 by subtracting minx
        norm = [((x1 - minx, y1 - maxy), (x2 - minx, y2 - maxy)) for (x1, y1), (x2, y2) in segs]

        # Shift line down by y_cursor (y_cursor is negative as we go down)
        shifted = [((x1, y1 + y_cursor), (x2, y2 + y_cursor)) for (x1, y1), (x2, y2) in norm]
        all_segs.extend(shifted)

        # Move cursor down by this line's height + gap
        height = maxy - miny
        y_cursor -= (height + line_gap_units)

    return all_segs


def compute_mm_per_unit_for_cap_height(hf: HersheyFonts):
    """
    Compute mm-per-font-unit so that a typical capital letter is TARGET_CAP_HEIGHT_MM tall.

    We use 'H' as the reference capital letter (you can switch to 'M' or 'A' if you prefer).
    """
    ref = "H"
    segs = list(hf.lines_for_text(ref))
    if not segs:
        # fallback safe value
        return 0.35

    _, miny, _, maxy = bbox_of_segments(segs)
    cap_height_units = (maxy - miny)
    if cap_height_units <= 0:
        return 0.35

    return TARGET_CAP_HEIGHT_MM / cap_height_units


def units_to_mm_top_left(segs_units, mm_per_unit):
    """
    Convert font-unit segments to mm and anchor the WHOLE text block to top-left.
    Top-left anchor point: (MARGIN_MM, WORKSPACE_HEIGHT_MM - MARGIN_MM)
    """
    if not segs_units:
        return []

    minx, miny, maxx, maxy = bbox_of_segments(segs_units)

    # We want the text block's top-left (minx, maxy) to land at the workspace top-left (with margin)
    anchor_x = MARGIN_MM
    anchor_y = WORKSPACE_HEIGHT_MM - MARGIN_MM

    segs_mm = []
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

        segs_mm.append(((X1, Y1), (X2, Y2)))

    return segs_mm


def to_gcode(segs_mm):
    out = []
    out.append("G21")  # mm
    out.append("G90")  # absolute
    out.append(PEN_UP_CMD)
    out.append(f"F{FEEDRATE}")

    # Simple/robust: lift between every segment (safe, but verbose)
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
    hf.normalize_rendering(1.0)  # keep native units

    mm_per_unit = compute_mm_per_unit_for_cap_height(hf)

    # Line gap in units based on cap height
    # Convert 1 cap-height (mm) back into units using mm_per_unit
    cap_height_units = TARGET_CAP_HEIGHT_MM / mm_per_unit
    line_gap_units = cap_height_units * LINE_GAP_CAP_MULT

    segs_units = segments_for_multiline_text_down(hf, text, line_gap_units=line_gap_units)
    segs_mm = units_to_mm_top_left(segs_units, mm_per_unit=mm_per_unit)

    return to_gcode(segs_mm)


def main():
    print(f"Hershey font: {HERSHEY_FONT_NAME}")
    print(f"Target capital height: {TARGET_CAP_HEIGHT_MM} mm (0.5 cm)")
    print("Anchored: TOP-RIGHT (with margin). Multi-line: paste text with real new lines.\n")

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