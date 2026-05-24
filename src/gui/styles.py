"""Design tokens and global stylesheet for the OpenSea-inspired redesign."""

# ------------------------------------------------------------------------------
# Design Tokens
# ------------------------------------------------------------------------------

TOKENS = {
    # Colors
    "midnight_ink": "#080809",     # Page backgrounds
    "deep_graphite": "#141415",    # Main surfaces
    "slate_card": "#1b1d1f",       # Card backgrounds
    "steel_border": "#26272d",     # Subtle borders
    "soft_stone": "#34353c",       # Dark borders
    "ghost_fill": "#3c3d40",       # Subdued layers
    "white_canvas": "#ffffff",     # Primary text
    "silver_whisper": "#acadae",   # Secondary text
    "electric_blue": "#83c3ff",    # Accents
    "success_green": "#47bb64",    # Positive accent
    "error_red": "#e24756",        # Negative accent

    # Typography
    "font_primary": "'Inter', 'Segoe UI', 'Roboto', sans-serif",
    "font_mono": "'JetBrains Mono', 'Consolas', monospace",

    # Spacing & Shapes
    "radius_md": "4px",
    "radius_lg": "8px",
    "spacing_base": "4px",
}

# ------------------------------------------------------------------------------
# Global Stylesheet (QSS)
# ------------------------------------------------------------------------------

GLOBAL_STYLE = f"""
/* Global Reset and Base Styles */
* {{
    font-family: {TOKENS['font_primary']};
    color: {TOKENS['white_canvas']};
    background: transparent;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {TOKENS['midnight_ink']};
}}

QWidget {{
    font-size: 14px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: {TOKENS['midnight_ink']};
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {TOKENS['soft_stone']};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: {TOKENS['midnight_ink']};
    height: 8px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {TOKENS['soft_stone']};
    min-width: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Splitters */
QSplitter::handle {{
    background-color: {TOKENS['midnight_ink']};
}}

/* GroupBoxes as Inset Border Cards */
QGroupBox {{
    background-color: {TOKENS['deep_graphite']};
    border: 1px solid {TOKENS['steel_border']};
    border-radius: {TOKENS['radius_lg']};
    margin-top: 24px;
    padding: 8px;
    font-weight: 600;
    font-size: 14px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    top: 8px;
    color: {TOKENS['white_canvas']};
}}

/* Labels */
QLabel {{
    color: {TOKENS['white_canvas']};
}}

QLabel[secondary="true"] {{
    color: {TOKENS['silver_whisper']};
    font-size: 12px;
}}

/* Input Fields */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {TOKENS['slate_card']};
    border: 1px solid {TOKENS['steel_border']};
    border-radius: {TOKENS['radius_md']};
    padding: 4px 8px;
    color: {TOKENS['white_canvas']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {TOKENS['electric_blue']};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

/* Buttons */
QPushButton {{
    background-color: {TOKENS['soft_stone']};
    border: 1px solid {TOKENS['steel_border']};
    border-radius: {TOKENS['radius_md']};
    padding: 4px 8px;
    font-weight: 500;
    color: {TOKENS['white_canvas']};
}}

QPushButton:hover {{
    background-color: {TOKENS['ghost_fill']};
    border-color: {TOKENS['silver_whisper']};
}}

QPushButton:pressed {{
    background-color: {TOKENS['midnight_ink']};
}}

QPushButton:disabled {{
    color: {TOKENS['soft_stone']};
    background-color: transparent;
    border-color: {TOKENS['soft_stone']};
}}

/* Ghost Button Variant */
QPushButton[variant="ghost"] {{
    background-color: transparent;
    border: 1px solid {TOKENS['soft_stone']};
    color: {TOKENS['silver_whisper']};
}}
QPushButton[variant="ghost"]:hover {{
    border-color: {TOKENS['silver_whisper']};
    color: {TOKENS['white_canvas']};
}}

/* Primary Action Variant */
QPushButton[variant="primary"] {{
    background-color: transparent;
    border: 1px solid {TOKENS['electric_blue']};
    color: {TOKENS['electric_blue']};
}}
QPushButton[variant="primary"]:hover {{
    background-color: {TOKENS['electric_blue']};
    color: {TOKENS['midnight_ink']};
}}

/* List Widgets */
QListWidget {{
    background-color: {TOKENS['slate_card']};
    border: 1px solid {TOKENS['steel_border']};
    border-radius: {TOKENS['radius_lg']};
    outline: none;
}}

QListWidget::item {{
    padding: 12px;
    border-bottom: 1px solid {TOKENS['steel_border']};
}}

QListWidget::item:selected {{
    background-color: {TOKENS['deep_graphite']};
    color: {TOKENS['electric_blue']};
}}

/* Sliders */
QSlider::groove:horizontal {{
    border: 1px solid {TOKENS['steel_border']};
    height: 4px;
    background: {TOKENS['slate_card']};
    margin: 2px 0;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TOKENS['electric_blue']};
    border: 1px solid {TOKENS['electric_blue']};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

/* Checkboxes */
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    background-color: {TOKENS['slate_card']};
    border: 1px solid {TOKENS['steel_border']};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background-color: {TOKENS['electric_blue']};
    border-color: {TOKENS['electric_blue']};
    image: url(assets/check.png); /* Need to ensure this exists or use a vector */
}}
"""
