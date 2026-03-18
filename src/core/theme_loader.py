"""Theme loading and defaults."""

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULTS = {
    "name": "Default",
    "background_color": "#1a1a1a",
    "text_color": "#ffffff",
    "active_text_color": "#D66E31",                 # burnt orange fill
    "active_text_bold": False,
    "active_text_glow": True,
    "active_glow_color": None,                      # None = same as active_text_color
    "active_font_family": None,                     # None = inherit from font_family
    "active_text_stroke_color": "#6A1E22",          # dark maroon rib/outline
    "active_text_stroke_width": 3,                  # px; 0 = no stroke
    "inactive_text_opacity_gradient": [0.6, 0.4, 0.2],
    "font_family": "Arial",
    "font_size": 72,
    "line_spacing": 1.5,
    "lyric_position": "center",
    "highlight_mode": "line",
    "highlight_dim_alpha": 0.3,
    "text_overlay_opacity": 0,       # int 0-100
    "text_overlay_color": "#000000",
    # Kept for backward compatibility
    "text_position": "center",
    "text_shadow": False,
    "text_shadow_color": "#000000",
    "text_shadow_offset": [3, 3],
    "column_width": 1760,           # px; valid range 200–1920
    "logo_path": "",                # abs or relative path to PNG/JPG; empty = no logo
    "logo_width": 400,              # px wide; height auto-scaled to maintain aspect ratio
    "logo_h_align": "center",       # "left", "center", "right"
    "title_h_align": "center",      # horizontal alignment for intro/outro title text
}


@dataclass
class Theme:
    """Resolved theme settings."""
    name: str
    background_color: str
    text_color: str
    active_text_color: str | None
    active_text_bold: bool
    active_text_glow: bool
    active_glow_color: str | None
    inactive_text_opacity_gradient: list[float]
    font_family: str
    font_size: int
    line_spacing: float
    lyric_position: str = "center"
    active_font_family: str | None = None
    active_text_stroke_color: str = "#6A1E22"
    active_text_stroke_width: int = 3
    highlight_mode: str = "line"
    highlight_dim_alpha: float = 0.3
    text_overlay_opacity: int = 0
    text_overlay_color: str = "#000000"
    # Backward-compat fields
    text_position: str = "center"
    text_shadow: bool = False
    text_shadow_color: str = "#000000"
    text_shadow_offset: list[int] = field(default_factory=lambda: [3, 3])
    column_width: int = 1760
    logo_path: str = ""
    logo_width: int = 400
    logo_h_align: str = "center"
    title_h_align: str = "center"

    @property
    def effective_active_text_color(self) -> str:
        """Return the resolved active line text color."""
        return self.active_text_color or self.text_color

    @property
    def effective_active_glow_color(self) -> str:
        """Return the resolved glow color."""
        return self.active_glow_color or self.effective_active_text_color

    @property
    def line_height(self) -> int:
        """Computed line height in pixels from line_spacing * font_size."""
        return int(self.line_spacing * self.font_size)


def _is_valid_hex_color(value: str) -> bool:
    """Return True if value is a valid #RRGGBB hex color string."""
    if not isinstance(value, str):
        return False
    s = value.lstrip("#")
    if len(s) != 6:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def _validate_theme(data: dict, filepath) -> None:
    """Raise ValueError with clear messages if theme data contains invalid values."""
    errors = []

    for key in ("background_color", "text_color", "text_shadow_color"):
        val = data.get(key)
        if val is not None and not _is_valid_hex_color(val):
            errors.append(f"'{key}': '{val}' is not a valid hex color (expected #RRGGBB)")

    for key in ("active_text_color", "active_glow_color", "active_text_stroke_color"):
        val = data.get(key)
        if val is not None and not _is_valid_hex_color(val):
            errors.append(f"'{key}': '{val}' is not a valid hex color (expected #RRGGBB)")

    sw = data.get("active_text_stroke_width")
    if sw is not None and (not isinstance(sw, int) or not (0 <= sw <= 40)):
        errors.append("'active_text_stroke_width': must be an integer between 0 and 40")

    if "lyric_position" in data and data["lyric_position"] not in ("left", "center", "right"):
        errors.append("'lyric_position': must be 'left', 'center', or 'right'")

    if "highlight_mode" in data and data["highlight_mode"] not in ("line", "word", "character"):
        errors.append("'highlight_mode': must be 'line', 'word', or 'character'")

    grad = data.get("inactive_text_opacity_gradient")
    if grad is not None:
        if not isinstance(grad, list) or not all(
            isinstance(x, (int, float)) and 0.0 <= x <= 1.0 for x in grad
        ):
            errors.append(
                "'inactive_text_opacity_gradient': must be a list of floats between 0.0 and 1.0"
            )

    ls = data.get("line_spacing")
    if ls is not None and (not isinstance(ls, (int, float)) or ls <= 0):
        errors.append("'line_spacing': must be a positive number")

    fs = data.get("font_size")
    if fs is not None and (not isinstance(fs, int) or fs <= 0):
        errors.append("'font_size': must be a positive integer")

    cw = data.get("column_width")
    if cw is not None and (not isinstance(cw, int) or not (200 <= cw <= 1920)):
        errors.append("'column_width': must be an integer between 200 and 1920")

    lw = data.get("logo_width")
    if lw is not None and (not isinstance(lw, int) or not (50 <= lw <= 1920)):
        errors.append("'logo_width': must be an integer between 50 and 1920")

    if "logo_h_align" in data and data["logo_h_align"] not in ("left", "center", "right"):
        errors.append("'logo_h_align': must be 'left', 'center', or 'right'")

    if "title_h_align" in data and data["title_h_align"] not in ("left", "center", "right"):
        errors.append("'title_h_align': must be 'left', 'center', or 'right'")

    if errors:
        label = f"theme '{filepath}'" if filepath else "theme"
        msg = f"Invalid {label}:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)


def load_theme(filepath: str | Path | None = None) -> Theme:
    """Load a theme JSON file with fallbacks to defaults.

    Args:
        filepath: Path to theme JSON. If None, returns the default theme.

    Returns:
        A Theme instance with all properties resolved.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the theme contains invalid property values.
    """
    if filepath is None:
        return Theme(
            name=DEFAULTS["name"],
            background_color=DEFAULTS["background_color"],
            text_color=DEFAULTS["text_color"],
            active_text_color=DEFAULTS["active_text_color"],
            active_text_bold=DEFAULTS["active_text_bold"],
            active_text_glow=DEFAULTS["active_text_glow"],
            active_glow_color=DEFAULTS["active_glow_color"],
            active_font_family=DEFAULTS["active_font_family"],
            active_text_stroke_color=DEFAULTS["active_text_stroke_color"],
            active_text_stroke_width=DEFAULTS["active_text_stroke_width"],
            inactive_text_opacity_gradient=list(DEFAULTS["inactive_text_opacity_gradient"]),
            font_family=DEFAULTS["font_family"],
            font_size=DEFAULTS["font_size"],
            line_spacing=DEFAULTS["line_spacing"],
            lyric_position=DEFAULTS["lyric_position"],
            highlight_mode=DEFAULTS["highlight_mode"],
            highlight_dim_alpha=DEFAULTS["highlight_dim_alpha"],
            text_overlay_opacity=DEFAULTS["text_overlay_opacity"],
            text_overlay_color=DEFAULTS["text_overlay_color"],
            text_position=DEFAULTS["text_position"],
            text_shadow=DEFAULTS["text_shadow"],
            text_shadow_color=DEFAULTS["text_shadow_color"],
            text_shadow_offset=list(DEFAULTS["text_shadow_offset"]),
            column_width=DEFAULTS["column_width"],
            logo_path=DEFAULTS["logo_path"],
            logo_width=DEFAULTS["logo_width"],
            logo_h_align=DEFAULTS["logo_h_align"],
            title_h_align=DEFAULTS["title_h_align"],
        )

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Theme file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    _validate_theme(data, filepath)

    # Backward-compat: map old property names to new ones
    if "glow_enabled" in data and "active_text_glow" not in data:
        data["active_text_glow"] = data["glow_enabled"]
    if "inactive_alphas" in data and "inactive_text_opacity_gradient" not in data:
        data["inactive_text_opacity_gradient"] = data["inactive_alphas"]
    if "line_height" in data and "line_spacing" not in data:
        font_size = data.get("font_size", DEFAULTS["font_size"])
        data["line_spacing"] = data["line_height"] / font_size

    merged = {**DEFAULTS, **data}

    return Theme(
        name=merged["name"],
        background_color=merged["background_color"],
        text_color=merged["text_color"],
        active_text_color=merged["active_text_color"],
        active_text_bold=merged["active_text_bold"],
        active_text_glow=merged["active_text_glow"],
        active_glow_color=merged["active_glow_color"],
        active_font_family=merged.get("active_font_family"),
        active_text_stroke_color=str(merged.get("active_text_stroke_color", DEFAULTS["active_text_stroke_color"])),
        active_text_stroke_width=int(merged.get("active_text_stroke_width", DEFAULTS["active_text_stroke_width"])),
        inactive_text_opacity_gradient=list(merged["inactive_text_opacity_gradient"]),
        font_family=merged["font_family"],
        font_size=merged["font_size"],
        line_spacing=merged["line_spacing"],
        lyric_position=merged["lyric_position"],
        highlight_mode=merged["highlight_mode"],
        highlight_dim_alpha=merged["highlight_dim_alpha"],
        text_overlay_opacity=merged["text_overlay_opacity"],
        text_overlay_color=merged["text_overlay_color"],
        text_position=merged["text_position"],
        text_shadow=merged["text_shadow"],
        text_shadow_color=merged["text_shadow_color"],
        text_shadow_offset=list(merged["text_shadow_offset"]),
        column_width=int(merged["column_width"]),
        logo_path=str(merged.get("logo_path", "")),
        logo_width=int(merged.get("logo_width", 400)),
        logo_h_align=str(merged.get("logo_h_align", "center")),
        title_h_align=str(merged.get("title_h_align", "center")),
    )
