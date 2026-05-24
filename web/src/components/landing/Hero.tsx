import React from 'react';
import { Link } from 'react-router-dom';
import './Hero.css';

export const Hero: React.FC = () => {
  return (
    <section className="hero-micro">
      <div className="hero-content">
        <div className="hero-tag">
          <span className="tag-new">NEW</span>
          <span className="tag-text">Advanced Video Editor Timeline now live</span>
        </div>
        
        <h1 className="hero-display-title">
          The new standard for <br />
          <span className="italic-serif">lyric video</span> production.
        </h1>
        
        <p className="hero-subheading">
          Generate 1080p high-fidelity lyric videos in minutes. <br />
          Professional NLE editing, direct in your browser.
        </p>
        
        <div className="hero-actions">
          <Link to="/dashboard">
            <button className="btn-hero-primary">Get Started — Free</button>
          </Link>
          <button className="btn-hero-ghost">Watch the process</button>
        </div>

        <div className="hero-app-mockup">
          <div className="mockup-frame">
            <div className="mockup-header">
              <div className="dots"><span></span><span></span><span></span></div>
              <div className="address-bar">lyricgen.ai/project/new</div>
            </div>
            <div className="mockup-content">
              <img 
                src="https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?q=80&w=2070&auto=format&fit=crop" 
                alt="App Preview" 
                className="mockup-img"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
