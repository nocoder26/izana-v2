'use client';

import type { ChatMessage, CardData } from '../types';
import CheckInCard from './CheckInCard';
import PlanCard from './PlanCard';
import SummaryCard from './SummaryCard';
import TransitionCard from './TransitionCard';
import CelebrationCard from './CelebrationCard';
import BloodworkCard from './BloodworkCard';
import PlanStatusCard from './PlanStatusCard';

interface ChatCardProps {
  message: ChatMessage;
  onAction?: (action: string, payload?: unknown) => void;
}

export default function ChatCard({ message, onAction }: ChatCardProps) {
  const data = message.cardData as CardData | undefined;
  if (!data) return null;

  switch (message.messageType) {
    case 'checkin_card':
      return (
        <CheckInCard
          data={data as import('../types').CheckInCardData}
          onAction={onAction}
        />
      );
    case 'plan_card':
      return (
        <PlanCard
          data={data as import('../types').PlanCardData}
          onAction={onAction}
        />
      );
    case 'summary_card':
      return (
        <SummaryCard
          data={data as import('../types').SummaryCardData}
        />
      );
    case 'transition_card':
      return (
        <TransitionCard
          data={data as import('../types').TransitionCardData}
          onAction={onAction}
        />
      );
    case 'celebration_card':
      return (
        <CelebrationCard
          data={data as import('../types').CelebrationCardData}
        />
      );
    case 'bloodwork_card':
      return (
        <BloodworkCard
          data={data as import('../types').BloodworkCardData}
        />
      );
    case 'plan_status_card':
      return (
        <PlanStatusCard
          data={data as import('../types').PlanStatusCardData}
          onAction={onAction}
        />
      );
    default:
      return null;
  }
}
