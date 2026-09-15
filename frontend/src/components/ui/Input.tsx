import React from 'react';
import { AlertCircle } from 'lucide-react';
import './Input.css';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  optional?: boolean;
  error?: string;
  hint?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, optional, error, hint: _hint, id, className = '', ...props }, ref) => {
    const inputId = id ?? `input-${label.toLowerCase().replace(/\s+/g, '-')}`;
    const errorId = error ? `${inputId}-error` : undefined;

    return (
      <div className="input-wrapper">
        <label htmlFor={inputId} className="input-label">
          {label}
          {optional && (
            <span className="input-label-optional">(optional)</span>
          )}
        </label>
        <input
          ref={ref}
          id={inputId}
          className={[
            'input-field',
            error ? 'input-error' : '',
            className,
          ]
            .filter(Boolean)
            .join(' ')}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={errorId}
          {...props}
        />
        {error && (
          <span id={errorId} className="input-error-msg" role="alert">
            <AlertCircle size={13} aria-hidden="true" />
            {error}
          </span>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';
