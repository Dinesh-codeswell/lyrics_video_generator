import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause, SkipBack, ChevronLeft, ChevronRight, Plus, Video, Scissors } from 'lucide-react';
import { Button } from '../ui/Button';
import type { LyricClip } from '../../types';
import './WebTimeline.css';

interface WebTimelineProps {
  audioUrl?: string;
  bgUrl?: string;
  clips: LyricClip[];
  onClipChange: (clips: LyricClip[]) => void;
  onTimeUpdate: (time: number) => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// Helper Components
// ──────────────────────────────────────────────────────────────────────────────

const TimelineRuler: React.FC<{ duration: number; zoom: number }> = ({ duration, zoom }) => {
  const ticks = [];
  // Decide tick frequency based on zoom
  let majorTickFreq = 5; // seconds
  if (zoom > 150) majorTickFreq = 1;
  if (zoom > 300) majorTickFreq = 0.5;
  if (zoom < 50) majorTickFreq = 10;

  for (let t = 0; t <= duration; t += majorTickFreq) {
    ticks.push(
      <div key={t} className="ruler-tick major" style={{ left: `${t * zoom}px` }}>
        <span className="ruler-label">
          {Math.floor(t / 60)}:{Math.floor(t % 60).toString().padStart(2, '0')}{t % 1 !== 0 ? `.${Math.floor((t % 1) * 10)}` : ''}
        </span>
      </div>
    );
    
    if (zoom > 100) {
      const minorT = t + (majorTickFreq / 2);
      if (minorT <= duration) {
        ticks.push(
          <div key={`m-${minorT}`} className="ruler-tick minor" style={{ left: `${minorT * zoom}px` }}></div>
        );
      }
    }
  }

  return <div className="timeline-ruler">{ticks}</div>;
};

const EditLyricModal: React.FC<{
  initialText: string;
  onSave: (text: string) => void;
  onCancel: () => void;
  title: string;
}> = ({ initialText, onSave, onCancel, title }) => {
  const [text, setText] = useState(initialText);
  return (
    <div className="lyric-modal-overlay">
      <div className="lyric-modal">
        <h3>{title}</h3>
        <textarea 
          autoFocus
          value={text} 
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter lyric text..."
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSave(text);
            }
          }}
        />
        <div className="modal-footer">
          <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
          <Button variant="primary" size="sm" onClick={() => onSave(text)}>Save</Button>
        </div>
      </div>
    </div>
  );
};

export const WebTimeline: React.FC<WebTimelineProps> = ({ 
  audioUrl, 
  bgUrl,
  clips, 
  onClipChange,
  onTimeUpdate
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [isReady, setIsReady] = useState(false);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);

  // Interaction State
  const [draggingClipId, setDraggingClipId] = useState<string | null>(null);
  const [resizingClipId, setResizingClipId] = useState<string | null>(null);
  const [resizeSide, setResizingSide] = useState<'left' | 'right' | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [initialStartTime, setInitialStartTime] = useState(0);
  const [initialEndTime, setInitialEndTime] = useState(0);

  // Edit/Add Modal State
  const [editingClipId, setEditingClipId] = useState<string | null>(null);
  const [addingAtTime, setAddingAtTime] = useState<number | null>(null);

  // Keep refs of props to avoid re-initializing Wavesurfer when they change
  const clipsRef = useRef(clips);
  useEffect(() => { clipsRef.current = clips; }, [clips]);

  const onTimeUpdateRef = useRef(onTimeUpdate);
  useEffect(() => { onTimeUpdateRef.current = onTimeUpdate; }, [onTimeUpdate]);

  // 1. Initialize Wavesurfer ONCE
  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#34353c',
      progressColor: 'transparent',
      cursorColor: '#e24756',
      height: 80,
      barWidth: 2,
      barGap: 1,
      minPxPerSec: zoom,
      interact: true,
    });

    wavesurferRef.current = ws;

    ws.on('play', () => setIsPlaying(true));
    ws.on('pause', () => setIsPlaying(false));
    ws.on('ready', () => {
      setIsReady(true);
      ws.zoom(zoom);
    });
    ws.on('timeupdate', (t) => {
      setCurrentTime(t);
      onTimeUpdateRef.current(t);
    });

    return () => {
      ws.destroy();
    };
  }, []);

  // 2. Handle Audio URL changes
  useEffect(() => {
    if (wavesurferRef.current && audioUrl) {
      wavesurferRef.current.load(audioUrl);
      setIsReady(false);
    }
  }, [audioUrl]);

  // 3. Handle Zoom changes
  useEffect(() => {
    if (wavesurferRef.current && isReady) {
      wavesurferRef.current.zoom(zoom);
    }
  }, [zoom, isReady]);

  // 4. Global Mouse Events for Drag/Resize
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      if (!draggingClipId && !resizingClipId) return;

      const deltaX = e.clientX - dragStartX;
      const deltaTime = deltaX / zoom;
      
      const newClips = clipsRef.current.map(c => {
        if (c.id === draggingClipId) {
          const dur = initialEndTime - initialStartTime;
          let newStart = Math.max(0, initialStartTime + deltaTime);
          return { ...c, start_time: newStart, end_time: newStart + dur };
        }
        if (c.id === resizingClipId) {
          if (resizeSide === 'left') {
            let newStart = Math.max(0, Math.min(initialStartTime + deltaTime, c.end_time - 0.1));
            return { ...c, start_time: newStart };
          } else {
            let newEnd = Math.max(c.start_time + 0.1, initialEndTime + deltaTime);
            return { ...c, end_time: newEnd };
          }
        }
        return c;
      });
      onClipChange(newClips);
    };

    const handleGlobalMouseUp = () => {
      setDraggingClipId(null);
      setResizingClipId(null);
      setResizingSide(null);
    };

    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove);
      window.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [draggingClipId, resizingClipId, dragStartX, zoom, resizeSide, onClipChange]);

  // 5. Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        const target = e.target as HTMLElement;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          handleStamp();
        }
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedClipId) {
        const target = e.target as HTMLElement;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          onClipChange(clipsRef.current.filter(c => c.id !== selectedClipId));
          setSelectedClipId(null);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedClipId, onClipChange]);

  const handleSplit = () => {
    if (!wavesurferRef.current) return;
    const time = wavesurferRef.current.getCurrentTime();
    
    const targetIdx = clipsRef.current.findIndex(c => time > c.start_time && time < c.end_time);
    if (targetIdx !== -1) {
      const target = clipsRef.current[targetIdx];
      const newClips = [...clipsRef.current];
      const clip1 = { ...target, end_time: time };
      const clip2 = { 
        ...target, 
        id: `clip-split-${Math.random().toString(36).substr(2, 9)}`,
        start_time: time 
      };
      newClips.splice(targetIdx, 1, clip1, clip2);
      onClipChange(newClips);
    }
  };

  const handleStamp = () => {
    if (!wavesurferRef.current) return;
    const time = wavesurferRef.current.getCurrentTime();
    const newClips = [...clipsRef.current];
    const idx = newClips.findIndex(c => c.start_time === 0);
    if (idx !== -1) {
      const dur = 3.0;
      newClips[idx].start_time = time;
      newClips[idx].end_time = time + dur;
      onClipChange([...newClips].sort((a,b) => a.start_time - b.start_time));
    }
  };

  const startDragging = (e: React.MouseEvent, clip: LyricClip) => {
    e.stopPropagation();
    setDraggingClipId(clip.id);
    setDragStartX(e.clientX);
    setInitialStartTime(clip.start_time);
    setInitialEndTime(clip.end_time);
    setSelectedClipId(clip.id);
  };

  const startResizing = (e: React.MouseEvent, clip: LyricClip, side: 'left' | 'right') => {
    e.stopPropagation();
    setResizingClipId(clip.id);
    setResizingSide(side);
    setDragStartX(e.clientX);
    setInitialStartTime(clip.start_time);
    setInitialEndTime(clip.end_time);
    setSelectedClipId(clip.id);
  };

  const duration = wavesurferRef.current?.getDuration() || 0;
  const activeIndex = clips.findIndex(c => currentTime >= c.start_time && currentTime < c.end_time);

  const handleTrackDoubleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).classList.contains('clips-area')) {
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const x = e.clientX - rect.left + (scrollRef.current?.scrollLeft || 0);
      const time = x / zoom;
      setAddingAtTime(time);
    }
  };

  const saveNewClip = (text: string) => {
    if (addingAtTime !== null) {
      const newClip: LyricClip = {
        id: `clip-add-${Math.random().toString(36).substr(2, 9)}`,
        start_time: addingAtTime,
        end_time: addingAtTime + 2.0,
        text
      };
      onClipChange([...clips, newClip].sort((a,b) => a.start_time - b.start_time));
    }
    setAddingAtTime(null);
  };

  const saveEditedClip = (text: string) => {
    if (editingClipId) {
      onClipChange(clips.map(c => c.id === editingClipId ? { ...c, text } : c));
    }
    setEditingClipId(null);
  };

  return (
    <div className="web-timeline nle-editor">
      {addingAtTime !== null && (
        <EditLyricModal 
          title="Add New Lyric" 
          initialText="" 
          onSave={saveNewClip} 
          onCancel={() => setAddingAtTime(null)} 
        />
      )}
      {editingClipId !== null && (
        <EditLyricModal 
          title="Edit Lyric" 
          initialText={clips.find(c => c.id === editingClipId)?.text || ""} 
          onSave={saveEditedClip} 
          onCancel={() => setEditingClipId(null)} 
        />
      )}

      <div className="timeline-toolbar">
        <div className="toolbar-left">
          <Button variant="ghost" size="sm" onClick={() => wavesurferRef.current?.seekTo(0)}>
            <SkipBack size={16} />
          </Button>
          <Button variant="primary" size="sm" onClick={() => wavesurferRef.current?.playPause()}>
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleStamp} className="stamp-btn">
             Stamp (Enter)
          </Button>
          <div className="divider-v"></div>
          <Button variant="ghost" size="sm" onClick={handleSplit} title="Split Clip at Playhead" disabled={activeIndex === -1}>
             <Scissors size={14} /> Split
          </Button>
        </div>
        
        <div className="toolbar-center">
          <div className="zoom-control">
            <ChevronLeft size={14} className="zoom-btn" onClick={() => setZoom(Math.max(20, zoom - 20))} />
            <span>{zoom} px/s</span>
            <ChevronRight size={14} className="zoom-btn" onClick={() => setZoom(Math.min(500, zoom + 20))} />
          </div>
        </div>

        <div className="time-readout">
          {Math.floor(currentTime / 60)}:{Math.floor(currentTime % 60).toString().padStart(2, '0')}.{Math.floor((currentTime % 1) * 10)}
        </div>
      </div>
      
      <div className="timeline-scroller" ref={scrollRef}>
        <div className="tracks-container" style={{ width: isReady ? duration * zoom : '100%' }}>
          <TimelineRuler duration={duration} zoom={zoom} />

          <div className="track video-track">
            <div className="track-label">VIDEO</div>
            <div className="clips-area">
              {bgUrl ? (
                <div 
                  className="video-clip"
                  style={{ 
                    left: 0, 
                    width: `${duration * zoom}px` 
                  }}
                >
                  <div className="clip-content">
                    <Video size={12} />
                    <span className="clip-text">Background Video</span>
                  </div>
                  <button className="change-bg-btn" onClick={() => document.getElementById('nle-bg-input')?.click()} title="Change Background">
                    <Plus size={12} />
                  </button>
                </div>
              ) : (
                <div className="empty-track-prompt" onClick={() => document.getElementById('nle-bg-input')?.click()}>
                  <Plus size={14} /> Add Background Video
                </div>
              )}
              <input 
                id="nle-bg-input"
                type="file" 
                accept="video/*" 
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    const event = new CustomEvent('nle-bg-upload', { detail: file });
                    window.dispatchEvent(event);
                  }
                }}
              />
            </div>
          </div>

          <div className="track audio-track">
            <div className="track-label">AUDIO</div>
            <div className="waveform-wrapper" ref={containerRef}></div>
          </div>

          <div className="track lyrics-track">
            <div className="track-label">LYRICS</div>
            <div className="clips-area" onDoubleClick={handleTrackDoubleClick}>
              {clips.map((clip) => (
                <div 
                  key={clip.id}
                  className={`lyric-clip ${selectedClipId === clip.id ? 'selected' : ''}`}
                  style={{ 
                    left: `${clip.start_time * zoom}px`, 
                    width: `${(clip.end_time - clip.start_time) * zoom}px` 
                  }}
                  onMouseDown={(e) => startDragging(e, clip)}
                  onDoubleClick={(e) => { e.stopPropagation(); setEditingClipId(clip.id); }}
                >
                  <div className="resize-handle left" onMouseDown={(e) => startResizing(e, clip, 'left')}></div>
                  <div className="clip-content">
                    <span className="clip-text">{clip.text}</span>
                  </div>
                  <div className="resize-handle right" onMouseDown={(e) => startResizing(e, clip, 'right')}></div>
                </div>
              ))}
            </div>
          </div>

          <div className="playhead-line" style={{ left: `${currentTime * zoom}px` }}></div>
        </div>
      </div>
    </div>
  );
};
