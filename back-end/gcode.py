"""gcode.py

Text -> Hershey stroke font -> GRBL-friendly pen-plotter G-code.

Exports:
  - text_to_gcode(text: str) -> str

Behavior:
  - Fixed font size: capital-letter height set by TARGET_CAP_HEIGHT_MM
  - Italic Hershey font by default (Times Italic)
  - Placement: LEFT-MIDDLE (block left-aligned to margin, vertically centered as a whole)
  - Multi-line supported; long lines automatically wrap to fit within width

Notes:
  - Requires: pip install Hershey-Fonts
"""

from __future__ import annotations

from HersheyFonts import HersheyFonts

# ===== Plotter / workspace config (mm) =====
WORKSPACE_WIDTH_MM: float = 150.0
WORKSPACE_HEIGHT_MM: float = 150.0
MARGIN_MM: float = 5.0

# Motion
FEEDRATE: int = 2500

# Target "capital letter height" (0.5 cm = 5 mm)
TARGET_CAP_HEIGHT_MM: float = 10.0

# Extra gap between lines, as a fraction of cap height
LINE_GAP_CAP_MULT: float = 0.35  # 0.2 tighter, 0.6 looser

# Pen commands (match your GRBL setup)
# Long dwells make plotting painfully slow. Increase PEN_DWELL_S only if your
# pen actuator (servo/solenoid) needs more time to settle.
PEN_DWELL_S: float = 0.0
PEN_DOWN_CMD: str = f"M03 S35\nG4 P{PEN_DWELL_S}"
PEN_UP_CMD: str = f"M5\nG4 P{PEN_DWELL_S}"

# Italic variants: "timesi" (Times Italic), "rowmani" (Roman Italic). You can also try "scriptc".
HERSHEY_FONT_NAME: str = "rowmans"

# Optional flips (if your machine is mirrored)
FLIP_X: bool = False
FLIP_Y: bool = False

# Clamp into workspace (safer)
CLAMP_COORDS: bool = True

# Wrap long lines to fit within the drawable width
WRAP_TEXT: bool = True
MAX_TEXT_WIDTH_MM: float = WORKSPACE_WIDTH_MM - 2 * MARGIN_MM

# If a segment starts close to the previous segment end, keep the pen down and continue.
# This drastically reduces M5/M03 toggles (especially for letters like O).
CONNECT_TOL_MM: float = 0.60


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _bbox_of_segments(segs):
    """Return (minx, miny, maxx, maxy) for a list of segments."""
    xs, ys = [], []
    for (x1, y1), (x2, y2) in segs:
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return min(xs), min(ys), max(xs), max(ys)


def _line_width_units(hf: HersheyFonts, s: str) -> float:
    segs = list(hf.lines_for_text(s))
    if not segs:
        return 0.0
    minx, _, maxx, _ = _bbox_of_segments(segs)
    return maxx - minx


def _estimate_max_chars_per_line(hf: HersheyFonts, max_width_units: float) -> int:
    """Rough estimate: varies by letters/spaces; used for debugging/intuition."""
    sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    w = _line_width_units(hf, sample)
    if w <= 0:
        return 0
    avg = w / len(sample)
    if avg <= 0:
        return 0
    return int(max_width_units // avg)


def _wrap_text_lines(hf: HersheyFonts, text: str, max_width_units: float):
    """Wrap input into lines so each line's width (font units) <= max_width_units.

    - Preserves existing newlines.
    - Wraps on spaces; if a single word exceeds width, hard-wraps by characters.
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
            candidate = w if cur == "" else (cur + " " + w)

            if _line_width_units(hf, candidate) <= max_width_units:
                cur = candidate
                continue

            if cur:
                out_lines.append(cur)
                cur = ""

            # Hard-wrap if a single word is wider than the line
            if _line_width_units(hf, w) > max_width_units:
                chunk = ""
                for ch in w:
                    cand2 = chunk + ch
                    if _line_width_units(hf, cand2) <= max_width_units:
                        chunk = cand2
                    else:
                        if chunk:
                            out_lines.append(chunk)
                        chunk = ch
                cur = chunk
            else:
                cur = w

        out_lines.append(cur)

    return out_lines


def _segments_for_multiline_text_down(hf: HersheyFonts, lines, line_gap_units: float):
    """Return stroke segments in font units for multi-line text.

    Each line is normalized so its LEFT is x=0 and its TOP is y=0,
    then lines are stacked downward.
    """
    lines = list(lines) if lines is not None else [""]

    all_segs = []
    y_cursor = 0.0  # start at top line; move DOWN (negative y)

    for ln in lines:
        segs = list(hf.lines_for_text(ln))
        if not segs:
            y_cursor -= line_gap_units
            continue

        minx, miny, maxx, maxy = _bbox_of_segments(segs)

        # Normalize line: left=0 and top=0
        norm = [
            ((x1 - minx, y1 - maxy), (x2 - minx, y2 - maxy))
            for (x1, y1), (x2, y2) in segs
        ]

        # Shift line down by y_cursor
        shifted = [
            ((x1, y1 + y_cursor), (x2, y2 + y_cursor))
            for (x1, y1), (x2, y2) in norm
        ]
        all_segs.extend(shifted)

        # Advance cursor down by line height + gap
        height = maxy - miny
        y_cursor -= (height + line_gap_units)

    return all_segs


def _mm_per_unit_for_cap_height(hf: HersheyFonts) -> float:
    """Scale so that capital 'H' height is TARGET_CAP_HEIGHT_MM."""
    segs = list(hf.lines_for_text("H"))
    if not segs:
        return 0.35

    _, miny, _, maxy = _bbox_of_segments(segs)
    cap_height_units = maxy - miny
    if cap_height_units <= 0:
        return 0.35

    return TARGET_CAP_HEIGHT_MM / cap_height_units


def _units_to_mm_left_middle(segs_units, mm_per_unit: float):
    """Convert font-unit segments to mm with LEFT-MIDDLE placement.

    - X: align block left edge to left margin.
    - Y: vertically center the entire text block around the page midline.
    """
    if not segs_units:
        return []

    minx, miny, maxx, maxy = _bbox_of_segments(segs_units)

    anchor_x = MARGIN_MM
    workspace_center_y = WORKSPACE_HEIGHT_MM / 2.0
    block_center_y_units = (miny + maxy) / 2.0

    out = []
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
            X1 = _clamp(X1, MARGIN_MM, WORKSPACE_WIDTH_MM - MARGIN_MM)
            X2 = _clamp(X2, MARGIN_MM, WORKSPACE_WIDTH_MM - MARGIN_MM)
            Y1 = _clamp(Y1, MARGIN_MM, WORKSPACE_HEIGHT_MM - MARGIN_MM)
            Y2 = _clamp(Y2, MARGIN_MM, WORKSPACE_HEIGHT_MM - MARGIN_MM)

        out.append(((X1, Y1), (X2, Y2)))

    return out


def _dist2(a, b) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def _to_gcode(segs_mm) -> str:
    """Convert segments to G-code while minimizing pen toggles.

    Strategy:
    - Rapid (pen up) to the start of a stroke.
    - Pen down.
    - For subsequent segments:
        * If the next segment starts where we are (within CONNECT_TOL_MM), keep pen down.
        * Otherwise lift pen, rapid to new start, pen down again.

    This makes letters like 'O' much faster because they are made of many connected segments.
    """
    out = []
    out.append("G21")  # mm
    out.append("G90")  # absolute
    out.append(PEN_UP_CMD)
    out.append(f"F{FEEDRATE}")

    tol2 = CONNECT_TOL_MM * CONNECT_TOL_MM
    pen_is_down = False
    cur_pos = None  # (x,y)

    for (x1, y1), (x2, y2) in segs_mm:
        start = (x1, y1)
        end = (x2, y2)

        # If we're not at the segment start, reposition with pen up.
        if (cur_pos is None) or (_dist2(cur_pos, start) > tol2):
            if pen_is_down:
                out.append(PEN_UP_CMD)
                pen_is_down = False
            out.append(f"G0 X{x1:.3f} Y{y1:.3f}")
            out.append(PEN_DOWN_CMD)
            pen_is_down = True

        # Draw to segment end (keep pen down)
        out.append(f"G1 X{x2:.3f} Y{y2:.3f}")
        cur_pos = end

    if pen_is_down:
        out.append(PEN_UP_CMD)

    out.append("M30")
    return "\n".join(out)


def text_to_gcode(text: str) -> str:
    """Public API used by the Flask app."""
    text = (text or "").rstrip("\n")
    if not text.strip():
        return "\n".join(["G21", "G90", PEN_UP_CMD, "M30"])

    hf = HersheyFonts()
    hf.load_default_font(HERSHEY_FONT_NAME)
    hf.normalize_rendering(1.0)

    mm_per_unit = _mm_per_unit_for_cap_height(hf)

    # Spacing in units based on cap height
    cap_height_units = TARGET_CAP_HEIGHT_MM / mm_per_unit
    line_gap_units = cap_height_units * LINE_GAP_CAP_MULT

    # Wrap width in units
    max_width_units = MAX_TEXT_WIDTH_MM / mm_per_unit

    if WRAP_TEXT:
        lines = _wrap_text_lines(hf, text, max_width_units=max_width_units)
    else:
        lines = text.splitlines() or [""]

    segs_units = _segments_for_multiline_text_down(hf, lines, line_gap_units=line_gap_units)
    segs_mm = _units_to_mm_left_middle(segs_units, mm_per_unit=mm_per_unit)

    return _to_gcode(segs_mm)


# Optional CLI for quick testing (does not affect Flask usage)
if __name__ == "__main__":
    hf = HersheyFonts()
    hf.load_default_font(HERSHEY_FONT_NAME)
    hf.normalize_rendering(1.0)
    mm_per_unit = _mm_per_unit_for_cap_height(hf)
    max_width_units = MAX_TEXT_WIDTH_MM / mm_per_unit
    est_chars = _estimate_max_chars_per_line(hf, max_width_units=max_width_units)

    print(f"Hershey font: {HERSHEY_FONT_NAME}")
    print(f"Target cap height: {TARGET_CAP_HEIGHT_MM} mm")
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

        print("\n--- GCODE START ---")
        print(text_to_gcode(s))
        print("--- GCODE END ---\n")