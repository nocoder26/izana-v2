'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import NutritionistLayout from '@/components/nutritionist/NutritionistLayout';
import { useParams } from 'next/navigation';

/* ── Types ─────────────────────────────────────────────────── */

type UserContext = {
  treatment: string;
  allergies: string[];
  preferences: string[];
  bloodwork: Record<string, string>;
  age: number;
  bmi: number;
};

type MealItem = {
  id: string;
  name: string;
  description: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  modified?: boolean;
};

type ExerciseItem = {
  id: string;
  name: string;
  duration: number;
  intensity: string;
  notes: string;
  modified?: boolean;
};

type MeditationItem = {
  id: string;
  name: string;
  duration: number;
  type: string;
  modified?: boolean;
};

type PlanData = {
  id: string;
  userId: string;
  userContext: UserContext;
  meals: MealItem[];
  exercises: ExerciseItem[];
  meditations: MeditationItem[];
  aiReasoning: string;
  fieInsights: string[];
  priority: string;
  deadline: string;
  reviewHistory: Array<{
    reviewer: string;
    action: string;
    date: string;
    notes?: string;
  }>;
};

type Modification = {
  itemId: string;
  field: string;
  oldValue: string;
  newValue: string;
  reason: string;
};

/* ── API Helper ────────────────────────────────────────────── */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

async function nutritionistFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? sessionStorage.getItem('nutritionist_jwt') : null;
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined),
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json() as Promise<T>;
}

/* ── Component ─────────────────────────────────────────────── */

export default function PlanReviewPage() {
  const params = useParams();
  const planId = params.planId as string;

  const [plan, setPlan] = useState<PlanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editorTab, setEditorTab] = useState<'nutrition' | 'exercise' | 'meditation'>('nutrition');
  const [modifications, setModifications] = useState<Modification[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Modal states
  const [showModModal, setShowModModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectInstructions, setRejectInstructions] = useState('');
  const [pendingMod, setPendingMod] = useState<{ itemId: string; field: string; oldValue: string; newValue: string } | null>(null);
  const [modReason, setModReason] = useState('');

  useEffect(() => {
    const token = sessionStorage.getItem('nutritionist_jwt');
    if (!token) {
      window.location.href = '/nutritionist/login';
      return;
    }
    setLoading(true);
    nutritionistFetch<PlanData>(`/nutritionist/plan/${planId}`)
      .then(setPlan)
      .catch(() => setPlan(null))
      .finally(() => setLoading(false));
  }, [planId]);

  const handleFieldEdit = useCallback(
    (itemId: string, field: string, oldValue: string, newValue: string) => {
      if (oldValue === newValue) return;
      setPendingMod({ itemId, field, oldValue, newValue });
      setModReason('');
      setShowModModal(true);
    },
    [],
  );

  const confirmModification = useCallback(() => {
    if (!pendingMod) return;
    setModifications((prev) => [
      ...prev.filter((m) => !(m.itemId === pendingMod.itemId && m.field === pendingMod.field)),
      { ...pendingMod, reason: modReason },
    ]);

    // Mark item as modified in plan
    if (plan) {
      const updatedPlan = { ...plan };
      const markModified = (items: Array<{ id: string; modified?: boolean }>) =>
        items.map((item) => (item.id === pendingMod.itemId ? { ...item, modified: true } : item));
      updatedPlan.meals = markModified(updatedPlan.meals) as MealItem[];
      updatedPlan.exercises = markModified(updatedPlan.exercises) as ExerciseItem[];
      updatedPlan.meditations = markModified(updatedPlan.meditations) as MeditationItem[];
      setPlan(updatedPlan);
    }

    setShowModModal(false);
    setPendingMod(null);
  }, [pendingMod, modReason, plan]);

  const handleApprove = useCallback(async () => {
    setSubmitting(true);
    try {
      await nutritionistFetch(`/nutritionist/plan/${planId}/approve`, { method: 'POST' });
      window.location.href = '/nutritionist/queue';
    } catch {
      // handle error
    } finally {
      setSubmitting(false);
    }
  }, [planId]);

  const handleModifyApprove = useCallback(async () => {
    setSubmitting(true);
    try {
      await nutritionistFetch(`/nutritionist/plan/${planId}/modify`, {
        method: 'POST',
        body: JSON.stringify({ modifications }),
      });
      window.location.href = '/nutritionist/queue';
    } catch {
      // handle error
    } finally {
      setSubmitting(false);
    }
  }, [planId, modifications]);

  const handleReject = useCallback(async () => {
    setSubmitting(true);
    try {
      await nutritionistFetch(`/nutritionist/plan/${planId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason: rejectReason, regenerationInstructions: rejectInstructions }),
      });
      window.location.href = '/nutritionist/queue';
    } catch {
      // handle error
    } finally {
      setSubmitting(false);
      setShowRejectModal(false);
    }
  }, [planId, rejectReason, rejectInstructions]);

  if (loading) {
    return (
      <NutritionistLayout>
        <div className="flex items-center justify-center h-dvh" style={{ minHeight: '100vh' }}>
          <div className="flex flex-col items-center gap-3">
            <div className="izana-avatar w-10 h-10" />
            <p className="text-sm text-text-secondary">Loading plan...</p>
          </div>
        </div>
      </NutritionistLayout>
    );
  }

  if (!plan) {
    return (
      <NutritionistLayout>
        <div className="flex items-center justify-center h-dvh" style={{ minHeight: '100vh' }}>
          <div className="text-center">
            <p className="text-lg font-medium text-text-primary mb-2">Plan not found</p>
            <Button variant="secondary" onClick={() => { window.location.href = '/nutritionist/queue'; }}>
              Back to Queue
            </Button>
          </div>
        </div>
      </NutritionistLayout>
    );
  }

  return (
    <NutritionistLayout>
      <div className="flex h-dvh" style={{ minHeight: '100vh' }}>
        {/* LEFT PANEL — User Context (272px) */}
        <aside className="w-[272px] border-r border-border-default bg-canvas-elevated overflow-y-auto flex-shrink-0">
          <div className="p-5">
            {/* Back button */}
            <button
              onClick={() => { window.location.href = '/nutritionist/queue'; }}
              className="flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-primary transition-colors mb-5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Queue
            </button>

            <h2 className="text-lg font-semibold text-text-primary mb-4">User Context</h2>

            <div className="space-y-4">
              <InfoRow label="Treatment" value={plan.userContext.treatment} />
              <InfoRow label="Age" value={String(plan.userContext.age)} />
              <InfoRow label="BMI" value={String(plan.userContext.bmi)} />

              <div>
                <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1.5">Allergies</p>
                <div className="flex flex-wrap gap-1.5">
                  {plan.userContext.allergies.length > 0 ? (
                    plan.userContext.allergies.map((a) => (
                      <span key={a} className="px-2 py-0.5 text-xs rounded-full bg-error/10 text-error">
                        {a}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-text-tertiary">None reported</span>
                  )}
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1.5">Preferences</p>
                <div className="flex flex-wrap gap-1.5">
                  {plan.userContext.preferences.length > 0 ? (
                    plan.userContext.preferences.map((p) => (
                      <span key={p} className="px-2 py-0.5 text-xs rounded-full bg-brand-primary-bg text-brand-primary">
                        {p}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-text-tertiary">None set</span>
                  )}
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1.5">Bloodwork</p>
                <div className="space-y-1.5">
                  {Object.entries(plan.userContext.bloodwork).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-text-secondary">{key}</span>
                      <span className="text-text-primary font-medium">{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* CENTER PANEL — Plan Editor (flex-1) */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-border-default bg-canvas-elevated px-6 pt-5 pb-0">
            <h2 className="text-lg font-semibold text-text-primary mb-3">Plan Editor</h2>
            <div className="flex gap-0">
              {(['nutrition', 'exercise', 'meditation'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setEditorTab(tab)}
                  className={cn(
                    'px-4 pb-3 text-sm font-medium border-b-2 transition-colors capitalize',
                    editorTab === tab
                      ? 'border-brand-primary text-brand-primary'
                      : 'border-transparent text-text-tertiary hover:text-text-secondary',
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Editor content */}
          <div className="flex-1 overflow-y-auto p-6">
            <AnimatePresence mode="wait">
              {editorTab === 'nutrition' && (
                <motion.div
                  key="nutrition"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ duration: 0.15 }}
                  className="space-y-3"
                >
                  {plan.meals.map((meal) => (
                    <EditableMealCard
                      key={meal.id}
                      meal={meal}
                      onEdit={handleFieldEdit}
                    />
                  ))}
                  {plan.meals.length === 0 && (
                    <p className="text-sm text-text-tertiary text-center py-12">No meal items in this plan.</p>
                  )}
                </motion.div>
              )}

              {editorTab === 'exercise' && (
                <motion.div
                  key="exercise"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ duration: 0.15 }}
                  className="space-y-3"
                >
                  {plan.exercises.map((ex) => (
                    <EditableExerciseCard
                      key={ex.id}
                      exercise={ex}
                      onEdit={handleFieldEdit}
                    />
                  ))}
                  {plan.exercises.length === 0 && (
                    <p className="text-sm text-text-tertiary text-center py-12">No exercises in this plan.</p>
                  )}
                </motion.div>
              )}

              {editorTab === 'meditation' && (
                <motion.div
                  key="meditation"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ duration: 0.15 }}
                  className="space-y-3"
                >
                  {plan.meditations.map((med) => (
                    <EditableMeditationCard
                      key={med.id}
                      meditation={med}
                      onEdit={handleFieldEdit}
                    />
                  ))}
                  {plan.meditations.length === 0 && (
                    <p className="text-sm text-text-tertiary text-center py-12">No meditations in this plan.</p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Bottom bar */}
          <div className="border-t border-border-default bg-canvas-elevated px-6 py-4 flex items-center justify-between">
            <p className="text-sm text-text-secondary">
              <span className="font-medium text-text-primary">{modifications.length}</span> modification{modifications.length !== 1 ? 's' : ''}
            </p>
            <div className="flex items-center gap-3">
              <Button
                variant="danger"
                size="sm"
                onClick={() => setShowRejectModal(true)}
                disabled={submitting}
              >
                Reject
              </Button>
              {modifications.length > 0 ? (
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={submitting}
                  onClick={handleModifyApprove}
                >
                  Modify & Approve
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={submitting}
                  onClick={handleApprove}
                >
                  Approve
                </Button>
              )}
            </div>
          </div>
        </main>

        {/* RIGHT PANEL — AI Reasoning (320px) */}
        <aside className="w-[320px] border-l border-border-default bg-canvas-elevated overflow-y-auto flex-shrink-0">
          <div className="p-5 space-y-6">
            {/* Priority & Deadline */}
            <div className="flex items-center justify-between">
              <span className={cn(
                'text-xs font-medium px-2.5 py-1 rounded-full capitalize',
                plan.priority === 'urgent' ? 'bg-error/15 text-error' :
                plan.priority === 'high' ? 'bg-warning/15 text-warning' :
                'bg-brand-primary/10 text-brand-primary',
              )}>
                {plan.priority} priority
              </span>
              <span className="text-xs text-text-tertiary">
                Due {new Date(plan.deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </span>
            </div>

            {/* AI Reasoning */}
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">AI Reasoning</h3>
              <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                {plan.aiReasoning}
              </p>
            </div>

            {/* FIE Insights */}
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">FIE Insights</h3>
              <ul className="space-y-2">
                {plan.fieInsights.map((insight, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-accent mt-1.5 flex-shrink-0" />
                    {insight}
                  </li>
                ))}
              </ul>
            </div>

            {/* Review History */}
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">Review History</h3>
              {plan.reviewHistory.length === 0 ? (
                <p className="text-xs text-text-tertiary">No previous reviews.</p>
              ) : (
                <div className="space-y-3">
                  {plan.reviewHistory.map((entry, i) => (
                    <div key={i} className="border-l-2 border-border-default pl-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-text-primary">{entry.reviewer}</span>
                        <span className={cn(
                          'text-[10px] font-medium px-1.5 py-0.5 rounded-full capitalize',
                          entry.action === 'approved' ? 'bg-success/15 text-success' :
                          entry.action === 'rejected' ? 'bg-error/15 text-error' :
                          'bg-warning/15 text-warning',
                        )}>
                          {entry.action}
                        </span>
                      </div>
                      <p className="text-xs text-text-tertiary mt-0.5">
                        {new Date(entry.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </p>
                      {entry.notes && (
                        <p className="text-xs text-text-secondary mt-1">{entry.notes}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>

      {/* Modification Reason Modal */}
      <AnimatePresence>
        {showModModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
              onClick={() => setShowModModal(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed inset-0 z-50 flex items-center justify-center px-6"
            >
              <div className="w-full max-w-md bg-canvas-elevated rounded-[14px] border-[0.5px] border-border-default shadow-lg p-6">
                <h3 className="text-base font-semibold text-text-primary mb-1">Modification Reason</h3>
                <p className="text-sm text-text-secondary mb-4">
                  Why are you changing <span className="font-medium text-text-primary">{pendingMod?.field}</span>?
                </p>
                <textarea
                  value={modReason}
                  onChange={(e) => setModReason(e.target.value)}
                  placeholder="Enter reason for this change..."
                  rows={3}
                  className="w-full rounded-xl border border-border-default bg-canvas-sunken px-4 py-3 text-sm text-text-primary placeholder:text-text-tertiary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 resize-none"
                />
                <div className="flex justify-end gap-3 mt-4">
                  <Button variant="ghost" size="sm" onClick={() => setShowModModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" onClick={confirmModification}>
                    Confirm Change
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Reject Modal */}
      <AnimatePresence>
        {showRejectModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
              onClick={() => setShowRejectModal(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed inset-0 z-50 flex items-center justify-center px-6"
            >
              <div className="w-full max-w-md bg-canvas-elevated rounded-[14px] border-[0.5px] border-border-default shadow-lg p-6">
                <h3 className="text-base font-semibold text-text-primary mb-4">Reject Plan</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-text-secondary mb-1.5 block">Reason for rejection</label>
                    <textarea
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      placeholder="Why is this plan being rejected?"
                      rows={3}
                      className="w-full rounded-xl border border-border-default bg-canvas-sunken px-4 py-3 text-sm text-text-primary placeholder:text-text-tertiary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 resize-none"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-text-secondary mb-1.5 block">
                      Regeneration instructions <span className="text-text-tertiary">(optional)</span>
                    </label>
                    <textarea
                      value={rejectInstructions}
                      onChange={(e) => setRejectInstructions(e.target.value)}
                      placeholder="Any specific instructions for regeneration..."
                      rows={2}
                      className="w-full rounded-xl border border-border-default bg-canvas-sunken px-4 py-3 text-sm text-text-primary placeholder:text-text-tertiary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 resize-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 mt-5">
                  <Button variant="ghost" size="sm" onClick={() => setShowRejectModal(false)}>
                    Cancel
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    isLoading={submitting}
                    onClick={handleReject}
                    disabled={!rejectReason.trim()}
                  >
                    Confirm Rejection
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </NutritionistLayout>
  );
}

/* ── Sub-components ────────────────────────────────────────── */

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide">{label}</p>
      <p className="text-sm text-text-primary mt-0.5">{value}</p>
    </div>
  );
}

function EditableMealCard({
  meal,
  onEdit,
}: {
  meal: MealItem;
  onEdit: (itemId: string, field: string, oldValue: string, newValue: string) => void;
}) {
  return (
    <Card className={cn(meal.modified && 'border-l-4 border-l-warning')}>
      <CardContent className="py-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h4 className="text-sm font-medium text-text-primary">{meal.name}</h4>
            <p className="text-xs text-text-secondary mt-0.5">{meal.description}</p>
          </div>
          {meal.modified && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-warning/15 text-warning">
              Modified
            </span>
          )}
        </div>
        <div className="grid grid-cols-4 gap-3 mt-3">
          {[
            { label: 'Calories', value: String(meal.calories), field: 'calories' },
            { label: 'Protein', value: `${meal.protein}g`, field: 'protein' },
            { label: 'Carbs', value: `${meal.carbs}g`, field: 'carbs' },
            { label: 'Fat', value: `${meal.fat}g`, field: 'fat' },
          ].map((macro) => (
            <button
              key={macro.field}
              onClick={() => {
                const newVal = prompt(`Edit ${macro.label}:`, macro.value);
                if (newVal !== null && newVal !== macro.value) {
                  onEdit(meal.id, macro.field, macro.value, newVal);
                }
              }}
              className="text-center p-2 rounded-lg bg-canvas-sunken hover:bg-border-default transition-colors cursor-pointer"
            >
              <p className="text-[10px] text-text-tertiary uppercase">{macro.label}</p>
              <p className="text-sm font-medium text-text-primary mt-0.5">{macro.value}</p>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function EditableExerciseCard({
  exercise,
  onEdit,
}: {
  exercise: ExerciseItem;
  onEdit: (itemId: string, field: string, oldValue: string, newValue: string) => void;
}) {
  return (
    <Card className={cn(exercise.modified && 'border-l-4 border-l-warning')}>
      <CardContent className="py-4">
        <div className="flex items-start justify-between mb-1">
          <div>
            <h4 className="text-sm font-medium text-text-primary">{exercise.name}</h4>
            <p className="text-xs text-text-secondary mt-0.5">{exercise.notes}</p>
          </div>
          {exercise.modified && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-warning/15 text-warning">
              Modified
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <button
            onClick={() => {
              const val = prompt('Edit duration (min):', String(exercise.duration));
              if (val !== null && val !== String(exercise.duration)) {
                onEdit(exercise.id, 'duration', String(exercise.duration), val);
              }
            }}
            className="text-center p-2 rounded-lg bg-canvas-sunken hover:bg-border-default transition-colors cursor-pointer"
          >
            <p className="text-[10px] text-text-tertiary uppercase">Duration</p>
            <p className="text-sm font-medium text-text-primary mt-0.5">{exercise.duration} min</p>
          </button>
          <button
            onClick={() => {
              const val = prompt('Edit intensity:', exercise.intensity);
              if (val !== null && val !== exercise.intensity) {
                onEdit(exercise.id, 'intensity', exercise.intensity, val);
              }
            }}
            className="text-center p-2 rounded-lg bg-canvas-sunken hover:bg-border-default transition-colors cursor-pointer"
          >
            <p className="text-[10px] text-text-tertiary uppercase">Intensity</p>
            <p className="text-sm font-medium text-text-primary mt-0.5 capitalize">{exercise.intensity}</p>
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

function EditableMeditationCard({
  meditation,
  onEdit,
}: {
  meditation: MeditationItem;
  onEdit: (itemId: string, field: string, oldValue: string, newValue: string) => void;
}) {
  return (
    <Card className={cn(meditation.modified && 'border-l-4 border-l-warning')}>
      <CardContent className="py-4">
        <div className="flex items-start justify-between mb-1">
          <h4 className="text-sm font-medium text-text-primary">{meditation.name}</h4>
          {meditation.modified && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-warning/15 text-warning">
              Modified
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <button
            onClick={() => {
              const val = prompt('Edit duration (min):', String(meditation.duration));
              if (val !== null && val !== String(meditation.duration)) {
                onEdit(meditation.id, 'duration', String(meditation.duration), val);
              }
            }}
            className="text-center p-2 rounded-lg bg-canvas-sunken hover:bg-border-default transition-colors cursor-pointer"
          >
            <p className="text-[10px] text-text-tertiary uppercase">Duration</p>
            <p className="text-sm font-medium text-text-primary mt-0.5">{meditation.duration} min</p>
          </button>
          <div className="text-center p-2 rounded-lg bg-canvas-sunken">
            <p className="text-[10px] text-text-tertiary uppercase">Type</p>
            <p className="text-sm font-medium text-text-primary mt-0.5 capitalize">{meditation.type}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
