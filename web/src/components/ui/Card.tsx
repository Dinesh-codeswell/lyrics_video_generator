import React from 'react';
import './Card.css';

interface CardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
  headerActions?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, title, className = '', headerActions }) => {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="card-header-bar">
          <div className="card-title">{title}</div>
          {headerActions && <div className="card-actions">{headerActions}</div>}
        </div>
      )}
      <div className="card-content">
        {children}
      </div>
    </div>
  );
};
