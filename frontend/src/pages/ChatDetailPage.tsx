import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Send, User, Clock, Check, CheckCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { chatsApi } from '../services/api';
import { timeAgo, formatDateTime } from '../utils/cn';

export default function ChatDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState('');

  const { data: chat, isLoading: chatLoading } = useQuery({
    queryKey: ['chat', id],
    queryFn: () => chatsApi.getOne(Number(id)),
    enabled: !!id
  });

  const { data: messagesData, isLoading: messagesLoading } = useQuery({
    queryKey: ['messages', id],
    queryFn: () => chatsApi.getMessages(Number(id)),
    enabled: !!id
  });

  const sendMutation = useMutation({
    mutationFn: (content: string) => chatsApi.sendMessage(Number(id), content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', id] });
      setMessage('');
    },
    onError: () => toast.error('Ошибка отправки')
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => chatsApi.updateStatus(Number(id), status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', id] });
      toast.success('Статус обновлён');
    }
  });

  if (chatLoading || messagesLoading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-gray-500">Загрузка...</div>
      </div>
    );
  }

  if (!chat) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Чат не найден</p>
          <button onClick={() => navigate('/chats')} className="text-blue-600 hover:underline">
            Вернуться к чатам
          </button>
        </div>
      </div>
    );
  }

  const currentChat = chat;
  const messages = messagesData?.messages || [];

  const handleSend = () => {
    if (!message.trim()) return;
    sendMutation.mutate(message);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button onClick={() => navigate('/chats')} className="mr-4 p-2 hover:bg-gray-100 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center mr-3">
              <span className="text-white font-medium">
                {currentChat.client_name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="font-semibold text-gray-900">{currentChat.client_name}</h1>
              <p className="text-sm text-gray-500">{currentChat.client_phone}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={currentChat.status}
              onChange={e => statusMutation.mutate(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              <option value="ACTIVE">Активный</option>
              <option value="PENDING">Ожидает</option>
              <option value="CLOSED">Закрыт</option>
            </select>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            Нет сообщений. Напишите первое сообщение!
          </div>
        ) : (
          messages.map((msg: any) => (
            <div
              key={msg.id}
              className={`flex ${msg.is_from_user ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-md rounded-2xl px-4 py-2 ${
                  msg.is_from_user
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p>{msg.content}</p>
                <div className={`flex items-center gap-1 mt-1 text-xs ${
                  msg.is_from_user ? 'text-blue-200' : 'text-gray-400'
                }`}>
                  <span>{formatDateTime(msg.created_at)}</span>
                  {msg.is_from_user && (
                    msg.is_read ? <CheckCheck className="w-3 h-3" /> : <Check className="w-3 h-3" />
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="bg-white border-t p-4">
        <div className="flex gap-3">
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Напишите сообщение..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500"
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={!message.trim() || sendMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
