import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Filter, Plus, MessageSquare, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { chatsApi } from '../services/api';
import { timeAgo } from '../utils/cn';
import { useNavigate } from 'react-router-dom';

export default function ChatsPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [newChat, setNewChat] = useState({ client_name: '', client_phone: '', priority: 'NORMAL' });
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['chats', { search, status }],
    queryFn: () => chatsApi.getAll({ search: search || undefined, status: status || undefined })
  });

  const createMutation = useMutation({
    mutationFn: chatsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      setShowModal(false);
      setNewChat({ client_name: '', client_phone: '', priority: 'NORMAL' });
      toast.success('Чат создан');
    },
    onError: () => toast.error('Ошибка создания чата')
  });

  const getStatusColor = (status: string) => {
    const normalizedStatus = status?.toUpperCase();
    switch (normalizedStatus) {
      case 'ACTIVE': return 'bg-green-100 text-green-800';
      case 'PENDING': return 'bg-yellow-100 text-yellow-800';
      case 'CLOSED': return 'bg-gray-100 text-gray-800';
      case 'ARCHIVED': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    const normalizedPriority = priority?.toUpperCase();
    switch (normalizedPriority) {
      case 'URGENT': return 'bg-red-100 text-red-800';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'NORMAL': return 'bg-blue-100 text-blue-800';
      case 'LOW': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusDisplayText = (status: string) => {
    const normalizedStatus = status?.toUpperCase();
    switch (normalizedStatus) {
      case 'ACTIVE': return 'Активен';
      case 'PENDING': return 'Ожидает';
      case 'CLOSED': return 'Закрыт';
      case 'ARCHIVED': return 'В архиве';
      default: return status || 'Неизвестно';
    }
  };

  const getPriorityDisplayText = (priority: string) => {
    const normalizedPriority = priority?.toUpperCase();
    switch (normalizedPriority) {
      case 'URGENT': return 'Срочный';
      case 'HIGH': return 'Высокий';
      case 'NORMAL': return 'Обычный';
      case 'LOW': return 'Низкий';
      default: return priority || 'Неизвестно';
    }
  };

  const chats = data?.chats || [];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Чаты</h1>
          <p className="text-gray-600">Управление коммуникациями с клиентами</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-5 h-5 mr-2" />
          Новый чат
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-4 mb-6 shadow-sm">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Поиск по имени клиента..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Все статусы</option>
            <option value="ACTIVE">Активные</option>
            <option value="PENDING">Ожидают</option>
            <option value="CLOSED">Закрытые</option>
            <option value="ARCHIVED">Архивные</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-gray-600 text-sm">Всего</p>
          <p className="text-2xl font-bold text-gray-900">{data?.total || 0}</p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-gray-600 text-sm">Активные</p>
          <p className="text-2xl font-bold text-green-600">
            {chats.filter((c: any) => c.status?.toUpperCase() === 'ACTIVE').length}
          </p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-gray-600 text-sm">Непрочитанные</p>
          <p className="text-2xl font-bold text-orange-600">
            {chats.reduce((sum: number, c: any) => sum + (c.unread_count || 0), 0)}
          </p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <p className="text-gray-600 text-sm">Срочные</p>
          <p className="text-2xl font-bold text-red-600">
            {chats.filter((c: any) => c.priority?.toUpperCase() === 'URGENT').length}
          </p>
        </div>
      </div>

      {/* Chats list */}
      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-4 border-b flex items-center">
          <MessageSquare className="w-5 h-5 text-gray-400 mr-3" />
          <h2 className="font-semibold text-gray-900">Список чатов</h2>
        </div>
        
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Загрузка...</div>
        ) : chats.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {search || status ? 'Чаты не найдены' : 'Нет чатов'}
          </div>
        ) : (
          <div className="divide-y">
            {chats.map((chat: any) => (
              <div
                key={chat.id}
                onClick={() => navigate(`/chats/${chat.id}`)}
                className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mr-4">
                      <span className="text-white font-medium">
                        {chat.client_name?.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-gray-900">{chat.client_name}</p>
                        <div className="flex items-center gap-1">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${getStatusColor(chat.status)}`}>
                            {getStatusDisplayText(chat.status)}
                          </span>
                          <span className={`px-2 py-0.5 text-xs rounded-full ${getPriorityColor(chat.priority)}`}>
                            {getPriorityDisplayText(chat.priority)}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{chat.title || chat.last_message || 'Нет сообщений'}</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {chat.client_phone} • {timeAgo(chat.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {chat.unread_count > 0 && (
                      <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-medium text-white bg-red-500 rounded-full">
                        {chat.unread_count}
                      </span>
                    )}
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Создать чат</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Имя клиента *</label>
                <input
                  type="text"
                  value={newChat.client_name}
                  onChange={e => setNewChat({ ...newChat, client_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Иван Петров"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Телефон</label>
                <input
                  type="text"
                  value={newChat.client_phone}
                  onChange={e => setNewChat({ ...newChat, client_phone: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="+7 (999) 123-45-67"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Приоритет</label>
                <select
                  value={newChat.priority}
                  onChange={e => setNewChat({ ...newChat, priority: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="LOW">Низкий</option>
                  <option value="NORMAL">Обычный</option>
                  <option value="HIGH">Высокий</option>
                  <option value="URGENT">Срочный</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                onClick={() => {
                  if (!newChat.client_name) {
                    toast.error('Введите имя клиента');
                    return;
                  }
                  createMutation.mutate(newChat);
                }}
                disabled={createMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Создание...' : 'Создать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
