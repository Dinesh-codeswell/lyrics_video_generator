import React, { useState, useEffect, useRef } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { Save, Undo, Redo, Download, HelpCircle, Maximize } from 'lucide-react';
import { SongSelector } from '../components/dashboard/SongSelector';
import { ThemeEditor } from '../components/dashboard/ThemeEditor';
import { WebTimeline } from '../components/dashboard/WebTimeline';
import { DEFAULTS } from '../types';
import type { Theme, LyricClip } from '../types';
import './Dashboard.css';

// Environment-aware API URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const Dashboard: React.FC = () => {
  const [selectedSong, setSelectedSong] = useState<string | null>(null);
  const [songPaths, setSongPaths] = useState<any>(null);
  const [clips, setClips] = useState<LyricClip[]>([]);
  const [theme, setTheme] = useState<Theme>(DEFAULTS);
  const [currentTime, setCurrentTime] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const [renderProgress, setRenderProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [songMetadata, setSongMetadata] = useState({ title: '', artist: '' });
  const [apiError, setApiError] = useState<string | null>(null);
  const bgVideoRef = useRef<HTMLVideoElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  // Dynamic Scaling State
  const [previewDimensions, setPreviewDimensions] = useState({ width: 0, height: 0 });
  const previewScale = previewDimensions.width / 1920 || 0.5;
  const stageHeight = previewDimensions.height || 540;
  const lineHeight = 240 * previewScale;

  useEffect(() => {
    if (!stageRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setPreviewDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });
    observer.observe(stageRef.current);
    return () => observer.disconnect();
  }, []);

  const toggleFullScreen = () => {
    if (stageRef.current) {
      if (!document.fullscreenElement) {
        stageRef.current.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    }
  };

  // Determine active lyric index (for highlighting ONLY)
  const activeIndex = React.useMemo(() => {
    if (!clips.length) return -1;
    return clips.findIndex(clip => 
      currentTime >= clip.start_time && currentTime < clip.end_time
    );
  }, [currentTime, clips]);

  // Find the index of the lyric that started most recently (for scrolling continuity)
  const lastStartedIndex = React.useMemo(() => {
    if (!clips.length) return -1;
    for (let i = clips.length - 1; i >= 0; i--) {
      if (currentTime >= clips[i].start_time) return i;
    }
    return 0;
  }, [currentTime, clips]);

  // Calculate smooth interpolation for continuous scrolling
  const scrollOffset = React.useMemo(() => {
    if (clips.length === 0) return 0;
    
    if (lastStartedIndex === -1 || (lastStartedIndex === 0 && currentTime < clips[0].start_time)) {
       return 0;
    }

    const i = lastStartedIndex;
    if (i >= clips.length - 1) return i * lineHeight;

    const currentClip = clips[i];
    const nextClip = clips[i + 1];
    const totalGap = nextClip.start_time - currentClip.start_time;
    
    if (totalGap <= 0) return i * lineHeight;

    const progress = (currentTime - currentClip.start_time) / totalGap;
    return (i + progress) * lineHeight;
  }, [currentTime, clips, lastStartedIndex, lineHeight]);

  // Logic to get visible lines
  const visibleLines = React.useMemo(() => {
    if (!selectedSong || !clips.length) return [];
    
    const centerIdx = lastStartedIndex >= 0 ? lastStartedIndex : 0;
    const range = 8;
    const start = Math.max(0, centerIdx - 4);
    const end = Math.min(clips.length, centerIdx + range);
    
    const lines = [];
    for (let i = start; i < end; i++) {
      lines.push({
        ...clips[i],
        index: i,
        y: i * lineHeight 
      });
    }
    return lines;
  }, [selectedSong, clips, lastStartedIndex, lineHeight]);

  // --- Animation Helpers ---
  const getLineStyles = (isCurrent: boolean, currentTheme: Theme): React.CSSProperties => ({
    fontSize: `${currentTheme.font_size * previewScale}px`, 
    color: isCurrent && currentTheme.highlight_mode === 'line' ? currentTheme.active_text_color : currentTheme.text_color,
    fontFamily: currentTheme.font_family,
    textAlign: currentTheme.lyric_position,
    fontWeight: (isCurrent && currentTheme.active_text_bold) ? 'bold' : 'normal',
    textShadow: (isCurrent && currentTheme.active_text_glow) ? `0 0 ${20 * previewScale}px ${currentTheme.active_glow_color || currentTheme.active_text_color}` : 'none',
    WebkitTextStroke: isCurrent ? `${currentTheme.active_text_stroke_width * previewScale}px ${currentTheme.active_text_stroke_color}` : 'none',
    letterSpacing: `${currentTheme.letter_spacing * previewScale}px`,
    maxWidth: `${currentTheme.column_width * previewScale}px`,
    width: '100%',
    padding: `0 ${40 * previewScale}px`,
  });

  const renderLineText = (line: LyricClip, isCurrent: boolean, currentTheme: Theme, time: number, activeClip: LyricClip) => {
    if (!isCurrent) return line.text;

    // Typewriter Logic
    if (currentTheme.animation_style === 'typewriter') {
      const dur = activeClip.end_time - activeClip.start_time;
      const prog = Math.max(0, Math.min(1, (time - activeClip.start_time) / dur));
      const charCount = Math.floor(line.text.length * prog);
      return line.text.substring(0, charCount);
    }

    // Word/Character Highlights
    if (currentTheme.highlight_mode === 'word' || currentTheme.highlight_mode === 'character') {
      const dur = activeClip.end_time - activeClip.start_time;
      const progress = Math.max(0, Math.min(1, (time - activeClip.start_time) / dur));
      
      if (currentTheme.highlight_mode === 'word') {
          const words = line.text.split(' ');
          const activeWordIdx = Math.floor(progress * words.length);
          return words.map((w, i) => (
              <span key={i} style={{ color: i <= activeWordIdx ? currentTheme.active_text_color : currentTheme.text_color }}>
                  {w}{' '}
              </span>
          ));
      } else if (currentTheme.highlight_mode === 'character') {
          const chars = line.text.split('');
          const activeCharIdx = Math.floor(progress * chars.length);
          return chars.map((c, i) => (
              <span key={i} style={{ color: i <= activeCharIdx ? currentTheme.active_text_color : currentTheme.text_color }}>
                  {c}
              </span>
          ));
      }
    }

    return line.text;
  };

  useEffect(() => {
    const checkApi = async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/songs`);
        if (resp.ok) setApiError(null);
      } catch {
        setApiError('Backend server unreachable. Please start the API using .\\venv\\Scripts\\python.exe -m src.api.main');
      }
    };
    checkApi();
    const interval = setInterval(checkApi, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSongSelect = async (slug: string) => {
    setSelectedSong(slug);
    try {
      // 1. Get file paths
      const resp = await fetch(`${API_BASE_URL}/api/songs/${slug}`);
      const paths = await resp.json();
      setSongPaths(paths);

      // 2. Fetch and parse lyrics into Clips (Auto-embedding)
      if (paths.lyrics) {
        const lyrResp = await fetch(`${API_BASE_URL}/api/download_raw?path=${paths.lyrics}`);
        const lyrData = await lyrResp.json();
        setSongMetadata({
          title: lyrData.title || slug,
          artist: lyrData.artist || 'Unknown Artist'
        });
        
        if (lyrData.lyrics && Array.isArray(lyrData.lyrics)) {
          const rawLyrics = lyrData.lyrics;
          const newClips: LyricClip[] = [];

          for (let i = 0; i < rawLyrics.length; i++) {
            const current = rawLyrics[i];
            if (current.text === "") continue;

            let startTime = current.time;
            if (i > 0 && startTime <= newClips[newClips.length - 1].start_time) {
              startTime = newClips[newClips.length - 1].end_time + 0.5;
            }

            let endTime = startTime + 2.0;
            if (i + 1 < rawLyrics.length) {
              const nextTime = rawLyrics[i + 1].time;
              if (nextTime > startTime) {
                endTime = nextTime;
              }
            }

            newClips.push({
              id: `clip-${i}-${Math.random().toString(36).substr(2, 9)}`,
              start_time: startTime,
              end_time: endTime,
              text: current.text
            });
          }
          setClips(newClips);
        }
      }

      // 3. Load theme if exists
      if (paths.theme) {
        const themeResp = await fetch(`${API_BASE_URL}/api/download_raw?path=${paths.theme}`);
        const themeData = await themeResp.json();
        setTheme({ ...DEFAULTS, ...themeData });
      } else {
        setTheme(DEFAULTS);
      }
    } catch {
      console.error('Failed to load song details');
    }
  };

  const handleBackgroundUpdate = async (file: File) => {
    if (!selectedSong) return;
    try {
      const formData = new FormData();
      formData.append('slug', selectedSong);
      formData.append('background', file);
      
      const resp = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (resp.ok) {
        // Refresh song paths to show new background in preview
        const pathsResp = await fetch(`${API_BASE_URL}/api/songs/${selectedSong}`);
        const paths = await pathsResp.json();
        setSongPaths(paths);
      }
    } catch {
      console.error('Failed to update background');
    }
  };

  useEffect(() => {
    const handleNleUpload = (e: any) => handleBackgroundUpdate(e.detail);
    window.addEventListener('nle-bg-upload', handleNleUpload);
    return () => window.removeEventListener('nle-bg-upload', handleNleUpload);
  }, [selectedSong]);

  const handleExport = async () => {
    if (!selectedSong) return;
    setIsExporting(true);
    setRenderProgress(0);
    setJobId(null);
    try {
      const resp = await fetch(`${API_BASE_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          song_slug: selectedSong,
          theme: theme,
          fps: 30
        }),
      });
      const data = await resp.json();
      setJobId(data.job_id);
      
      const poll = setInterval(async () => {
        try {
          const statusResp = await fetch(`${API_BASE_URL}/api/status/${data.job_id}`);
          const statusData = await statusResp.json();
          
          setRenderProgress(statusData.progress || 0);

          if (statusData.status === 'completed' || statusData.status === 'failed') {
            clearInterval(poll);
            setIsExporting(false);
            if (statusData.status === 'failed') alert('Export failed: ' + statusData.error);
          }
        } catch {
          console.error('Polling failed');
        }
      }, 1000);
    } catch {
      console.error('Export failed');
      setIsExporting(false);
    }
  };

  const handleSaveLyrics = async () => {
    if (!selectedSong || !songPaths?.lyrics) return;
    const payload = {
      title: songMetadata.title,
      artist: songMetadata.artist,
      lyrics: clips.map(c => ({ time: c.start_time, text: c.text })),
      theme: theme
    };
    if (clips.length > 0) {
      payload.lyrics.push({ time: clips[clips.length - 1].end_time, text: "" });
    }

    try {
      const formData = new FormData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      formData.append('lyrics', blob, `${selectedSong}.json`);
      formData.append('slug', selectedSong);
      
      await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
      });
      alert('Lyrics and Theme saved successfully');
    } catch {
      console.error('Failed to save lyrics');
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <Link to="/" className="dashboard-brand">
            <span className="text-accent">LV</span> Gen
          </Link>
          <div className="divider"></div>
          <div className="song-title-display">
            {selectedSong ? `${songMetadata.artist} - ${songMetadata.title}` : 'Select a Song'}
          </div>
        </div>
        <div className="header-right">
          <div className="toolbar-group">
            <Button variant="ghost" size="sm" onClick={handleSaveLyrics} disabled={!selectedSong}>
              <Save size={14} /> Save
            </Button>
            <Button variant="ghost" size="sm" disabled={!selectedSong}>
              <Undo size={14} />
            </Button>
            <Button variant="ghost" size="sm" disabled={!selectedSong}>
              <Redo size={14} />
            </Button>
          </div>
          <div className="divider"></div>
          <Button 
            variant="primary" 
            size="sm" 
            onClick={handleExport}
            disabled={!selectedSong || isExporting}
          >
            {isExporting ? `Generating (${renderProgress}%)` : 'Export Video'}
          </Button>
          {jobId && !isExporting && (
            <a href={`${API_BASE_URL}/api/download/${jobId}`} download>
              <Button variant="ghost" size="sm" className="success-btn"><Download size={14} /> Download</Button>
            </a>
          )}
        </div>
      </header>

      {apiError && (
        <div className="api-error-banner">
          <HelpCircle size={16} />
          <span>{apiError}</span>
        </div>
      )}

      <div className="dashboard-layout">
        <aside className="sidebar left-sidebar">
          <Card title="Project Library" className="panel-card">
            <SongSelector onSelect={handleSongSelect} />
          </Card>
        </aside>

        <main className="dashboard-main">
          <div className="top-row">
            <div className="preview-area">
              <Card 
                title="Live Preview" 
                className="panel-card preview-card"
                headerActions={
                  <Button variant="ghost" size="sm" onClick={toggleFullScreen} title="Fullscreen Preview">
                    <Maximize size={14} />
                  </Button>
                }
              >
                  <div 
                    ref={stageRef}
                    className="preview-stage" 
                    style={{ 
                      backgroundColor: theme.background_color,
                      aspectRatio: theme.aspect_ratio.replace(':', '/'),
                      maxHeight: '100%'
                    }}
                  >
                    {/* Background Video */}
                    {songPaths?.background && (
                      <video 
                        ref={bgVideoRef}
                        src={`${API_BASE_URL}/api/download_raw?path=${songPaths.background}`}
                        autoPlay 
                        loop 
                        muted 
                        className="preview-bg-video"
                      />
                    )}

                    {/* Background Overlay */}
                    <div 
                      className="preview-overlay" 
                      style={{ 
                        backgroundColor: theme.text_overlay_color,
                        opacity: theme.text_overlay_opacity / 100 
                      }} 
                    />

                    {/* Logo Section */}
                    {theme.logo_path && (
                      <div className="preview-logo-container" style={{ textAlign: theme.logo_h_align }}>
                        <img 
                          src={`${API_BASE_URL}/api/download_raw?path=${theme.logo_path}`} 
                          alt="Logo"
                          style={{ width: `${theme.logo_width / 4}px`, height: 'auto' }}
                          onError={(e) => (e.currentTarget.style.display = 'none')}
                        />
                      </div>
                    )}

                    {/* Cinematic Animation Engine */}
                    <div className="preview-lyrics-container">
                      {theme.animation_style === 'scroll' ? (
                        <div 
                          className="preview-scroller-inner"
                          style={{ 
                            transform: `translateY(${(stageHeight / 2) - scrollOffset}px)`,
                            transition: `transform ${0.3 / theme.animation_speed}s linear`
                          }}
                        >
                          {visibleLines.map((line) => {
                            const isCurrent = line.index === activeIndex;
                            const gradIdx = Math.abs(line.index - activeIndex) - 1;
                            const opacity = isCurrent ? 1 : (theme.inactive_text_opacity_gradient[gradIdx] ?? 0.1);
                            
                            return (
                              <div key={line.id} className="preview-text-wrapper" style={{ top: `${line.y}px`, transform: 'translateY(-50%)', opacity }}>
                                <div className="preview-text" style={getLineStyles(isCurrent, theme)}>
                                  {renderLineText(line, isCurrent, theme, currentTime, clips[activeIndex])}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className={`preview-static-stage ${theme.animation_style}`}>
                          {clips[activeIndex] && (
                            <div 
                              key={clips[activeIndex].id} 
                              className="animate-current-line"
                              style={{
                                ...getLineStyles(true, theme),
                                animationDuration: `${0.5 / theme.animation_speed}s`
                              }}
                            >
                              {renderLineText(clips[activeIndex], true, theme, currentTime, clips[activeIndex])}
                            </div>
                          )}
                        </div>
                      )}
                      
                      {!selectedSong && (
                        <div className="preview-placeholder">Load a song to see preview</div>
                      )}
                    </div>

                    {/* Export Progress Overlay */}
                    {isExporting && (
                      <div className="export-progress-overlay">
                        <div className="progress-container">
                          <div className="progress-label">RENDERING VIDEO... {renderProgress}%</div>
                          <div className="progress-track">
                            <div className="progress-fill" style={{ width: `${renderProgress}%` }} />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
              </Card>
            </div>
            
            <aside className="sidebar right-sidebar">
              <Card title="Theme Editor" className="panel-card scrollable">
                <ThemeEditor theme={theme} onChange={setTheme} />
              </Card>
            </aside>
          </div>

          <div className="timeline-area">
             <Card title="Professional Video Editor" className="panel-card timeline-card">
                <WebTimeline 
                  audioUrl={songPaths?.audio ? `${API_BASE_URL}/api/download_raw?path=${songPaths.audio}` : undefined}
                  bgUrl={songPaths?.background ? `${API_BASE_URL}/api/download_raw?path=${songPaths.background}` : undefined}
                  clips={clips}
                  onClipChange={setClips}
                  onTimeUpdate={setCurrentTime}
                />
             </Card>
          </div>
        </main>
      </div>
    </div>
  );
};
