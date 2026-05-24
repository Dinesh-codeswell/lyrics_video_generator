export interface Theme {
  name: string;
  background_color: string;
  text_color: string;
  active_text_color: string;
  active_text_bold: boolean;
  active_text_glow: boolean;
  active_glow_color: string | null;
  active_font_family: string | null;
  active_text_stroke_color: string;
  active_text_stroke_width: number;
  inactive_text_opacity_gradient: number[];
  font_family: string;
  font_size: number;
  letter_spacing: number;
  line_spacing: number;
  lyric_position: 'left' | 'center' | 'right';
  highlight_mode: 'line' | 'word' | 'character';
  highlight_dim_alpha: number;
  text_overlay_opacity: number;
  text_overlay_color: string;
  column_width: number;
  logo_path: string;
  logo_width: number;
  logo_h_align: 'left' | 'center' | 'right';
  title_h_align: 'left' | 'center' | 'right';
  
  // Advanced Animation & Canvas
  animation_style: 'scroll' | 'fade' | 'slide' | 'kinetic' | 'typewriter';
  animation_speed: number; // 0.1 to 2.0 multiplier
  aspect_ratio: '16:9' | '9:16' | '1:1' | '4:5';
  fps: 24 | 30 | 60;
}

export interface LyricClip {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface Marker {
  time: number;
  text: string;
}

export const DEFAULTS: Theme = {
  name: "Default",
  background_color: "#1a1a1a",
  text_color: "#ffffff",
  active_text_color: "#D66E31",
  active_text_bold: false,
  active_text_glow: true,
  active_glow_color: null,
  active_font_family: null,
  active_text_stroke_color: "#6A1E22",
  active_text_stroke_width: 3,
  inactive_text_opacity_gradient: [0.6, 0.4, 0.2],
  font_family: "Arial",
  font_size: 72,
  letter_spacing: 0,
  line_spacing: 1.5,
  lyric_position: "center",
  highlight_mode: "line",
  highlight_dim_alpha: 0.3,
  text_overlay_opacity: 0,
  text_overlay_color: "#000000",
  column_width: 1760,
  logo_path: "",
  logo_width: 400,
  logo_h_align: "center",
  title_h_align: "center",
  
  // Animation Defaults
  animation_style: "scroll",
  animation_speed: 1.0,
  aspect_ratio: "16:9",
  fps: 30,
};
