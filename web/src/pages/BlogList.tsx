import React from 'react';
import { Link } from 'react-router-dom';
import { blogs } from '../data/blogs';
import { Navbar } from '../components/landing/Navbar';
import './Blog.css';

export const BlogList: React.FC = () => {
  return (
    <div className="blog-page-micro">
      <Navbar />
      <header className="blog-header-section">
        <div className="container-micro">
          <span className="blog-badge">Insights & Resources</span>
          <h1 className="blog-main-title">Beyond Career Blog</h1>
          <p className="blog-subtitle">The definitive prep resources for consulting, finance, and career growth.</p>
        </div>
      </header>

      <main className="container-micro">
        <div className="blog-grid-micro">
          {blogs.map((blog) => (
            <Link to={`/blog/${blog.id}`} key={blog.id} className="blog-card-micro">
              <div className="blog-card-img-box">
                <img src={blog.featuredImage} alt={blog.title} className="blog-card-img" />
              </div>
              <div className="blog-card-content">
                <div className="blog-card-meta">
                  <span className="blog-card-category">{blog.category}</span>
                  <span className="blog-card-dot">•</span>
                  <span className="blog-card-time">{blog.readTime} read</span>
                </div>
                <h2 className="blog-card-title">{blog.title}</h2>
                <p className="blog-card-excerpt">{blog.excerpt}</p>
                <div className="blog-card-footer">
                  <span className="blog-card-date">{blog.date}</span>
                  <span className="blog-card-link">Read Article →</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </main>

      <footer className="footer-micro">
        <div className="footer-container">
          <div className="footer-bottom">
            <p>&copy; 2026 Beyond Career. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};
