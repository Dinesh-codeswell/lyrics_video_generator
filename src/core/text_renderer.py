"""Text and font rendering with Pillow."""

from PIL import Image, ImageDraw, ImageFont

from src.core.theme_loader import Theme

# Output resolution
WIDTH = 1920
HEIGHT = 1080

# Horizontal column layout
COLUMN_PADDING = 80  # px inset from screen edge for left/right positions


class TextRenderer:
    """Renders styled lyric text onto PIL Images using a Theme."""

    def __init__(self, theme: Theme):
        self.theme = theme
        self.font = self._load_font()
        self.bold_font = self._load_bold_font()
        self._logo: Image.Image | None = self._load_logo()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Load the theme font, falling back to default if unavailable."""
        try:
            return ImageFont.truetype(self.theme.font_family, self.theme.font_size)
        except OSError:
            # Try common system font paths
            for fallback in ("Arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
                try:
                    return ImageFont.truetype(fallback, self.theme.font_size)
                except OSError:
                    continue
            return ImageFont.load_default()

    def _load_bold_font(self) -> ImageFont.FreeTypeFont:
        """Load a bold font variant for active line rendering.

        If active_text_bold is False, or the base font is already bold,
        returns self.font unchanged.
        """
        if not self.theme.active_text_bold:
            return self.font
        # If font_family already contains "bold", it is already bold
        if "bold" in self.theme.font_family.lower():
            return self.font
        bold_name = self.theme.font_family + " Bold"
        try:
            return ImageFont.truetype(bold_name, self.theme.font_size)
        except OSError:
            return self.font

    def _get_font(self, is_active: bool = False) -> ImageFont.FreeTypeFont:
        """Return the appropriate font for the given line."""
        if is_active:
            return self.bold_font
        return self.font

    def _load_logo(self) -> "Image.Image | None":
        """Load and scale the theme logo image, returning None if unset or unreadable."""
        if not self.theme.logo_path:
            return None
        try:
            img = Image.open(self.theme.logo_path).convert("RGBA")
            w = self.theme.logo_width
            h = int(img.height * w / img.width)
            return img.resize((w, h), Image.LANCZOS)
        except Exception:
            return None

    def _composite_logo(self, img: Image.Image, screen_y: float, alpha: float) -> Image.Image:
        """Composite the cached logo onto img centered at screen_y with the given alpha."""
        logo = self._logo
        if logo is None:
            return img
        if int(alpha * 255) <= 0:
            return img
        r, g, b, orig_a = logo.split()
        scaled_a = orig_a.point(lambda p: int(p * alpha))
        logo_frame = Image.merge("RGBA", (r, g, b, scaled_a))
        lw, lh = logo_frame.size
        align = self.theme.logo_h_align
        if align == "left":
            px = COLUMN_PADDING
        elif align == "right":
            px = WIDTH - COLUMN_PADDING - lw
        else:  # center
            px = (WIDTH - lw) // 2
        # Anchor logo bottom at screen_y + line_height//2: consistent gap above the title
        # regardless of logo size (avoids overlap and avoids floating too far up).
        py = round(screen_y) - lh + self.theme.line_height // 2
        layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        layer.paste(logo_frame, (px, py))
        return Image.alpha_composite(img, layer)

    def render_frame(self, text: str, alpha: float = 1.0, y_offset: int = 0) -> Image.Image:
        """Render a single frame with the given text.

        Args:
            text: The lyric text to render.
            alpha: Opacity of the text (0.0 to 1.0), used by animations.
            y_offset: Vertical pixel offset from the base position (for slide animations).

        Returns:
            A 1920x1080 RGBA PIL Image.
        """
        bg_color = self.theme.background_color
        img = Image.new("RGBA", (WIDTH, HEIGHT), bg_color)

        if not text:
            return img

        x_h, anchor, align, col_w = self._get_horizontal_layout()

        # Wrap long lines
        wrapped = self._wrap_text(text, col_w)

        # Create a transparent overlay for text (supports alpha)
        txt_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)

        # Vertical position
        x = x_h
        y = self._compute_vertical_position()
        y += y_offset

        # Convert alpha to 0-255
        a = int(alpha * 255)

        # Draw shadow if enabled
        if self.theme.text_shadow:
            sx, sy = self.theme.text_shadow_offset
            shadow_color = self._hex_to_rgba(self.theme.text_shadow_color, a)
            draw.multiline_text(
                (x + sx, y + sy), wrapped, font=self.font,
                fill=shadow_color, anchor=anchor, align=align,
            )

        # Draw main text
        text_color = self._hex_to_rgba(self.theme.text_color, a)
        draw.multiline_text(
            (x, y), wrapped, font=self.font,
            fill=text_color, anchor=anchor, align=align,
        )

        return Image.alpha_composite(img, txt_layer)

    def render_scroll_frame(self, lines_data: list[dict], background: Image.Image | None = None) -> Image.Image:
        """Render multiple lyric lines for the scrolling view.

        Args:
            lines_data: List of dicts with keys:
                - 'text': str
                - 'screen_y': float  (center y position on screen)
                - 'alpha': float     (0.0 – 1.0)
                - 'is_active': bool
                - 'highlight_progress': float  (0.0 – 1.0, for word/char modes)
            background: Optional pre-scaled 1920×1080 RGBA PIL Image to use
                as the background instead of the solid theme color.

        Returns:
            A 1920x1080 RGBA PIL Image.
        """
        if background is not None:
            img = background.convert("RGBA")
        else:
            img = Image.new("RGBA", (WIDTH, HEIGHT), self.theme.background_color)

        x, anchor, align, col_w = self._get_horizontal_layout()
        highlight_mode = self.theme.highlight_mode

        for line_data in lines_data:
            text = line_data.get("text", "")
            screen_y = line_data["screen_y"]
            alpha = line_data["alpha"]

            if text == "__LOGO__":
                img = self._composite_logo(img, screen_y, alpha)
                continue
            if not text:
                continue

            is_active = line_data.get("is_active", False)
            highlight_progress = line_data.get("highlight_progress", 0.0)

            font = self._get_font(is_active)
            wrapped = self._wrap_text(text, col_w, font=font)
            a = int(alpha * 255)
            y = round(screen_y)

            txt_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt_layer)

            # Soft glow for active line
            if is_active and self.theme.active_text_glow:
                glow_a = int(alpha * 38)  # ~15% opacity
                glow_color = self._hex_to_rgba(self.theme.effective_active_glow_color, glow_a)
                for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
                    draw.multiline_text(
                        (x + dx, y + dy), wrapped, font=font,
                        fill=glow_color, anchor=anchor, align=align,
                    )

            # Shadow
            if self.theme.text_shadow:
                sx, sy = self.theme.text_shadow_offset
                shadow_color = self._hex_to_rgba(self.theme.text_shadow_color, a)
                draw.multiline_text(
                    (x + sx, y + sy), wrapped, font=font,
                    fill=shadow_color, anchor=anchor, align=align,
                )

            # Main text — use token-level highlighting for active line in word/char mode
            if is_active and highlight_mode in ("word", "character"):
                self._render_highlighted_tokens(
                    draw, wrapped, y, alpha, highlight_progress, highlight_mode, font,
                )
            else:
                color = self.theme.effective_active_text_color if is_active else self.theme.text_color
                text_color = self._hex_to_rgba(color, a)
                draw.multiline_text(
                    (x, y), wrapped, font=font,
                    fill=text_color, anchor=anchor, align=align,
                )

            img = Image.alpha_composite(img, txt_layer)

        return img

    def _render_highlighted_tokens(
        self,
        draw: ImageDraw.ImageDraw,
        wrapped_text: str,
        y: int,
        alpha: float,
        progress: float,
        mode: str,
        font: ImageFont.FreeTypeFont | None = None,
    ) -> None:
        """Render text with progressive word- or character-level highlighting.

        Tokens up to ``progress * total_tokens`` are drawn at full alpha;
        the remaining tokens are drawn at ``highlight_dim_alpha`` opacity.

        Args:
            draw: PIL ImageDraw instance for the current text layer.
            wrapped_text: Line text, possibly containing \\n (from _wrap_text).
            y: Vertical center of the full text block in pixels.
            alpha: Overall line opacity (0.0 – 1.0).
            progress: Fraction of the line's duration elapsed (0.0 – 1.0).
            mode: ``"word"`` or ``"character"``.
            font: Font to use; defaults to self.font.
        """
        if font is None:
            font = self.font

        display_lines = wrapped_text.split("\n")
        n_lines = len(display_lines)
        pos = self.theme.lyric_position

        a_full = int(alpha * 255)
        dim_frac = self.theme.highlight_dim_alpha
        a_dim = int(alpha * dim_frac * 255)
        color_full = self._hex_to_rgba(self.theme.effective_active_text_color, a_full)
        color_dim = self._hex_to_rgba(self.theme.text_color, a_dim)

        # Count all tokens across every display line to set the threshold.
        total_tokens = 0
        for dl in display_lines:
            total_tokens += len(dl.split()) if mode == "word" else len(dl)
        if total_tokens == 0:
            return
        threshold = progress * total_tokens  # tokens with index < threshold are lit

        # Font metrics for vertical positioning of individual wrapped lines.
        try:
            ascent, descent = font.getmetrics()
        except AttributeError:
            ascent = self.theme.font_size
            descent = int(self.theme.font_size * 0.2)
        char_height = ascent + descent
        spacing = 4  # PIL default line spacing
        line_h = char_height + spacing
        # With anchor="mm" the block is centered at y.
        # Block top = y - total_block_height / 2
        total_block_height = n_lines * char_height + max(0, n_lines - 1) * spacing
        block_top = y - total_block_height / 2.0

        token_idx = 0
        for i, display_line in enumerate(display_lines):
            if not display_line:
                continue

            # Vertical center of this display line.
            line_center_y = block_top + char_height / 2.0 + i * line_h

            # Build token strings for this line.
            if mode == "word":
                words = display_line.split()
                token_strs = [
                    w + (" " if j < len(words) - 1 else "")
                    for j, w in enumerate(words)
                ]
            else:  # character
                token_strs = list(display_line)

            # Starting x: replicate the alignment logic using per-line width.
            try:
                line_width = font.getlength(display_line)
            except AttributeError:
                line_width, _ = font.getsize(display_line)  # type: ignore[attr-defined]

            if pos == "left":
                x_cursor = float(COLUMN_PADDING)
            elif pos == "right":
                x_cursor = float(WIDTH - COLUMN_PADDING - line_width)
            else:  # center
                x_cursor = WIDTH / 2.0 - line_width / 2.0

            for token_str in token_strs:
                color = color_full if token_idx < threshold else color_dim
                draw.text(
                    (x_cursor, line_center_y),
                    token_str,
                    font=font,
                    fill=color,
                    anchor="lm",
                )
                try:
                    token_width = font.getlength(token_str)
                except AttributeError:
                    token_width, _ = font.getsize(token_str)  # type: ignore[attr-defined]
                x_cursor += token_width
                token_idx += 1

    def _get_horizontal_layout(self) -> tuple[int, str, str, int]:
        """Return (x, anchor, align, col_w) based on theme lyric_position."""
        pos = self.theme.lyric_position
        col_w = self.theme.column_width

        if pos == "left":
            return COLUMN_PADDING, "lm", "left", col_w
        elif pos == "right":
            return WIDTH - COLUMN_PADDING, "rm", "right", col_w
        else:  # center (default)
            return WIDTH // 2, "mm", "center", col_w

    def _wrap_text(self, text: str, max_px: int, font=None) -> str:
        """Wrap text so no line exceeds max_px pixels wide."""
        f = font or self.font
        words = text.split()
        if not words:
            return text
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            try:
                width = f.getlength(candidate)
            except AttributeError:
                width, _ = f.getsize(candidate)  # type: ignore[attr-defined]
            if width <= max_px:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return "\n".join(lines)

    def _compute_vertical_position(self) -> int:
        """Return the vertical anchor y based on theme text_position."""
        pos = self.theme.text_position
        if pos == "top":
            return HEIGHT // 4
        elif pos == "bottom":
            return (HEIGHT * 3) // 4
        else:  # center (default)
            return HEIGHT // 2

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
        """Convert a hex color string to an RGBA tuple."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b, alpha)
