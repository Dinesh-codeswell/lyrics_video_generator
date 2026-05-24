import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { blogs } from '../data/blogs';
import { Navbar } from '../components/landing/Navbar';
import './Blog.css';

export const BlogDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const blog = blogs.find((b) => b.id === id);

  if (!blog) {
    return <div>Blog not found</div>;
  }

  return (
    <div className="blog-detail-micro">
      <Navbar />
      <header className="blog-post-header">
        <div className="container-micro">
          <Link to="/blog" className="back-link">← Back to Blog</Link>
          <div className="post-meta">
            <span>{blog.category}</span>
            <span>•</span>
            <span>{blog.date}</span>
          </div>
          <h1 className="post-title">{blog.title}</h1>
        </div>
      </header>

      <main className="container-micro post-layout">
        <div className="post-content">
          {blog.content.split('\n').map((line, i) => {
            if (line.startsWith('# ')) return <h1 key={i}>{line.replace('# ', '')}</h1>;
            if (line.startsWith('## ')) return <h2 key={i}>{line.replace('## ', '')}</h2>;
            if (line.startsWith('### ')) return <h3 key={i}>{line.replace('### ', '')}</h3>;
            if (line.startsWith('![')) {
              const alt = line.match(/\[(.*?)\]/)?.[1];
              const src = line.substring(line.lastIndexOf('(') + 1, line.lastIndexOf(')'));
              return <img key={i} src={src} alt={alt} className="post-inline-img" />;
            }
            if (line.startsWith('* ')) return <li key={i}>{line.replace('* ', '')}</li>;
            if (line.trim() === '') return <br key={i} />;
            return <p key={i}>{line}</p>;
          })}
        </div>
        
        <aside className="post-sidebar">
          <div className="cta-card-micro">
            <h3>Get the Prep Kit</h3>
            <p>Master your interviews with our comprehensive resources.</p>
            <button className="btn-hero-primary">Explore Now</button>
          </div>
        </aside>
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
