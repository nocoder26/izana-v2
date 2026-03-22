'use client';

import { useState, useEffect, useCallback } from 'react';
import ChatInterface from '@/components/chat/ChatInterface';
import ConversationalOnboarding from '@/components/onboarding/ConversationalOnboarding';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';
import { apiGet, apiPost, ApiError } from '@/lib/api-client';
import type { ChapterInfo } from '@/components/chat/types';

/* ── Treatment type mapping (UI label -> backend enum) ──────── */

const TREATMENT_TYPE_MAP: Record<string, string> = {
  IVF: 'ivf',
  IUI: 'iui',
  Natural: 'natural',
  'Egg freezing': 'egg_freezing',
  Exploring: 'exploring',
};

/* ── Phase mapping (UI label -> backend enum) ────────────────── */

const PHASE_MAP: Record<string, string> = {
  // IVF
  Baseline: 'initial_consultation',
  Stims: 'ovarian_stimulation',
  Retrieval: 'egg_retrieval',
  Transfer: 'embryo_transfer',
  TWW: 'two_week_wait',
  'Between cycles': 'outcome',
  // IUI
  Medication: 'ovarian_stimulation',
  Monitoring: 'monitoring',
  Insemination: 'insemination',
  // Natural
  Follicular: 'preconception',
  Ovulation: 'fertile_window',
  Luteal: 'two_week_wait',
  // Egg freezing
  Recovery: 'recovery',
  // Exploring
  'Just starting research': 'learning',
  'Choosing a clinic': 'lifestyle_optimisation',
  'Waiting for appointment': 'diagnostic_testing',
};

type PageState = 'loading' | 'onboarding' | 'chat';

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState<TabId>('today');
  const [pageState, setPageState] = useState<PageState>('loading');
  const [chapter, setChapter] = useState<ChapterInfo>({
    phaseName: 'Getting started',
    day: 1,
    streak: 0,
  });

  /* ── Check whether onboarding is needed ──────────────────── */

  useEffect(() => {
    let cancelled = false;

    async function checkOnboarding() {
      try {
        // Check if the user has COMPLETED onboarding (not just has a profile row)
        const profile = await apiGet<{
          allergies: string[];
          exercise_preferences: string[];
          health_conditions: string[];
          age_range: string | null;
        }>('/nutrition/wellness-profile');
        if (cancelled) return;

        // Profile exists but check if onboarding was actually completed
        // (signup creates empty profile — onboarding fills it)
        const hasCompletedOnboarding = Boolean(
          (profile.age_range && profile.age_range !== null)
          || (profile.exercise_preferences && profile.exercise_preferences.length > 0)
          || (profile.allergies && profile.allergies.length > 0)
        );

        if (hasCompletedOnboarding) {
          // User completed onboarding — load chat
          await fetchActiveChapter();
          if (!cancelled) setPageState('chat');
        } else {
          // Profile exists but empty — show onboarding
          if (!cancelled) setPageState('onboarding');
        }
      } catch (err) {
        if (cancelled) return;
        // Any error (404, 401, network) — show onboarding
        setPageState('onboarding');
      }
    }

    checkOnboarding();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Fetch active chapter from backend ───────────────────── */

  const fetchActiveChapter = useCallback(async () => {
    try {
      const data = await apiGet<{
        phase: string;
        day: number;
        streak: number;
      }>('/chapters/active');
      setChapter({
        phaseName: data.phase,
        day: data.day,
        streak: data.streak,
      });
    } catch {
      // No active chapter yet — keep the default "Getting started"
    }
  }, []);

  /* ── Onboarding completion handler ───────────────────────── */

  const handleOnboardingComplete = useCallback(
    async (data: {
      treatmentType: string | null;
      currentPhase: string | null;
      dayInPhase: number | null;
      ageRange: string | null;
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
    }) => {
      try {
        // 1. Save wellness profile
        await apiPost('/nutrition/wellness-profile', {
          allergies: data.allergies.filter((a) => a !== 'None'),
          dietary_restrictions: data.allergies.filter((a) => a !== 'None').map((a) => `${a.toLowerCase()}-free`),
          food_preferences: [data.dietaryStyle, ...data.cuisines].filter(Boolean),
          exercise_preferences: data.exercisePrefs,
          health_conditions: data.healthConditions.filter((c) => c !== 'None'),
          fitness_level: data.activityLevel?.toLowerCase() || 'moderate',
          smoking_status: data.smoking?.toLowerCase() || 'never',
          alcohol_consumption: data.alcohol?.toLowerCase() || 'none',
          sleep_duration: data.sleep || '7-8h',
          stress_level: data.stress?.toLowerCase() || 'sometimes',
          age_range: data.ageRange || '31-35',
          exercise_time_minutes: parseInt(data.exerciseTime || '20') || 20,
        });
      } catch {
        // Continue even if profile save fails — journey creation matters too
      }

      try {
        // 2. Create the treatment journey
        const treatmentType =
          TREATMENT_TYPE_MAP[data.treatmentType ?? ''] ?? 'exploring';
        const initialPhase = data.currentPhase
          ? PHASE_MAP[data.currentPhase] ?? undefined
          : undefined;

        await apiPost('/journey', {
          treatment_type: treatmentType,
          initial_phase: initialPhase,
        });
      } catch {
        // Journey might already exist (409) — that's okay
      }

      // 3. Fetch the active chapter and switch to chat
      await fetchActiveChapter();
      setPageState('chat');
    },
    [fetchActiveChapter],
  );

  /* ── Tab navigation ──────────────────────────────────────── */

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    if (tab === 'journey') {
      window.location.href = '/journey';
    } else if (tab === 'you') {
      window.location.href = '/profile';
    }
  };

  /* ── Render ──────────────────────────────────────────────── */

  if (pageState === 'loading') {
    return (
      <div className="flex items-center justify-center h-dvh bg-canvas-base">
        <div className="flex flex-col items-center gap-3">
          <div className="izana-avatar flex items-center justify-center" style={{ width: 40, height: 40 }}>
            <span className="text-white text-lg">&#10022;</span>
          </div>
          <p className="text-sm text-text-tertiary">Loading...</p>
        </div>
      </div>
    );
  }

  if (pageState === 'onboarding') {
    return (
      <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
        <ConversationalOnboarding onComplete={handleOnboardingComplete} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Main chat area */}
      <div className="flex-1 min-h-0 pb-[52px]">
        <ChatInterface chapter={chapter} />
      </div>

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
