import { create } from 'zustand';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  messageType: string;
  cardData?: Record<string, unknown>;
  sources?: Array<{ title: string; url: string; snippet?: string }>;
  followUps?: string[];
  createdAt: string;
};

type ChatStore = {
  messages: ChatMessage[];
  isStreaming: boolean;
  addMessage: (msg: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  setStreaming: (val: boolean) => void;
  clearMessages: () => void;
};

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isStreaming: false,

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...patch } : m,
      ),
    })),

  setStreaming: (val) => set({ isStreaming: val }),

  clearMessages: () => set({ messages: [] }),
}));
