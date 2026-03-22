'use client';

import { useState } from 'react';
import ChatInterface from '@/components/chat/ChatInterface';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';
import type { ChapterInfo } from '@/components/chat/types';

// In production, fetch from API; using placeholder data for now
const MOCK_CHAPTER: ChapterInfo = {
  phaseName: 'stims',
  day: 8,
  streak: 2,
};

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState<TabId>('today');

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    // In production, use Next.js router to navigate
    if (tab === 'journey') {
      window.location.href = '/journey';
    } else if (tab === 'you') {
      window.location.href = '/profile';
    }
  };

  return (
    <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Main chat area — takes all available space above bottom nav */}
      <div className="flex-1 min-h-0 pb-[52px]">
        <ChatInterface chapter={MOCK_CHAPTER} />
      </div>

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
