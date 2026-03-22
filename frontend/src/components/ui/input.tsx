'use client';

import { forwardRef, useState, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
  showPasswordToggle?: boolean;
};

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, showPasswordToggle, id, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);

    const isPassword = type === 'password';
    const resolvedType = isPassword && showPassword ? 'text' : type;
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-text-secondary"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={inputId}
            type={resolvedType}
            className={cn(
              'flex w-full rounded-xl border border-border-default bg-canvas-elevated px-4 py-2.5',
              'text-[16px] leading-6 text-text-primary',
              'placeholder:text-text-tertiary',
              'transition-colors duration-150',
              'focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20',
              'disabled:cursor-not-allowed disabled:opacity-50',
              error && 'border-error focus:border-error focus:ring-error/20',
              isPassword && showPasswordToggle && 'pr-12',
              className,
            )}
            {...props}
          />
          {isPassword && showPasswordToggle && (
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2',
                'text-xs font-medium text-text-tertiary',
                'hover:text-text-secondary',
                'transition-colors duration-150',
                'select-none',
              )}
              tabIndex={-1}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          )}
        </div>
        {error && (
          <p className="text-xs text-error" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';

export { Input };
export type { InputProps };
