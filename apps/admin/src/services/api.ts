import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;

// API methods
export const userApi = {
  list: (params?: Record<string, unknown>) => api.get('/admin/users', { params }),
  detail: (id: string) => api.get(`/admin/users/${id}`),
  ban: (id: string) => api.post(`/admin/users/${id}/ban`),
  unban: (id: string) => api.post(`/admin/users/${id}/unban`),
};

export const characterApi = {
  list: () => api.get('/characters'),
  update: (id: string, data: Record<string, unknown>) => api.put(`/characters/${id}`, data),
};

export const memoryApi = {
  list: (params?: Record<string, unknown>) => api.get('/admin/memories', { params }),
  delete: (id: string) => api.delete(`/admin/memories/${id}`),
};

export const dashboardApi = {
  stats: () => api.get('/admin/dashboard/stats'),
  trends: (params?: Record<string, unknown>) => api.get('/admin/dashboard/trends', { params }),
};
