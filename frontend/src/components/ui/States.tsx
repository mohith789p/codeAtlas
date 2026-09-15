import React from 'react';

interface SpinnerProps {
  size?: number;
  className?: string;
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 20,
  className = '',
  label = 'Loading…',
}) => (
  <span
    className={`codeatlas-loader ${className}`.trim()}
    role="status"
    aria-label={label}
    style={{ '--loader-size': `${size}px` } as React.CSSProperties}
  >
  </span>
);

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
  style,
}) => (
  <div
    className={className}
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      padding: 'var(--space-12) var(--space-8)',
      gap: 'var(--space-4)',
      color: 'var(--text-secondary)',
      ...style,
    }}
  >
    {icon && (
      <span style={{ color: 'var(--text-muted)', opacity: 0.6 }}>{icon}</span>
    )}
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', alignItems: 'center' }}>
      <p
        style={{
          fontSize: 'var(--text-body)',
          fontWeight: 'var(--weight-medium)',
          color: 'var(--text-secondary)',
        }}
      >
        {title}
      </p>
      {description && (
        <p style={{ fontSize: 'var(--text-meta)', color: 'var(--text-muted)', maxWidth: '28ch' }}>
          {description}
        </p>
      )}
    </div>
    {action}
  </div>
);

interface ErrorStateProps {
  title?: string;
  message: string;
  action?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  action,
  className = '',
  style,
}) => (
  <div
    className={className}
    role="alert"
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      padding: 'var(--space-12) var(--space-8)',
      gap: 'var(--space-4)',
      ...style,
    }}
  >
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
        alignItems: 'center',
      }}
    >
      <p
        style={{
          fontSize: 'var(--text-body)',
          fontWeight: 'var(--weight-medium)',
          color: 'var(--text-primary)',
        }}
      >
        {title}
      </p>
      <p style={{ fontSize: 'var(--text-meta)', color: 'var(--error)', maxWidth: '36ch' }}>
        {message}
      </p>
    </div>
    {action}
  </div>
);
