import React from 'react';
import { Navbar } from '../components/landing/Navbar';
import { Hero } from '../components/landing/Hero';
import { Features } from '../components/landing/Features';
import { Creators } from '../components/landing/Creators';
import { Workflow } from '../components/landing/Workflow';
import './LandingPage.css';
import { blogs } from '../data/blogs';
... [rest of imports] ...
export const LandingPage: React.FC = () => {
  const featuredBlogs = blogs.slice(0, 3);

  return (
    <div className="landing-page-micro">
      <Navbar />
      <main>
        <Hero />
        <Workflow />
        <Features />
        <Creators />

        <section className="latest-blog-section">
          <div className="container-micro">
            <div className="section-header">
              <h2 className="section-title">Latest insights.</h2>
              <Link to="/blog" className="view-all-link">View all articles →</Link>
            </div>
            <div className="blog-grid-micro">
              {featuredBlogs.map((blog) => (
                <Link to={`/blog/${blog.id}`} key={blog.id} className="blog-card-micro">
                  <div className="blog-card-img-box">
                    <img src={blog.featuredImage} alt={blog.title} className="blog-card-img" />
                  </div>
                  <div className="blog-card-content">
                    <div className="blog-card-meta">
                      <span>{blog.category}</span>
                      <span>•</span>
                      <span>{blog.readTime}</span>
                    </div>
                    <h3 className="blog-card-title">{blog.title}</h3>
                    <p className="blog-card-excerpt">{blog.excerpt}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </main>
...

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
