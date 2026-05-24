import React from 'react';
import type { Theme } from '../../types';
import './ThemeEditor.css';

interface ThemeEditorProps {
  theme: Theme;
  onChange: (theme: Theme) => void;
}

export const ThemeEditor: React.FC<ThemeEditorProps> = ({ theme, onChange }) => {
  const handleChange = (key: keyof Theme, value: any) => {
    onChange({ ...theme, [key]: value });
  };

  const handleGradientChange = (index: number, value: number) => {
    const newGrad = [...theme.inactive_text_opacity_gradient];
    newGrad[index] = value;
    handleChange('inactive_text_opacity_gradient', newGrad);
  };

  return (
    <div className="theme-editor">
      {/* Background Section */}
      <div className="editor-section">
        <label className="section-label">Background</label>
        <div className="control-row">
          <span>Main Color</span>
          <input type="color" value={theme.background_color} onChange={(e) => handleChange('background_color', e.target.value)} />
        </div>
        <div className="control-row">
          <span>Overlay %</span>
          <input type="range" min="0" max="100" value={theme.text_overlay_opacity} onChange={(e) => handleChange('text_overlay_opacity', parseInt(e.target.value))} />
          <span className="value-label">{theme.text_overlay_opacity}%</span>
        </div>
        <div className="control-row">
          <span>Overlay Color</span>
          <input type="color" value={theme.text_overlay_color} onChange={(e) => handleChange('text_overlay_color', e.target.value)} />
        </div>
      </div>

      {/* Text Section */}
      <div className="editor-section">
        <label className="section-label">General Text</label>
        <div className="control-row">
          <span>Font</span>
          <select value={theme.font_family} onChange={(e) => handleChange('font_family', e.target.value)}>
            <option value="Arial">Arial</option>
            <option value="Inter">Inter</option>
            <option value="Roboto">Roboto</option>
            <option value="JetBrains Mono">JetBrains Mono</option>
          </select>
        </div>
        <div className="control-row">
          <span>Size</span>
          <input type="range" min="24" max="144" value={theme.font_size} onChange={(e) => handleChange('font_size', parseInt(e.target.value))} />
          <span className="value-label">{theme.font_size}px</span>
        </div>
        <div className="control-row">
          <span>Spacing</span>
          <input type="range" min="1.0" max="3.0" step="0.1" value={theme.line_spacing} onChange={(e) => handleChange('line_spacing', parseFloat(e.target.value))} />
          <span className="value-label">{theme.line_spacing}</span>
        </div>
        <div className="control-row">
          <span>Letter Spacing</span>
          <input type="range" min="-10" max="50" step="1" value={theme.letter_spacing} onChange={(e) => handleChange('letter_spacing', parseInt(e.target.value))} />
          <span className="value-label">{theme.letter_spacing}px</span>
        </div>
        <div className="control-row">
          <span>Color</span>
          <input type="color" value={theme.text_color} onChange={(e) => handleChange('text_color', e.target.value)} />
        </div>
      </div>

      {/* Active Line Section */}
      <div className="editor-section">
        <label className="section-label">Active Line</label>
        <div className="control-row">
          <span>Fill Color</span>
          <input type="color" value={theme.active_text_color} onChange={(e) => handleChange('active_text_color', e.target.value)} />
        </div>
        <div className="control-row">
          <span>Style</span>
          <label className="checkbox-label">
            <input type="checkbox" checked={theme.active_text_bold} onChange={(e) => handleChange('active_text_bold', e.target.checked)} />
            Bold
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={theme.active_text_glow} onChange={(e) => handleChange('active_text_glow', e.target.checked)} />
            Glow
          </label>
        </div>
        {theme.active_text_glow && (
          <div className="control-row">
            <span>Glow Color</span>
            <input type="color" value={theme.active_glow_color || theme.active_text_color} onChange={(e) => handleChange('active_glow_color', e.target.value)} />
          </div>
        )}
        <div className="control-row">
          <span>Stroke Color</span>
          <input type="color" value={theme.active_text_stroke_color} onChange={(e) => handleChange('active_text_stroke_color', e.target.value)} />
        </div>
        <div className="control-row">
          <span>Stroke Width</span>
          <input type="range" min="0" max="20" value={theme.active_text_stroke_width} onChange={(e) => handleChange('active_text_stroke_width', parseInt(e.target.value))} />
          <span className="value-label">{theme.active_text_stroke_width}px</span>
        </div>
      </div>

      {/* Inactive Lines Section */}
      <div className="editor-section">
        <label className="section-label">Inactive Opacity</label>
        {theme.inactive_text_opacity_gradient.map((val, i) => (
          <div key={i} className="control-row">
            <span>Line ±{i + 1}</span>
            <input type="range" min="0" max="1" step="0.05" value={val} onChange={(e) => handleGradientChange(i, parseFloat(e.target.value))} />
            <span className="value-label">{Math.round(val * 100)}%</span>
          </div>
        ))}
      </div>

      {/* Layout Section */}
      <div className="editor-section">
        <label className="section-label">Layout</label>
        <div className="control-row">
          <span>Alignment</span>
          <select value={theme.lyric_position} onChange={(e) => handleChange('lyric_position', e.target.value)}>
            <option value="left">Left</option>
            <option value="center">Center</option>
            <option value="right">Right</option>
          </select>
        </div>
        <div className="control-row">
          <span>Highlight</span>
          <select value={theme.highlight_mode} onChange={(e) => handleChange('highlight_mode', e.target.value)}>
            <option value="line">Line</option>
            <option value="word">Word</option>
            <option value="character">Character</option>
          </select>
        </div>
        <div className="control-row">
          <span>Column Width</span>
          <input type="range" min="200" max="1920" step="10" value={theme.column_width} onChange={(e) => handleChange('column_width', parseInt(e.target.value))} />
          <span className="value-label">{theme.column_width}px</span>
        </div>
      </div>

      {/* Logo Section */}
      <div className="editor-section">
        <label className="section-label">Logo / Intro</label>
        <div className="control-row">
          <span>Logo Path</span>
          <input type="text" value={theme.logo_path} placeholder="assets/logo.png" onChange={(e) => handleChange('logo_path', e.target.value)} className="text-input" />
        </div>
        <div className="control-row">
          <span>Logo Width</span>
          <input type="range" min="50" max="1000" step="10" value={theme.logo_width} onChange={(e) => handleChange('logo_width', parseInt(e.target.value))} />
          <span className="value-label">{theme.logo_width}px</span>
        </div>
        <div className="control-row">
          <span>Logo Align</span>
          <select value={theme.logo_h_align} onChange={(e) => handleChange('logo_h_align', e.target.value)}>
            <option value="left">Left</option>
            <option value="center">Center</option>
            <option value="right">Right</option>
          </select>
        </div>
        <div className="control-row">
          <span>Title Align</span>
          <select value={theme.title_h_align} onChange={(e) => handleChange('title_h_align', e.target.value)}>
            <option value="left">Left</option>
            <option value="center">Center</option>
            <option value="right">Right</option>
          </select>
        </div>
      </div>

      {/* Animation & Canvas Section */}
      <div className="editor-section">
        <label className="section-label">Animation & Canvas</label>
        <div className="control-row">
          <span>Style</span>
          <select value={theme.animation_style} onChange={(e) => handleChange('animation_style', e.target.value)}>
            <option value="scroll">Scroll (Cinematic)</option>
            <option value="fade">Fade (Minimalist)</option>
            <option value="slide">Slide (Dynamic)</option>
            <option value="kinetic">Kinetic (Pop)</option>
            <option value="typewriter">Typewriter (Glitch)</option>
          </select>
        </div>
        <div className="control-row">
          <span>Speed</span>
          <input type="range" min="0.2" max="3.0" step="0.1" value={theme.animation_speed} onChange={(e) => handleChange('animation_speed', parseFloat(e.target.value))} />
          <span className="value-label">{theme.animation_speed}x</span>
        </div>
        <div className="control-row">
          <span>Aspect Ratio</span>
          <select value={theme.aspect_ratio} onChange={(e) => handleChange('aspect_ratio', e.target.value)}>
            <option value="16:9">16:9 (YouTube)</option>
            <option value="9:16">9:16 (TikTok/Shorts)</option>
            <option value="4:5">4:5 (Instagram)</option>
            <option value="1:1">1:1 (Square)</option>
          </select>
        </div>
        <div className="control-row">
          <span>FPS Target</span>
          <select value={theme.fps} onChange={(e) => handleChange('fps', parseInt(e.target.value))}>
            <option value={24}>24 (Cinematic)</option>
            <option value={30}>30 (Standard)</option>
            <option value={60}>60 (Ultra-smooth)</option>
          </select>
        </div>
      </div>
    </div>
  );
};
