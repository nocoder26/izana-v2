/* ─── Chat Domain Types ─── */

export type MessageType =
  | 'text'
  | 'checkin_card'
  | 'plan_card'
  | 'summary_card'
  | 'transition_card'
  | 'celebration_card'
  | 'bloodwork_card'
  | 'plan_status_card';

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  messageType: MessageType;
  cardData?: CardData;
  sources?: Source[];
  suggestedQuestions?: string[];
  followUps?: string[];
  timestamp: string;
  createdAt: string;
  day?: number;
  isStreaming?: boolean;
}

export interface Source {
  id: string;
  title: string;
  url?: string;
}

/* ─── Card Data Types ─── */

export type CardData =
  | CheckInCardData
  | PlanCardData
  | SummaryCardData
  | TransitionCardData
  | CelebrationCardData
  | BloodworkCardData
  | PlanStatusCardData;

export interface CheckInCardData {
  type: 'checkin';
  prompt: string;
  submitted?: boolean;
  selectedMood?: string;
}

export interface Meal {
  id: string;
  label: string;
  emoji: string;
  description: string;
  done: boolean;
}

export interface ExerciseItem {
  id: string;
  title: string;
  duration: string;
  videoUrl: string;
  thumbnailUrl?: string;
  done: boolean;
}

export interface MeditationItem {
  id: string;
  title: string;
  duration: string;
  audioUrl: string;
  done: boolean;
}

export interface PlanCardData {
  type: 'plan';
  meals: Meal[];
  exercise: ExerciseItem;
  meditation: MeditationItem;
  progress: number; // 0-1
}

export interface SummaryLineItem {
  label: string;
  value: string;
  status: 'done' | 'skipped' | 'partial';
}

export interface SummaryCardData {
  type: 'summary';
  day: number;
  items: SummaryLineItem[];
  points: number;
  streakDays: number;
}

export interface TransitionOption {
  id: string;
  label: string;
}

export interface TransitionCardData {
  type: 'transition';
  day: number;
  message: string;
  options: TransitionOption[];
}

export interface CelebrationCardData {
  type: 'celebration';
  title: string;
  subtitle?: string;
}

export interface Biomarker {
  id: string;
  name: string;
  value: number;
  unit: string;
  status: 'normal' | 'high' | 'low';
  referenceRange: string;
}

export interface BloodworkCardData {
  type: 'bloodwork';
  date: string;
  biomarkers: Biomarker[];
}

export type PlanReviewStatus = 'created' | 'in_review' | 'approved';

export interface PlanStatusStep {
  label: string;
  time?: string;
  status: 'done' | 'active' | 'pending';
}

export interface PlanStatusCardData {
  type: 'plan_status';
  steps: PlanStatusStep[];
  currentStatus: PlanReviewStatus;
}

/* ─── Chapter / Phase types ─── */

export interface ChapterInfo {
  phaseName: string;
  day: number;
  streak: number;
}

/* ─── Journey types ─── */

export type PhaseStatus = 'completed' | 'active' | 'upcoming';

export interface JourneyPhase {
  id: string;
  name: string;
  status: PhaseStatus;
  day?: number;
  totalDays?: number;
}

/* ─── Profile types ─── */

export interface UserProfile {
  pseudonym: string;
  avatarUrl?: string;
  treatmentType: string;
  points: number;
  streak: number;
  badges: number;
}
