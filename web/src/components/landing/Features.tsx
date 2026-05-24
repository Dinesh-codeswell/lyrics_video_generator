import React from 'react';
import { Layers, Zap, Palette, Video, MousePointer2, Smartphone } from 'lucide-react';
import './Features.css';

const features = [
  {
    title: 'Multi-Track NLE Timeline',
    description: 'Edit like a pro with separate tracks for audio and lyrics. Drag, trim, and sync with industry-standard precision.',
    icon: <Layers size={24} />,
    tag: 'PRO'
  },
  {
    title: 'Real-time Waveform Sync',
    description: 'Visual audio visualization powered by Wavesurfer.js. Stamp lyrics instantly as the music plays.',
    icon: <Zap size={24} />,
    tag: 'CORE'
  },
  {
    title: 'Deep Theme Engine',
    description: 'Control every pixel. Over 25+ settings for typography, glow effects, text strokes, and custom logos.',
    icon: <Palette size={24} />,
    tag: 'DESIGN'
  },
  {
    title: '1080p Production Export',
    description: 'High-fidelity MP4 generation optimized for YouTube and social media platforms.',
    icon: <Video size={24} />,
    tag: 'OUTPUT'
  },
  {
    title: 'Precision Drag-and-Drop',
    description: 'Adjust timings by simply dragging lyric blocks on the timeline. No more manual timestamp typing.',
    icon: <MousePointer2 size={24} />,
    tag: 'UX'
  },
  {
    title: 'Cloud-Ready Workflow',
    description: 'Manage your library of songs and themes in a single production-ready dashboard.',
    icon: <Smartphone size={24} />,
    tag: 'FLOW'
  },
];

export const Features: React.FC = () => {
  return (
    <section id="features" className="features-micro">
      <div className="features-container">
        <div className="features-header">
          <h2 className="features-title">Engineered for quality.</h2>
          <p className="features-subtitle">
            A powerful suite of tools designed to take your lyric video <br />
            production from hours to minutes.
          </p>
        </div>
        
        <div className="features-grid">
          {features.map((f, i) => (
            <div key={i} className="feature-card-micro">
              <div className="feature-icon-box">
                {f.icon}
                <span className="feature-tag">{f.tag}</span>
              </div>
              <h3 className="feature-name">{f.title}</h3>
              <p className="feature-text">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
