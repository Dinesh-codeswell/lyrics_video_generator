import React from 'react';
import './Creators.css';

export const Creators: React.FC = () => {
  return (
    <section id="creators" className="creators-micro">
      <div className="creators-container">
        <div className="creators-layout">
          <div className="creators-visual">
            <img 
              src="https://images.unsplash.com/photo-1514525253361-bee8718a300a?q=80&w=2048&auto=format&fit=crop" 
              alt="Live concert" 
              className="creators-img"
            />
            <div className="creators-quote-card">
              <p className="quote-text">"The only tool that gives me the precision I need for complex tour visuals without the Premiere overhead."</p>
              <div className="quote-author">
                <span className="author-name">Alex Rivera</span>
                <span className="author-role">Visual Director</span>
              </div>
            </div>
          </div>
          <div className="creators-info">
            <h2 className="creators-title">Built for the <br /><span className="text-accent-blue">Modern Creator.</span></h2>
            <p className="creators-description">
              Whether you're a YouTuber, a professional editor, or an independent artist, our platform provides the high-fidelity output you demand with the speed you deserve.
            </p>
            <ul className="creators-list">
              <li>
                <span className="list-dot"></span>
                <strong>Tour Visuals:</strong> Create stunning synced backdrops for live performances.
              </li>
              <li>
                <span className="list-dot"></span>
                <strong>Social Media:</strong> Export vertical-ready crops for TikTok and Instagram.
              </li>
              <li>
                <span className="list-dot"></span>
                <strong>Production Workflows:</strong> Seamlessly integrate into your existing studio setup.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};
