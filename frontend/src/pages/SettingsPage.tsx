import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { User, Bell, Shield, Palette, Database, Save, Edit, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { settingsApi, authApi } from '../services/api';

export default function SettingsPage() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [editingSetting, setEditingSetting] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');

  const { data: systemSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: async () => {
      const response = await settingsApi.getSystemSettings();
      return response.data;
    },
    enabled: user?.is_superuser || false,
    retry: false
  });

  const { data: dashboardStats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await settingsApi.getDashboardStats();
      return response.data;
    },
    enabled: user?.is_superuser || false,
    retry: false
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => 
      settingsApi.updateSystemSetting(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
      setEditingSetting(null);
      toast.success('Настройка обновлена');
    },
    onError: () => toast.error('Ошибка обновления настройки')
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => settingsApi.deleteSystemSetting(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
      toast.success('Настройка удалена');
    },
    onError: () => toast.error('Ошибка удаления настройки')
  });

  const handleEdit = (setting: any) => {
    setEditingSetting(setting.id);
    setEditValue(setting.value);
  };

  const handleSave = (id: number) => {
    updateMutation.mutate({ id, data: { value: editValue } });
  };

  const handleCancel = () => {
    setEditingSetting(null);
    setEditValue('');
  };

  const sections = [
    {
      title: 'Профиль',
      icon: User,
      items: [
        { label: 'Редактировать профиль', description: 'Имя, email, телефон' },
        { label: 'Смена пароля', description: 'Обновить пароль' },
        { label: 'Аватар', description: 'Загрузить фото' }
      ]
    },
    {
      title: 'Уведомления',
      icon: Bell,
      items: [
        { label: 'Email уведомления', description: 'Получать на почту' },
        { label: 'Push уведомления', description: 'Браузерные уведомления' }
      ]
    },
    {
      title: 'Безопасность',
      icon: Shield,
      items: [
        { label: 'Двухфакторная аутентификация', description: 'Дополнительная защита' },
        { label: 'История входов', description: 'Просмотр активности' }
      ]
    },
    {
      title: 'Внешний вид',
      icon: Palette,
      items: [
        { label: 'Тема', description: 'Светлая/тёмная' },
        { label: 'Язык', description: 'Русский/English' }
      ]
    }
  ];

  const settings = systemSettings?.settings || [];

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Настройки</h1>
      <p className="text-gray-600 mb-8">Управление аккаунтом и приложением</p>

      {/* User card */}
      <div className="bg-white rounded-xl p-6 shadow-sm mb-8">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
            <span className="text-white text-xl font-medium">
              {user?.full_name?.charAt(0) || 'U'}
            </span>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{user?.full_name || 'Пользователь'}</h3>
            <p className="text-gray-600">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* System Settings (Admin only) */}
      {user?.is_superuser && (
        <div className="bg-white rounded-xl shadow-sm mb-8">
          <div className="p-4 border-b flex items-center">
            <Database className="w-5 h-5 text-blue-600 mr-3" />
            <h2 className="font-semibold text-gray-900">Системные настройки</h2>
          </div>
          <div className="divide-y">
            {settingsLoading ? (
              <div className="p-8 text-center text-gray-500">Загрузка...</div>
            ) : settings.length === 0 ? (
              <div className="p-8 text-center text-gray-500">Нет системных настроек</div>
            ) : (
              settings.map((setting: any) => (
                <div key={setting.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{setting.key}</p>
                      <p className="text-sm text-gray-500">{setting.description || 'Нет описания'}</p>
                      {editingSetting === setting.id ? (
                        <div className="mt-2 flex gap-2">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                            placeholder="Значение"
                          />
                          <button
                            onClick={() => handleSave(setting.id)}
                            disabled={updateMutation.isPending}
                            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                          <button
                            onClick={handleCancel}
                            className="px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
                          >
                            Отмена
                          </button>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-700 mt-1">Значение: <code className="bg-gray-100 px-2 py-0.5 rounded">{setting.value}</code></p>
                      )}
                    </div>
                    {editingSetting !== setting.id && (
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleEdit(setting)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                          title="Редактировать"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('Удалить настройку?')) {
                              deleteMutation.mutate(setting.id);
                            }
                          }}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                          title="Удалить"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Dashboard Stats (Admin only) */}
      {user?.is_superuser && dashboardStats && (
        <div className="bg-white rounded-xl shadow-sm mb-8">
          <div className="p-4 border-b flex items-center">
            <Database className="w-5 h-5 text-blue-600 mr-3" />
            <h2 className="font-semibold text-gray-900">Статистика системы</h2>
          </div>
          <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600">Пользователей</p>
              <p className="text-2xl font-bold text-gray-900">{dashboardStats?.users?.total || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Активных</p>
              <p className="text-2xl font-bold text-green-600">{dashboardStats?.users?.active || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Чатов</p>
              <p className="text-2xl font-bold text-blue-600">{dashboardStats?.chats?.total || 0}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Сообщений</p>
              <p className="text-2xl font-bold text-purple-600">{dashboardStats?.messages?.total || 0}</p>
            </div>
          </div>
        </div>
      )}

      {/* Settings sections */}
      <div className="space-y-6">
        {sections.map(section => (
          <div key={section.title} className="bg-white rounded-xl shadow-sm">
            <div className="p-4 border-b flex items-center">
              <section.icon className="w-5 h-5 text-blue-600 mr-3" />
              <h2 className="font-semibold text-gray-900">{section.title}</h2>
            </div>
            <div className="divide-y">
              {section.items.map((item, i) => (
                <div key={i} className="p-4 hover:bg-gray-50 cursor-pointer">
                  <p className="font-medium text-gray-900">{item.label}</p>
                  <p className="text-sm text-gray-500">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
