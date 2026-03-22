'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2',
    'font-medium transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
    'select-none cursor-pointer',
  ].join(' '),
  {
    variants: {
      variant: {
        primary: [
          'bg-brand-primary text-white',
          'hover:opacity-90',
          'focus-visible:ring-brand-primary',
        ].join(' '),
        secondary: [
          'bg-canvas-elevated text-text-primary',
          'border border-border-default',
          'hover:bg-canvas-sunken',
          'focus-visible:ring-brand-primary',
        ].join(' '),
        ghost: [
          'bg-transparent text-text-secondary',
          'hover:bg-canvas-sunken hover:text-text-primary',
          'focus-visible:ring-brand-primary',
        ].join(' '),
        danger: [
          'bg-error text-white',
          'hover:opacity-90',
          'focus-visible:ring-error',
        ].join(' '),
      },
      size: {
        sm: 'h-8 px-3 text-sm rounded-lg',
        md: 'h-10 px-4 text-sm rounded-xl',
        lg: 'h-12 px-6 text-base rounded-xl',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
);

type ButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onAnimationStart' | 'onDrag' | 'onDragEnd' | 'onDragStart'> &
  VariantProps<typeof buttonVariants> & {
    isLoading?: boolean;
  };

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, disabled, children, ...props }, ref) => {
    return (
      <motion.button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        disabled={disabled || isLoading}
        whileTap={{ scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 400, damping: 17 }}
        {...(props as HTMLMotionProps<'button'>)}
      >
        {isLoading ? (
          <>
            <Spinner />
            <span>{children}</span>
          </>
        ) : (
          children
        )}
      </motion.button>
    );
  },
);

Button.displayName = 'Button';

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export { Button, buttonVariants };
export type { ButtonProps };
