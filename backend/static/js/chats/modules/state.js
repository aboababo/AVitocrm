/**
 * State Management Module
 * Управление состоянием приложения
 */

// Глобальное состояние
export let currentChatId = null;
export let allChats = [];
export let filteredChats = [];
export let currentSort = 'all';
export let currentSortOrder = 'newest'; // 'newest' или 'oldest'
export let searchQuery = '';
export let autoRefreshInterval = null;
export let messagesAutoRefreshInterval = null;
export let quickRepliesCache = null;
export let quickRepliesCacheTime = 0;
export let messagesState = {};
export let currentChatHasAvito = true;
export let chatsLoading = false;
export let chatsLoadError = null;
export let searchDebounceTimer = null;
export let initialChatIdFromUrl = null;
export let chatIdFromUrlHandled = false;
export let messagesLoading = false;
export let unreadFromRefresh = 0;

// Флаги для рендеринга
export let isRendering = false;
export let renderScheduled = false;
export let lastAutoRefreshTime = 0;

// Константы
export const CACHE_DURATION = 60000;
export const DEBUG_MODE = false; // Отключено для производительности
export const AUTO_REFRESH_THROTTLE = 2000; // Минимум 2 секунды между обновлениями
export const MESSAGE_PAGE = 50;

// Константы для задержек и таймаутов
export const DELAYS = {
    BATCH_TAKE_CLEANUP: 2000,        // Задержка перед очисткой locallyTakenChats
    PRODUCT_URL_EXTRACT: 3000,       // Задержка перед извлечением product_url
    AUTO_EXTRACT: 5000,              // Задержка перед автоматическим извлечением
    SYNC_RETRY: 1000,                // Задержка перед повторной попыткой синхронизации
    SEARCH_DEBOUNCE: 300             // Debounce для поиска (улучшает производительность)
};

// Кеширование чатов в localStorage
export const CHATS_CACHE_KEY = 'chats_cache';
export const CHATS_CACHE_TIMESTAMP_KEY = 'chats_cache_timestamp';
export const CHATS_CACHE_MAX_AGE = 5 * 60 * 1000; // 5 минут

// НОВЫЙ ПОДХОД: Set для отслеживания чатов, которые были взяты локально
export const locallyTakenChats = new Set();
// Map для хранения timestamp каждого взятого чата (для автоматической очистки)
export const locallyTakenChatsTimestamps = new Map();

// Кэш DOM элементов для быстрого доступа
export const domCache = {
    chatsList: null,
    myChatsCount: null,
    poolChatsCount: null,
    archiveCount: null,
    blockedCount: null
};

// Функции для работы с кешем
export function saveChatsToCache(chats) {
    try {
        localStorage.setItem(CHATS_CACHE_KEY, JSON.stringify(chats));
        localStorage.setItem(CHATS_CACHE_TIMESTAMP_KEY, Date.now().toString());
    } catch (e) {
        console.warn('[CACHE] Ошибка сохранения в localStorage:', e);
    }
}

export function loadChatsFromCache() {
    try {
        const cached = localStorage.getItem(CHATS_CACHE_KEY);
        const timestamp = localStorage.getItem(CHATS_CACHE_TIMESTAMP_KEY);
        
        if (!cached || !timestamp) {
            return null;
        }
        
        const age = Date.now() - parseInt(timestamp, 10);
        if (age > CHATS_CACHE_MAX_AGE) {
            localStorage.removeItem(CHATS_CACHE_KEY);
            localStorage.removeItem(CHATS_CACHE_TIMESTAMP_KEY);
            return null;
        }
        
        const chats = JSON.parse(cached);
        return chats;
    } catch (e) {
        console.warn('[CACHE] Ошибка загрузки из localStorage:', e);
        return null;
    }
}

// Setters для обновления состояния
export function setCurrentChatId(id) {
    currentChatId = id;
}

export function setAllChats(chats) {
    allChats = chats;
}

export function setFilteredChats(chats) {
    filteredChats = chats;
}

export function setCurrentSort(sort) {
    currentSort = sort;
}

export function setCurrentSortOrder(order) {
    currentSortOrder = order;
}

export function setSearchQuery(query) {
    searchQuery = query;
}

export function setChatsLoading(loading) {
    chatsLoading = loading;
}

export function setMessagesLoading(loading) {
    messagesLoading = loading;
}

export function setChatsLoadError(error) {
    chatsLoadError = error;
}

