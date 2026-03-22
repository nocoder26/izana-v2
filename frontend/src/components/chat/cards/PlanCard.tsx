'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { PlanCardData, Meal } from '../types';

type PlanTab = 'nutrition' | 'exercise' | 'meditation';

interface PlanCardProps {
  data: PlanCardData;
  onAction?: (action: string, payload?: unknown) => void;
}

export default function PlanCard({ data, onAction }: PlanCardProps) {
  const [activeTab, setActiveTab] = useState<PlanTab>('nutrition');
  const [meals, setMeals] = useState<Meal[]>(data.meals);
  const [exerciseDone, setExerciseDone] = useState(data.exercise.done);
  const [meditationDone, setMeditationDone] = useState(data.meditation.done);

  const tabs: { id: PlanTab; label: string }[] = [
    { id: 'nutrition', label: 'Nutrition' },
    { id: 'exercise', label: 'Exercise' },
    { id: 'meditation', label: 'Meditation' },
  ];

  const completedCount =
    meals.filter((m) => m.done).length +
    (exerciseDone ? 1 : 0) +
    (meditationDone ? 1 : 0);
  const totalCount = meals.length + 2;
  const progress = totalCount > 0 ? completedCount / totalCount : 0;

  const handleMealDone = (mealId: string) => {
    setMeals((prev) =>
      prev.map((m) => (m.id === mealId ? { ...m, done: true } : m)),
    );
    onAction?.('meal_done', { mealId });
  };

  const firstUndoneIndex = meals.findIndex((m) => !m.done);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn(
        'rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated',
        'shadow-[0_1px_3px_rgba(42,36,51,0.04)] overflow-hidden',
      )}
    >
      {/* Tabs */}
      <div className="flex border-b border-border-default">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex-1 py-3 text-sm font-medium transition-colors relative',
              activeTab === tab.id
                ? 'text-brand-primary'
                : 'text-text-tertiary hover:text-text-secondary',
            )}
          >
            {tab.label}
            {activeTab === tab.id && (
              <motion.div
                layoutId="plan-tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-primary"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === 'nutrition' && (
          <div className="flex flex-col gap-3">
            {meals.map((meal, i) => {
              const isNext = i === firstUndoneIndex;
              return (
                <motion.div
                  key={meal.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, delay: i * 0.1 }}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-xl',
                    'border border-border-default',
                    meal.done
                      ? 'opacity-50'
                      : isNext
                        ? 'opacity-100'
                        : 'opacity-60',
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{meal.emoji}</span>
                    <div>
                      <p className="text-sm font-medium text-text-primary">
                        {meal.label}
                      </p>
                      <p className="text-xs text-text-tertiary">
                        {meal.description}
                      </p>
                    </div>
                  </div>
                  {meal.done ? (
                    <span className="text-success text-sm font-medium">
                      Done
                    </span>
                  ) : (
                    <button
                      onClick={() => handleMealDone(meal.id)}
                      className="px-3 py-1 text-xs font-medium rounded-lg
                        bg-brand-primary text-white hover:opacity-90 transition-opacity"
                    >
                      Done
                    </button>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}

        {activeTab === 'exercise' && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-3"
          >
            <div
              className={cn(
                'relative rounded-xl overflow-hidden bg-canvas-sunken',
                'aspect-video flex items-center justify-center',
              )}
            >
              {data.exercise.thumbnailUrl ? (
                <img
                  src={data.exercise.thumbnailUrl}
                  alt={data.exercise.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-text-tertiary text-sm">Video Preview</div>
              )}
              <button
                onClick={() => onAction?.('play_video', { exercise: data.exercise })}
                className="absolute inset-0 flex items-center justify-center
                  bg-black/20 hover:bg-black/30 transition-colors"
                aria-label="Play exercise video"
              >
                <span className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center text-2xl">
                  ▶
                </span>
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-text-primary">
                  {data.exercise.title}
                </p>
                <p className="text-xs text-text-tertiary">
                  {data.exercise.duration}
                </p>
              </div>
              {exerciseDone ? (
                <span className="text-success text-sm font-medium">Done</span>
              ) : (
                <button
                  onClick={() => {
                    setExerciseDone(true);
                    onAction?.('exercise_done', { exerciseId: data.exercise.id });
                  }}
                  className="px-3 py-1 text-xs font-medium rounded-lg
                    bg-brand-primary text-white hover:opacity-90 transition-opacity"
                >
                  Done
                </button>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'meditation' && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-3"
          >
            <div
              className={cn(
                'rounded-xl overflow-hidden p-6',
                'bg-gradient-to-br from-brand-primary/10 to-brand-accent/10',
                'flex flex-col items-center gap-4',
              )}
            >
              <button
                onClick={() => onAction?.('play_audio', { meditation: data.meditation })}
                className="w-16 h-16 rounded-full bg-brand-primary text-white
                  flex items-center justify-center text-2xl
                  hover:opacity-90 transition-opacity"
                aria-label="Play meditation audio"
              >
                ▶
              </button>
              <div className="text-center">
                <p className="text-sm font-medium text-text-primary">
                  {data.meditation.title}
                </p>
                <p className="text-xs text-text-tertiary">
                  {data.meditation.duration}
                </p>
              </div>
            </div>
            <div className="flex justify-end">
              {meditationDone ? (
                <span className="text-success text-sm font-medium">Done</span>
              ) : (
                <button
                  onClick={() => {
                    setMeditationDone(true);
                    onAction?.('meditation_done', {
                      meditationId: data.meditation.id,
                    });
                  }}
                  className="px-3 py-1 text-xs font-medium rounded-lg
                    bg-brand-primary text-white hover:opacity-90 transition-opacity"
                >
                  Done
                </button>
              )}
            </div>
          </motion.div>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-0.5 w-full bg-canvas-sunken">
        <motion.div
          className="h-full bg-brand-primary"
          initial={{ width: 0 }}
          animate={{ width: `${progress * 100}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </motion.div>
  );
}
