import React from 'react';
import { Navbar } from '../components/landing/Navbar';
import { Hero } from '../components/landing/Hero';
import { Features } from '../components/landing/Features';
import { Creators } from '../components/landing/Creators';
import { Workflow } from '../components/landing/Workflow';
import './LandingPage.css';

export const LandingPage: React.FC = () => {
  return (
    <div className="landing-page-micro">
      <Navbar />
      <main>
        <Hero />
        <Workflow />
        <Features />
        <Creators />
      </main>
      <footer className="footer-micro">
        <div className="footer-container">
          <div className="footer-top">
            <div className="footer-brand">LyricGen</div>
            <div className="footer-nav">
              <a href="#features">Features</a>
              <a href="#creators">Creators</a>
              <a href="/dashboard">Dashboard</a>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 Lyric Video Generator. The new standard for synced production.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};
