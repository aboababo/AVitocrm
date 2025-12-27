import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; first_name: string; last_name: string }) =>
    api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout')
};

export const chatsApi = {
  getAll: (params?: { page?: number; size?: number; status?: string; search?: string }) =>
    api.get('/chats', { params }),
  getOne: (id: number) => api.get(`/chats/${id}`),
  create: (data: { client_name: string; client_phone?: string; priority?: string }) =>
    api.post('/chats', data),
  update: (id: number, data: any) => api.put(`/chats/${id}`, data),
  delete: (id: number) => api.delete(`/chats/${id}`),
  updateStatus: (id: number, status: string) =>
    api.patch(`/chats/${id}/status`, { status }),
  getMessages: (chatId: number, page = 1, size = 50) =>
    api.get(`/chats/${chatId}/messages`, { params: { page, size } }),
  sendMessage: (chatId: number, content: string, messageType = 'text') =>
    api.post(`/chats/${chatId}/messages`, { chat_id: chatId, content, message_type: messageType }),
  markRead: (chatId: number, messageIds: number[]) =>
    api.patch(`/chats/${chatId}/messages/read`, { message_ids: messageIds }),
  getStats: () => api.get('/chats/stats')
};

export const settingsApi = {
  getSystemSettings: () => api.get('/settings/system'),
  createSystemSetting: (data: { key: string; value: any; type?: string; description?: string }) =>
    api.post('/settings/system', data),
  updateSystemSetting: (id: number, data: { value?: any; description?: string }) =>
    api.put(`/settings/system/${id}`, data),
  deleteSystemSetting: (id: number) => api.delete(`/settings/system/${id}`),
  getKPISettings: () => api.get('/settings/kpi-settings'),
  getDashboardStats: () => api.get('/settings/dashboard-stats'),
  getAvailableVariables: () => api.get('/settings/available-variables')
};

export default api;
