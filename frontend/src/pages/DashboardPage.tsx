import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageSquare, Users, Clock, TrendingUp } from 'lucide-react';
import { chatsApi } from '../services/api';
import { timeAgo } from '../utils/cn';

export default function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: chatsApi.getStats,
    retry: false
  });

  const { data: recentChats } = useQuery({
    queryKey: ['recent-chats'],
    queryFn: () => chatsApi.getAll({ size: 5 }),
    retry: false
  });

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Панель управления</h1>
      <p className="text-gray-600 mb-8">Обзор системы и ключевые метрики</p>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Всего чатов</p>
              <p className="text-3xl font-bold text-gray-900">{stats?.total_chats || 0}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Активные</p>
              <p className="text-3xl font-bold text-green-600">{stats?.active_chats || 0}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Непрочитанные</p>
              <p className="text-3xl font-bold text-orange-600">{stats?.unread_messages || 0}</p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
              <Clock className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Сообщений</p>
              <p className="text-3xl font-bold text-purple-600">{stats?.total_messages || 0}</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Recent chats */}
      <div className="bg-white rounded-xl shadow-sm">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Последние чаты</h2>
        </div>
        <div className="divide-y">
          {recentChats?.chats?.length === 0 ? (
            <div className="p-8 text-center text-gray-500">Нет чатов</div>
          ) : (
            recentChats?.chats?.map((chat: any) => (
              <div key={chat.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mr-4">
                      <span className="text-white font-medium">
                        {chat.client_name?.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{chat.client_name}</p>
                      <p className="text-sm text-gray-500">{chat.last_message || 'Нет сообщений'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500">{timeAgo(chat.created_at)}</p>
                    {chat.unread_count > 0 && (
                      <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-medium text-white bg-red-500 rounded-full mt-1">
                        {chat.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
