import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}

// Логирование для отладки
const log = (msg: string, data?: any) => {
  console.log(`[AUTH STORE] ${msg}`, data || '');
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token, user) => {
        log('login() called', { token: token.substring(0, 20) + '...', user });
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
        set({ token, user, isAuthenticated: true });
        log('After login - isAuthenticated:', true);
      },
      logout: () => {
        log('logout() called');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        set({ user: null, token: null, isAuthenticated: false });
        log('After logout - isAuthenticated:', false);
      },
      updateUser: (user) => {
        log('updateUser() called', user);
        localStorage.setItem('user', JSON.stringify(user));
        set({ user });
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        log('onRehydrateStorage - state:', state);
      }
    }
  )
);

// Логируем при загрузке
console.log('[AUTH STORE] Module loaded, checking localStorage...');
console.log('[AUTH STORE] token:', localStorage.getItem('token') ? 'exists' : 'null');
console.log('[AUTH STORE] user:', localStorage.getItem('user') ? 'exists' : 'null');