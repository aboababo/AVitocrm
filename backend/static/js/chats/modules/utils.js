/**
 * Utilities Module
 * Вспомогательные функции
 */

import { DEBUG_MODE } from './state.js';

// Оптимизированная функция логирования - не выполняет ничего если DEBUG_MODE = false
export function debugLog(...args) {
    if (!DEBUG_MODE) return; // Быстрый выход без создания строк
    console.log(...args);
}

export function debugError(...args) {
    if (!DEBUG_MODE) return;
    console.error(...args);
}

// Мемоизация для фильтрации чатов (улучшает производительность)
export function memoize(fn, keyFn) {
    const cache = new Map();
    return function(...args) {
        const key = keyFn ? keyFn(...args) : JSON.stringify(args);
        if (cache.has(key)) {
            return cache.get(key);
        }
        const result = fn(...args);
        cache.set(key, result);
        // Ограничиваем размер кеша (LRU - удаляем старые записи)
        if (cache.size > 100) {
            const firstKey = cache.keys().next().value;
            cache.delete(firstKey);
        }
        return result;
    };
}

// Экранирование HTML
export function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Экранирование для регулярных выражений
export function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Подсветка текста в результатах поиска
export function highlightText(text, query) {
    const safe = escapeHtml(text || '');
    const q = (query || '').trim();
    if (!q) return safe;
    const pattern = new RegExp(escapeRegExp(q), 'gi');
    return safe.replace(pattern, (m) => `<mark>${m}</mark>`);
}

// Показ уведомлений
export function showNotification(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const normalizedType = ['success', 'error'].includes(type) ? type : 'info';
    const icons = {success: '✅', error: '⚠️', info: 'ℹ️'};
    const safeMessage = escapeHtml(message);
    const toast = document.createElement('div');
    toast.className = `toast toast-${normalizedType}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[normalizedType]}</span>
        <span>${safeMessage}</span>
        <button class="toast-close" aria-label="Закрыть уведомление">×</button>
    `;
    const removeToast = () => toast.remove();
    toast.querySelector('.toast-close').addEventListener('click', removeToast);
    container.appendChild(toast);
    setTimeout(removeToast, 3500);
}

// Валидация данных чата
export function validateChatData(chat) {
    if (!chat || typeof chat !== 'object') return false;
    if (typeof chat.id !== 'number' || chat.id <= 0) return false;
    if (typeof chat.status !== 'string') return false;
    if (chat.assigned_manager_id !== null && chat.assigned_manager_id !== undefined && 
        typeof chat.assigned_manager_id !== 'number') return false;
    return true;
}

