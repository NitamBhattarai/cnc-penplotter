# hershey_gcode_cli_fixed_size_top_right.py
# pip install Hershey-Fonts
# Run: python hershey_gcode_cli_fixed_size_top_right.py
#
# Behavior:
# - Fixed font size: capital-letter height ≈ 0.5 cm (5 mm)
# - Text starts from the LEFT side and the whole text block is vertically centered ("left-middle")
# - Multi-line supported. Lines are stacked downward and the block is centered around the page middle.
# - If a line is too long, text is wrapped to fit within the workspace width.

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
PEN_DOWN_CMD = "M03 S35\nG4 P0.2"
PEN_UP_CMD   = "M5\nG4 P0.2"

# Italic variants: "timesi" (Times Italic), "rowmani" (Roman Italic). You can also try "scriptc" for a cursive look.
HERSHEY_FONT_NAME = "timesi"

# Optional flips (if your machine is mirrored)
FLIP_X = False
FLIP_Y = False

# Clamp into workspace (safer)
CLAMP_COORDS = True

# Wrap long lines to fit within the drawable width
WRAP_TEXT = True
# Max drawable width (mm) inside margins
MAX_TEXT_WIDTH_MM = WORKSPACE_WIDTH_MM - 2 * MARGIN_MM


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


def line_width_units(hf: HersheyFonts, s: str) -> float:
    segs = list(hf.lines_for_text(s))
    if not segs:
        return 0.0
    minx, _, maxx, _ = bbox_of_segments(segs)
    return maxx - minx


def estimate_max_chars_per_line(hf: HersheyFonts, max_width_units: float) -> int:
    # Use a mixed sample to estimate average character width
    sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    w = line_width_units(hf, sample)
    if w <= 0:
        return 0
    avg = w / len(sample)
    if avg <= 0:
        return 0
    return int(max_width_units // avg)


def wrap_text_lines(hf: HersheyFonts, text: str, max_width_units: float):
    """
    Wrap input text into a list of lines so each line's width (in font units) <= max_width_units.
    - Preserves existing newlines.
    - Wraps primarily on spaces; if a single word exceeds width, it hard-wraps by characters.
    """
    out_lines = []
    for raw_line in (text.splitlines() or [""]):
        line = raw_line.rstrip("\n")
        if not line:
            out_lines.append("")
            continue

        words = line.split(" ")
        cur = ""
        for w in words:
            if cur == "":
                candidate = w
            else:
                candidate = cur + " " + w

            if line_width_units(hf, candidate) <= max_width_units:
                cur = candidate
                continue

            # candidate too wide: push current line if non-empty
            if cur:
                out_lines.append(cur)
                cur = ""

            # if the word itself is too wide, hard-wrap it
            if line_width_units(hf, w) > max_width_units:
                chunk = ""
                for ch in w:
                    cand2 = chunk + ch
                    if line_width_units(hf, cand2) <= max_width_units:
                        chunk = cand2
                    else:
                        if chunk:
                            out_lines.append(chunk)
                        chunk = ch
                if chunk:
                    cur = chunk
            else:
                cur = w

        out_lines.append(cur)

    return out_lines


def segments_for_multiline_text_down(hf: HersheyFonts, lines, line_gap_units: float):
    """
    Build segments for multi-line text in font units.
    Anchoring is NOT applied here; we just stack lines downward.
    """
    lines = list(lines) if lines is not None else [""]

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


def units_to_mm_left_middle(segs_units, mm_per_unit):
    """
    Convert font-unit segments to mm.

    Placement:
    - X: align the block's left edge to the left margin.
    - Y: vertically center the ENTIRE text block around the page midline ("left-middle").

    This means if there are 3 lines, the middle line will be around the center of the page,
    and the top line will start above it.
    """
    if not segs_units:
        return []

    minx, miny, maxx, maxy = bbox_of_segments(segs_units)

    # Left margin anchor for X
    anchor_x = MARGIN_MM

    # Center of the workspace for Y
    workspace_center_y = WORKSPACE_HEIGHT_MM / 2.0
    block_center_y_units = (miny + maxy) / 2.0

    segs_mm = []
    for (x1, y1), (x2, y2) in segs_units:
        X1 = (x1 - minx) * mm_per_unit + anchor_x
        Y1 = (y1 - block_center_y_units) * mm_per_unit + workspace_center_y
        X2 = (x2 - minx) * mm_per_unit + anchor_x
        Y2 = (y2 - block_center_y_units) * mm_per_unit + workspace_center_y

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

    # Maximum width in font units for wrapping
    max_width_units = MAX_TEXT_WIDTH_MM / mm_per_unit

    if WRAP_TEXT:
        lines = wrap_text_lines(hf, text, max_width_units=max_width_units)
    else:
        lines = text.splitlines() or [""]

    segs_units = segments_for_multiline_text_down(hf, lines, line_gap_units=line_gap_units)
    segs_mm = units_to_mm_left_middle(segs_units, mm_per_unit=mm_per_unit)

    return to_gcode(segs_mm)


def main():
    print(f"Hershey font: {HERSHEY_FONT_NAME}")
    print(f"Target capital height: {TARGET_CAP_HEIGHT_MM} mm (0.5 cm)")

    # Rough estimate of how many characters fit per line at the current size
    hf = HersheyFonts()
    hf.load_default_font(HERSHEY_FONT_NAME)
    hf.normalize_rendering(1.0)
    mm_per_unit = compute_mm_per_unit_for_cap_height(hf)
    max_width_units = MAX_TEXT_WIDTH_MM / mm_per_unit
    est_chars = estimate_max_chars_per_line(hf, max_width_units=max_width_units)

    print("Placement: LEFT-MIDDLE (block vertically centered). Long lines wrap to fit width.")
    if est_chars:
        print(f"Approx max characters per line at this size: ~{est_chars} (varies by letters/spaces)")
    print()

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