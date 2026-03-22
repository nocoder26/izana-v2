'use client';

import { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/* ── Types ────────────────────────────────────────────────────── */

type TreatmentType = 'IVF' | 'IUI' | 'Natural' | 'Egg freezing' | 'Exploring';
type AgeRange = '18-25' | '26-30' | '31-35' | '36-40' | '41+';

interface OnboardingData {
  treatmentType: TreatmentType | null;
  currentPhase: string | null;
  dayInPhase: number | null;
  ageRange: AgeRange | null;
  healthConditions: string[];
  activityLevel: string | null;
  smoking: string | null;
  alcohol: string | null;
  sleep: string | null;
  stress: string | null;
  allergies: string[];
  dietaryStyle: string | null;
  cuisines: string[];
  exercisePrefs: string[];
  exerciseTime: string | null;
}

interface ConversationalOnboardingProps {
  onComplete: (data: OnboardingData) => void;
}

/* ── Phase options per treatment type ─────────────────────────── */

const PHASE_OPTIONS: Record<TreatmentType, string[]> = {
  IVF: ['Baseline', 'Stims', 'Retrieval', 'Transfer', 'TWW', 'Between cycles'],
  IUI: ['Medication', 'Monitoring', 'Insemination', 'TWW', 'Between cycles'],
  Natural: ['Follicular', 'Ovulation', 'Luteal', 'TWW'],
  'Egg freezing': ['Baseline', 'Stims', 'Retrieval', 'Recovery'],
  Exploring: ['Just starting research', 'Choosing a clinic', 'Waiting for appointment'],
};

/** Phases that show a day-in-phase number picker */
const DAY_TRACKABLE_PHASES = new Set([
  'Stims', 'Baseline', 'TWW', 'Medication',
]);

/* ── Chip component ──────────────────────────────────────────── */

function Chip({
  label,
  selected,
  onToggle,
  emoji,
}: {
  label: string;
  selected: boolean;
  onToggle: () => void;
  emoji?: string;
}) {
  return (
    <motion.button
      onClick={onToggle}
      whileTap={{ scale: 0.95 }}
      transition={{ duration: 0.15 }}
      className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-all border ${
        selected
          ? 'bg-brand-primary-bg text-brand-primary border-brand-primary/40'
          : 'bg-canvas-elevated text-text-secondary border-border-default hover:border-brand-primary/20'
      }`}
    >
      {emoji && <span>{emoji}</span>}
      {label}
    </motion.button>
  );
}

/* ── Number selector (for day in phase) ──────────────────────── */

function NumberSelector({
  value,
  onChange,
  max,
}: {
  value: number | null;
  onChange: (n: number) => void;
  max: number;
}) {
  const options = Array.from({ length: max }, (_, i) => i + 1);
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((n) => {
        const label = n === max ? `${n}+` : String(n);
        return (
          <Chip
            key={n}
            label={label}
            selected={value === n}
            onToggle={() => onChange(n)}
          />
        );
      })}
    </div>
  );
}

/* ── Main component ──────────────────────────────────────────── */

export default function ConversationalOnboarding({
  onComplete,
}: ConversationalOnboardingProps) {
  const [round, setRound] = useState(1);
  const [showConfetti, setShowConfetti] = useState(false);

  const [data, setData] = useState<OnboardingData>({
    treatmentType: null,
    currentPhase: null,
    dayInPhase: null,
    ageRange: null,
    healthConditions: [],
    activityLevel: null,
    smoking: null,
    alcohol: null,
    sleep: null,
    stress: null,
    allergies: [],
    dietaryStyle: null,
    cuisines: [],
    exercisePrefs: [],
    exerciseTime: null,
  });

  /* ── Helpers for multi-select with "None" logic ─── */

  const toggleMulti = useCallback(
    (
      field: keyof OnboardingData,
      value: string,
      isNone: boolean = false,
    ) => {
      setData((prev) => {
        const current = prev[field] as string[];
        if (isNone) {
          // "None" clears all others
          return { ...prev, [field]: current.includes(value) ? [] : [value] };
        }
        // Regular option: remove "None" if present, toggle this value
        const withoutNone = current.filter((v) => v !== 'None');
        const hasValue = withoutNone.includes(value);
        const next = hasValue
          ? withoutNone.filter((v) => v !== value)
          : [...withoutNone, value];
        return { ...prev, [field]: next };
      });
    },
    [],
  );

  const toggleSingle = useCallback(
    (field: keyof OnboardingData, value: string) => {
      setData((prev) => ({ ...prev, [field]: prev[field] === value ? null : value }));
    },
    [],
  );

  /* ── Validation per round ─── */

  const isRound1Valid = useMemo(() => {
    return data.treatmentType !== null && data.ageRange !== null;
  }, [data.treatmentType, data.ageRange]);

  const isRound2Valid = useMemo(() => {
    return (
      data.healthConditions.length > 0 &&
      data.activityLevel !== null &&
      data.smoking !== null &&
      data.alcohol !== null &&
      data.sleep !== null &&
      data.stress !== null
    );
  }, [data.healthConditions, data.activityLevel, data.smoking, data.alcohol, data.sleep, data.stress]);

  const isRound3Valid = useMemo(() => {
    return (
      data.allergies.length > 0 &&
      data.dietaryStyle !== null &&
      data.cuisines.length >= 1 &&
      data.exercisePrefs.length >= 1 &&
      data.exerciseTime !== null
    );
  }, [data.allergies, data.dietaryStyle, data.cuisines, data.exercisePrefs, data.exerciseTime]);

  /* ── Confetti on finish ─── */

  const handleFinish = useCallback(async () => {
    setShowConfetti(true);

    // Dynamic import to avoid SSR issues
    const confetti = (await import('canvas-confetti')).default;
    confetti({
      particleCount: 120,
      spread: 80,
      origin: { y: 0.7 },
      colors: ['#4A3D8F', '#C4956A', '#7BA68E', '#8B7FC7'],
    });

    setTimeout(() => {
      onComplete(data);
    }, 1500);
  }, [data, onComplete]);

  /* ── Show phase options based on treatment ─── */

  const showDaySelector = useMemo(() => {
    return data.currentPhase && DAY_TRACKABLE_PHASES.has(data.currentPhase);
  }, [data.currentPhase]);

  /* ── Render ─── */

  return (
    <div className="flex flex-col h-full">
      {/* Progress bar */}
      <div className="px-5 pt-4 pb-2">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-secondary font-medium">
            {round} of 3
          </span>
          <span className="text-xs text-text-tertiary">
            {round === 1
              ? 'Treatment & You'
              : round === 2
                ? 'Lifestyle'
                : 'Food & Movement'}
          </span>
        </div>
        <div className="h-1 w-full rounded-full bg-canvas-sunken overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-brand-primary"
            initial={{ width: '0%' }}
            animate={{ width: `${(round / 3) * 100}%` }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          />
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto px-5 pb-24">
        <AnimatePresence mode="wait">
          {/* ────── Round 1: Treatment & You ────── */}
          {round === 1 && (
            <motion.div
              key="r1"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="space-y-5 pt-3"
            >
              {/* Izana message */}
              <div className="flex items-start gap-2">
                <div className="izana-avatar flex items-center justify-center" style={{ width: 28, height: 28 }}>
                  <span className="text-white text-xs">✦</span>
                </div>
                <div className="izana-bubble">
                  <p className="text-sm">
                    Let&apos;s personalise your experience! First, tell me about your treatment journey.
                  </p>
                </div>
              </div>

              {/* Card */}
              <div className="bg-canvas-elevated rounded-2xl border border-border-default p-5 space-y-5">
                {/* Treatment type */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Treatment type
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(
                      [
                        ['IVF', '🔬'],
                        ['IUI', '💉'],
                        ['Natural', '🌱'],
                        ['Egg freezing', '❄️'],
                        ['Exploring', '🔍'],
                      ] as [TreatmentType, string][]
                    ).map(([t, emoji]) => (
                      <Chip
                        key={t}
                        label={t}
                        emoji={emoji}
                        selected={data.treatmentType === t}
                        onToggle={() =>
                          setData((prev) => ({
                            ...prev,
                            treatmentType: prev.treatmentType === t ? null : t,
                            currentPhase: null,
                            dayInPhase: null,
                          }))
                        }
                      />
                    ))}
                  </div>
                </div>

                {/* Current phase (conditional) */}
                {data.treatmentType && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    transition={{ duration: 0.2 }}
                  >
                    <p className="text-xs font-medium text-text-secondary mb-2">
                      Current phase
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {PHASE_OPTIONS[data.treatmentType].map((phase) => (
                        <Chip
                          key={phase}
                          label={phase}
                          selected={data.currentPhase === phase}
                          onToggle={() =>
                            setData((prev) => ({
                              ...prev,
                              currentPhase: prev.currentPhase === phase ? null : phase,
                              dayInPhase: null,
                            }))
                          }
                        />
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* Day in phase (conditional) */}
                {showDaySelector && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    transition={{ duration: 0.2 }}
                  >
                    <p className="text-xs font-medium text-text-secondary mb-2">
                      Day in phase
                    </p>
                    <NumberSelector
                      value={data.dayInPhase}
                      onChange={(n) => setData((prev) => ({ ...prev, dayInPhase: n }))}
                      max={15}
                    />
                  </motion.div>
                )}

                {/* Age range */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Age range
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(['18-25', '26-30', '31-35', '36-40', '41+'] as AgeRange[]).map(
                      (age) => (
                        <Chip
                          key={age}
                          label={age}
                          selected={data.ageRange === age}
                          onToggle={() =>
                            setData((prev) => ({
                              ...prev,
                              ageRange: prev.ageRange === age ? null : age,
                            }))
                          }
                        />
                      ),
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ────── Round 2: Lifestyle ────── */}
          {round === 2 && (
            <motion.div
              key="r2"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="space-y-5 pt-3"
            >
              <div className="flex items-start gap-2">
                <div className="izana-avatar flex items-center justify-center" style={{ width: 28, height: 28 }}>
                  <span className="text-white text-xs">✦</span>
                </div>
                <div className="izana-bubble">
                  <p className="text-sm">
                    Great! Now let&apos;s understand your lifestyle so I can tailor recommendations.
                  </p>
                </div>
              </div>

              <div className="bg-canvas-elevated rounded-2xl border border-border-default p-5 space-y-5">
                {/* Health conditions */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Health conditions
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['PCOS', 'Endometriosis', 'Thyroid', 'Diabetes', 'Autoimmune', 'None'].map(
                      (c) => (
                        <Chip
                          key={c}
                          label={c}
                          selected={data.healthConditions.includes(c)}
                          onToggle={() => toggleMulti('healthConditions', c, c === 'None')}
                        />
                      ),
                    )}
                  </div>
                </div>

                {/* Activity level */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Activity level
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['Low', 'Moderate', 'Active'].map((l) => (
                      <Chip
                        key={l}
                        label={l}
                        selected={data.activityLevel === l}
                        onToggle={() => toggleSingle('activityLevel', l)}
                      />
                    ))}
                  </div>
                </div>

                {/* Smoking */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Smoking
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['Never', 'Former', 'Current'].map((s) => (
                      <Chip
                        key={s}
                        label={s}
                        selected={data.smoking === s}
                        onToggle={() => toggleSingle('smoking', s)}
                      />
                    ))}
                  </div>
                </div>

                {/* Alcohol */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Alcohol
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['None', 'Occasional', 'Moderate'].map((a) => (
                      <Chip
                        key={a}
                        label={a}
                        selected={data.alcohol === a}
                        onToggle={() => toggleSingle('alcohol', a)}
                      />
                    ))}
                  </div>
                </div>

                {/* Sleep */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Sleep
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['<6h', '6-7h', '7-8h', '8-9h', '>9h'].map((s) => (
                      <Chip
                        key={s}
                        label={s}
                        selected={data.sleep === s}
                        onToggle={() => toggleSingle('sleep', s)}
                      />
                    ))}
                  </div>
                </div>

                {/* Stress */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Stress
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['Rarely', 'Sometimes', 'Often', 'Always'].map((s) => (
                      <Chip
                        key={s}
                        label={s}
                        selected={data.stress === s}
                        onToggle={() => toggleSingle('stress', s)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ────── Round 3: Food & Movement ────── */}
          {round === 3 && (
            <motion.div
              key="r3"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
              className="space-y-5 pt-3"
            >
              <div className="flex items-start gap-2">
                <div className="izana-avatar flex items-center justify-center" style={{ width: 28, height: 28 }}>
                  <span className="text-white text-xs">✦</span>
                </div>
                <div className="izana-bubble">
                  <p className="text-sm">
                    Almost done! Let&apos;s learn about your food preferences and how you like to move.
                  </p>
                </div>
              </div>

              <div className="bg-canvas-elevated rounded-2xl border border-border-default p-5 space-y-5">
                {/* Allergies */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Allergies
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['Dairy', 'Gluten', 'Nuts', 'Soy', 'Eggs', 'Shellfish', 'None'].map(
                      (a) => (
                        <Chip
                          key={a}
                          label={a}
                          selected={data.allergies.includes(a)}
                          onToggle={() => toggleMulti('allergies', a, a === 'None')}
                        />
                      ),
                    )}
                  </div>
                </div>

                {/* Dietary style */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Dietary style
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Vegetarian', 'Vegan', 'Pescatarian', 'Keto',
                      'Halal', 'Kosher', 'No restrictions',
                    ].map((d) => (
                      <Chip
                        key={d}
                        label={d}
                        selected={data.dietaryStyle === d}
                        onToggle={() => toggleSingle('dietaryStyle', d)}
                      />
                    ))}
                  </div>
                </div>

                {/* Cuisines (multi-select, at least 1) */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Cuisines you enjoy <span className="text-text-tertiary">(pick at least 1)</span>
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Mediterranean', 'Indian', 'Asian', 'Latin',
                      'Middle Eastern', 'Western', 'African',
                    ].map((c) => (
                      <Chip
                        key={c}
                        label={c}
                        selected={data.cuisines.includes(c)}
                        onToggle={() => toggleMulti('cuisines', c)}
                      />
                    ))}
                  </div>
                </div>

                {/* Exercise preferences (multi-select, at least 1) */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Exercise preferences{' '}
                    <span className="text-text-tertiary">(pick at least 1)</span>
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Yoga', 'Walking', 'Pilates', 'Swimming',
                      'Light gym', 'Stretching', 'Dance',
                    ].map((e) => (
                      <Chip
                        key={e}
                        label={e}
                        selected={data.exercisePrefs.includes(e)}
                        onToggle={() => toggleMulti('exercisePrefs', e)}
                      />
                    ))}
                  </div>
                </div>

                {/* Exercise time */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Exercise time per session
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {['10 min', '20 min', '30 min', '45+ min'].map((t) => (
                      <Chip
                        key={t}
                        label={t}
                        selected={data.exerciseTime === t}
                        onToggle={() => toggleSingle('exerciseTime', t)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ────── Completion ────── */}
          {showConfetti && (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, type: 'spring' }}
              className="flex flex-col items-center justify-center py-12 gap-4"
            >
              <div className="izana-avatar flex items-center justify-center" style={{ width: 56, height: 56 }}>
                <span className="text-white text-2xl">✦</span>
              </div>
              <h2 className="font-serif text-xl text-text-primary text-center">
                You&apos;re all set!
              </h2>
              <p className="text-sm text-text-secondary text-center px-6">
                I&apos;ve built your personalised fertility wellness profile.
                Let&apos;s begin your journey together.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ─── Bottom action button ─── */}
      {!showConfetti && (
        <div className="fixed bottom-0 left-0 right-0 px-5 pb-6 pt-3 bg-gradient-to-t from-canvas-base via-canvas-base to-transparent safe-area-bottom">
          {round < 3 ? (
            <button
              onClick={() => setRound(round + 1)}
              disabled={round === 1 ? !isRound1Valid : !isRound2Valid}
              className={`w-full py-3.5 rounded-full text-sm font-medium transition-all ${
                (round === 1 && isRound1Valid) || (round === 2 && isRound2Valid)
                  ? 'bg-brand-primary text-white active:scale-[0.97]'
                  : 'bg-canvas-sunken text-text-tertiary cursor-not-allowed'
              }`}
            >
              Next round →
            </button>
          ) : (
            <button
              onClick={handleFinish}
              disabled={!isRound3Valid}
              className={`w-full py-3.5 rounded-full text-sm font-medium transition-all ${
                isRound3Valid
                  ? 'bg-brand-primary text-white active:scale-[0.97]'
                  : 'bg-canvas-sunken text-text-tertiary cursor-not-allowed'
              }`}
            >
              Finish setup ✓
            </button>
          )}
        </div>
      )}
    </div>
  );
}
