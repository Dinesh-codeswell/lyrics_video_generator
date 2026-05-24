import React from 'react';
import { Upload, Sliders, FileVideo } from 'lucide-react';
import './Workflow.css';

export const Workflow: React.FC = () => {
  return (
    <section className="workflow-micro">
      <div className="workflow-container">
        <h2 className="workflow-title">Ready in three steps.</h2>
        <div className="workflow-steps">
          <div className="step-card">
            <div className="step-number">01</div>
            <div className="step-icon"><Upload size={32} /></div>
            <h3 className="step-name">Upload Assets</h3>
            <p className="step-text">Drop your audio and lyrics. Our engine auto-embeds the timeline instantly.</p>
          </div>
          
          <div className="step-connector"></div>

          <div className="step-card">
            <div className="step-number">02</div>
            <div className="step-icon"><Sliders size={32} /></div>
            <h3 className="step-name">Refine & Style</h3>
            <p className="step-text">Drag clips on the NLE timeline and customize your unique theme.</p>
          </div>

          <div className="step-connector"></div>

          <div className="step-card">
            <div className="step-number">03</div>
            <div className="step-icon"><FileVideo size={32} /></div>
            <h3 className="step-name">Instant Export</h3>
            <p className="step-text">Render 1080p high-fidelity MP4s ready for all major platforms.</p>
          </div>
        </div>
      </div>
    </section>
  );
};
