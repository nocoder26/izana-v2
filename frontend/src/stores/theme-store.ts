import { create } from 'zustand';
import { type Theme, setTheme as applyAndPersistTheme, getTheme } from '@/lib/theme';

type ThemeStore = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

export const useThemeStore = create<ThemeStore>((set) => ({
  theme: typeof window !== 'undefined' ? getTheme() : 'system',
  setTheme: (theme: Theme) => {
    applyAndPersistTheme(theme);
    set({ theme });
  },
}));
