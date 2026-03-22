import { create } from 'zustand';

type UserStore = {
  userId: string | null;
  pseudonym: string | null;
  avatar: string | null;
  isAuthenticated: boolean;
  setUser: (user: { userId: string; pseudonym: string; avatar: string }) => void;
  clearUser: () => void;
};

export const useUserStore = create<UserStore>((set) => ({
  userId: null,
  pseudonym: null,
  avatar: null,
  isAuthenticated: false,

  setUser: (user) =>
    set({
      userId: user.userId,
      pseudonym: user.pseudonym,
      avatar: user.avatar,
      isAuthenticated: true,
    }),

  clearUser: () =>
    set({
      userId: null,
      pseudonym: null,
      avatar: null,
      isAuthenticated: false,
    }),
}));
