import React from 'react';
import { BarChart3, TrendingUp, Users, MessageSquare } from 'lucide-react';

export default function AnalyticsPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Аналитика</h1>
      <p className="text-gray-600 mb-8">Статистика и метрики системы</p>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-blue-600" />
            </div>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-gray-600 text-sm">Всего сообщений</p>
          <p className="text-2xl font-bold text-gray-900">1,234</p>
          <p className="text-sm text-green-600 mt-1">+12% за неделю</p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-green-600" />
            </div>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-gray-600 text-sm">Активные клиенты</p>
          <p className="text-2xl font-bold text-gray-900">89</p>
          <p className="text-sm text-green-600 mt-1">+8% за неделю</p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-purple-600" />
            </div>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-gray-600 text-sm">Среднее время ответа</p>
          <p className="text-2xl font-bold text-gray-900">2.5 мин</p>
          <p className="text-sm text-green-600 mt-1">-15% за неделю</p>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-orange-600" />
            </div>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-gray-600 text-sm">Закрытые чаты</p>
          <p className="text-2xl font-bold text-gray-900">156</p>
          <p className="text-sm text-green-600 mt-1">+5% за неделю</p>
        </div>
      </div>

      {/* Placeholder chart */}
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <h2 className="font-semibold text-gray-900 mb-4">График активности</h2>
        <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
          <p className="text-gray-500">График активности загружается...</p>
        </div>
      </div>
    </div>
  );
}
