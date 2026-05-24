import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

export const Navbar: React.FC = () => {
  return (
    <nav className="navbar-micro">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          <span className="brand-dot"></span>
          LyricGen
        </Link>
        <div className="navbar-links">
          <a href="/#features" className="nav-link">Features</a>
          <a href="/#creators" className="nav-link">For Creators</a>
          <Link to="/blog" className="nav-link">Blog</Link>
          <Link to="/dashboard">
            <button className="btn-primary-filled">Open Dashboard</button>
          </Link>
        </div>
      </div>
    </nav>
  );
};
