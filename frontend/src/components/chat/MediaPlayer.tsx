'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiPost } from '@/lib/api-client';

type MediaType = 'video' | 'audio';

interface MediaPlayerProps {
  open: boolean;
  onClose: () => void;
  type: MediaType;
  src: string;
  title: string;
  contentId?: string;
}

export default function MediaPlayer({
  open,
  onClose,
  type,
  src,
  title,
  contentId,
}: MediaPlayerProps) {
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement | null>(null);
  const dragControls = useDragControls();
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const progressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Track progress and POST every 60s
  useEffect(() => {
    if (!open || !contentId) return;

    progressIntervalRef.current = setInterval(() => {
      if (mediaRef.current && !mediaRef.current.paused) {
        apiPost(`/content/${contentId}/progress`, {
          currentTime: mediaRef.current.currentTime,
          duration: mediaRef.current.duration,
        }).catch(() => {});
      }
    }, 60_000);

    return () => {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
    };
  }, [open, contentId]);

  const handleTimeUpdate = useCallback(() => {
    const el = mediaRef.current;
    if (el && el.duration) {
      setProgress(el.currentTime / el.duration);
      setDuration(el.duration);
    }
  }, []);

  const togglePlayPause = useCallback(() => {
    const el = mediaRef.current;
    if (!el) return;
    if (el.paused) {
      el.play();
      setIsPlaying(true);
    } else {
      el.pause();
      setIsPlaying(false);
    }
  }, []);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Bottom sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            drag="y"
            dragControls={dragControls}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.5 }}
            onDragEnd={(_e, info) => {
              if (info.offset.y > 100) onClose();
            }}
            className={cn(
              'fixed bottom-0 left-0 right-0 z-50',
              'bg-canvas-elevated rounded-t-2xl',
              'max-h-[85vh] overflow-hidden',
              'safe-area-bottom',
            )}
            style={{ boxShadow: '0 -4px 24px rgba(42,36,51,0.12)' }}
          >
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-10 h-1 rounded-full bg-border-default" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-5 pb-3">
              <h3 className="text-base font-semibold text-text-primary truncate pr-4">
                {title}
              </h3>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-full bg-canvas-sunken flex items-center justify-center
                  text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Media content */}
            <div className="px-5 pb-6">
              {type === 'video' ? (
                <div className="rounded-xl overflow-hidden bg-black">
                  <video
                    ref={mediaRef as React.RefObject<HTMLVideoElement>}
                    src={src}
                    className="w-full aspect-video"
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleTimeUpdate}
                    onEnded={() => setIsPlaying(false)}
                    playsInline
                  />
                </div>
              ) : (
                <div
                  className={cn(
                    'rounded-xl p-10',
                    'bg-gradient-to-br from-brand-primary/15 to-brand-accent/15',
                    'flex flex-col items-center gap-6',
                  )}
                >
                  <button
                    onClick={togglePlayPause}
                    className="w-20 h-20 rounded-full bg-brand-primary text-white
                      flex items-center justify-center text-3xl
                      hover:opacity-90 transition-opacity
                      shadow-[0_4px_12px_rgba(74,61,143,0.3)]"
                    aria-label={isPlaying ? 'Pause' : 'Play'}
                  >
                    {isPlaying ? '⏸' : '▶'}
                  </button>
                  <audio
                    ref={mediaRef as React.RefObject<HTMLAudioElement>}
                    src={src}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleTimeUpdate}
                    onEnded={() => setIsPlaying(false)}
                  />
                </div>
              )}

              {/* Controls */}
              <div className="mt-4 flex flex-col gap-2">
                {/* Progress bar */}
                <div className="w-full h-1 rounded-full bg-canvas-sunken overflow-hidden">
                  <div
                    className="h-full bg-brand-primary rounded-full transition-all duration-300"
                    style={{ width: `${progress * 100}%` }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-tertiary">
                    {formatTime(progress * duration)}
                  </span>
                  {type === 'video' && (
                    <button
                      onClick={togglePlayPause}
                      className="w-10 h-10 rounded-full bg-brand-primary text-white
                        flex items-center justify-center text-sm
                        hover:opacity-90 transition-opacity"
                      aria-label={isPlaying ? 'Pause' : 'Play'}
                    >
                      {isPlaying ? '⏸' : '▶'}
                    </button>
                  )}
                  <span className="text-xs text-text-tertiary">
                    {formatTime(duration)}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
