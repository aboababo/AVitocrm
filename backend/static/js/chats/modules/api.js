/**
 * API Module
 * Все запросы к серверу
 */

import { 
    DELAYS, 
    allChats, 
    setAllChats, 
    currentUserId, 
    currentUsername,
    locallyTakenChats,
    locallyTakenChatsTimestamps,
    setChatsLoading,
    setChatsLoadError,
    messagesState,
    MESSAGE_PAGE,
    currentChatId,
    setMessagesLoading
} from './state.js';
import { 
    debugLog, 
    debugError, 
    showNotification, 
    validateChatData,
    escapeHtml
} from './utils.js';
import { saveChatsToCache, loadChatsFromCache } from './state.js';

// Улучшенная функция fetch с retry логикой
async function fetchWithRetry(url, options, maxRetries) {
    maxRetries = maxRetries || 3;
    let lastError = null;
    let response = null;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            response = await fetch(url, {
                ...options,
                signal: AbortSignal.timeout(30000) // Таймаут 30 секунд
            });
            
            if (response.ok) {
                return response;
            }
            
            const errorText = await response.text();
            lastError = new Error(`HTTP ${response.status}: ${errorText.substring(0, 100)}`);
            
            // Для 4xx ошибок не делаем retry (кроме 408, 429)
            if (response.status >= 400 && response.status < 500 && 
                response.status !== 408 && response.status !== 429) {
                if (attempt === maxRetries - 1) throw lastError;
                break;
            }
            
            // Для 5xx и временных ошибок делаем retry
            if (attempt < maxRetries - 1) {
                const delay = DELAYS.SYNC_RETRY * Math.pow(2, attempt); // Exponential backoff
                debugLog(`[FETCH RETRY] Ошибка ${response.status}, повтор через ${delay}мс (попытка ${attempt + 1}/${maxRetries})`);
                await new Promise(resolve => setTimeout(resolve, delay));
                continue;
            }
            
            throw lastError;
        } catch (error) {
            lastError = error;
            
            // Если это AbortError (таймаут), пробуем еще раз
            if (error.name === 'AbortError' && attempt < maxRetries - 1) {
                const delay = DELAYS.SYNC_RETRY * Math.pow(2, attempt);
                debugLog(`[FETCH RETRY] Таймаут, повтор через ${delay}мс (попытка ${attempt + 1}/${maxRetries})`);
                await new Promise(resolve => setTimeout(resolve, delay));
                continue;
            }
            
            // Если это последняя попытка - пробрасываем
            if (attempt === maxRetries - 1) {
                throw error;
            }
            
            // Для других ошибок делаем retry
            const delay = DELAYS.SYNC_RETRY * Math.pow(2, attempt);
            debugLog(`[FETCH RETRY] Ошибка сети, повтор через ${delay}мс (попытка ${attempt + 1}/${maxRetries})`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    return response;
}

// Загрузка чатов
export async function loadChats(doSync = false, silent = false) {
    debugLog('========================================');
    debugLog('[LOAD CHATS] Начинаем загрузку чатов');
    debugLog('[LOAD CHATS] doSync:', doSync, 'silent:', silent);
    
    try {
        const isFirstLoad = allChats.length === 0;
        
        // ВСЕГДА показываем кеш сразу, если он есть
        const cachedChats = loadChatsFromCache();
        if (cachedChats && cachedChats.length > 0) {
            setAllChats(cachedChats);
            debugLog('[LOAD CHATS] ✅ Показаны кешированные чаты мгновенно, обновляем в фоне...');
        } else if (isFirstLoad && !silent) {
            setChatsLoading(true);
            setChatsLoadError(null);
        }
        
        // Синхронизация в фоне
        if (doSync || isFirstLoad) {
            fetch('/api/chats/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({})
            }).then(syncResponse => {
                if (syncResponse.ok) {
                    debugLog('[LOAD CHATS] ✅ Синхронизация завершена в фоне');
                    loadChats(false, true).catch(() => {});
                }
            }).catch(syncError => {
                debugLog('[LOAD CHATS] Ошибка синхронизации, продолжаем загрузку:', syncError);
            });
        }
        
        // Загрузка чатов с сервера
        const MAX_RETRIES = 3;
        let response = null;
        
        try {
            response = await fetchWithRetry('/api/chats', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                mode: 'cors'
            }, MAX_RETRIES);
        } catch (error) {
            if (allChats.length > 0) {
                setChatsLoading(false);
                return;
            }
            const errorMessage = error.message || 'Не удалось загрузить чаты';
            let userMessage = 'Ошибка загрузки чатов';
            if (error.message && error.message.includes('Failed to fetch')) {
                userMessage = 'Нет подключения к серверу. Проверьте интернет-соединение.';
            } else if (error.message && error.message.includes('timeout')) {
                userMessage = 'Превышено время ожидания ответа от сервера.';
            } else if (error.message && error.message.includes('HTTP 5')) {
                userMessage = 'Ошибка на сервере. Попробуйте позже.';
            }
            showNotification(`❌ ${userMessage}`, 'error');
            throw error;
        }
        
        if (!response || !response.ok) {
            if (allChats.length > 0) {
                setChatsLoading(false);
                return;
            }
            throw new Error('Не удалось загрузить чаты');
        }
        
        const data = await response.json();
        const items = Array.isArray(data) ? data : (Array.isArray(data.items) ? data.items : []);
        
        const validChats = items.filter(validateChatData);
        if (validChats.length !== items.length) {
            debugLog(`[LOAD CHATS] Отфильтровано ${items.length - validChats.length} невалидных чатов из ${items.length}`);
        }
        
        // Обновляем allChats данными с сервера
        setAllChats(validChats);
        
        // Обновляем локальные изменения для чатов, которые были взяты локально
        locallyTakenChats.forEach(chatId => {
            const chatIndex = allChats.findIndex(c => c.id === chatId);
            if (chatIndex !== -1) {
                const chat = allChats[chatIndex];
                if (!chat.assigned_manager_id || chat.assigned_manager_id === null || chat.assigned_manager_id === undefined) {
                    chat.assigned_manager_id = currentUserId;
                    chat.assigned_manager_name = currentUsername;
                    debugLog('[LOAD CHATS] ✅ Сохранены локальные изменения для чата', chatId);
                } else if (chat.assigned_manager_id === currentUserId) {
                    locallyTakenChats.delete(chatId);
                    locallyTakenChatsTimestamps.delete(chatId);
                }
            }
        });
        
        // Сохраняем в кеш
        saveChatsToCache(allChats);
        
        return { success: true, chats: allChats };
    } catch (error) {
        console.error('[LOAD CHATS] Ошибка загрузки чатов:', error);
        showNotification('Не удалось загрузить чаты: ' + error.message, 'error');
        setChatsLoadError(error);
        throw error;
    } finally {
        setChatsLoading(false);
    }
}

// Синхронизация чатов
export async function syncChats() {
    try {
        const response = await fetch('/api/chats/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({})
        });
        
        if (response.ok) {
            const data = await response.json();
            showNotification(`✅ Синхронизировано ${data.synced_count || 0} чатов`, 'success');
            return data;
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка синхронизации');
        }
    } catch (error) {
        console.error('Ошибка синхронизации:', error);
        showNotification(`❌ ${error.message || 'Ошибка синхронизации'}`, 'error');
        throw error;
    }
}

// Загрузка сообщений
export async function loadChatMessages(chatId, mode = 'replace') {
    if (!chatId) return;
    const state = messagesState[chatId] || {offset: 0, limit: MESSAGE_PAGE, messages: [], has_more: true, loading: false};
    if (state.loading) return;
    state.loading = true;
    messagesState[chatId] = state;
    const shouldDisableUi = mode !== 'refresh';
    if (shouldDisableUi) {
        setMessagesLoading(true);
    }
    
    const fetchOffset = mode === 'prepend' ? state.offset : 0;
    const params = new URLSearchParams({
        limit: state.limit,
        offset: fetchOffset
    });
    
    try {
        const response = await fetch(`/api/chats/${chatId}/messages?${params.toString()}`, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const payload = await response.json();
        let messages = [];
        if (Array.isArray(payload)) {
            messages = payload;
        } else if (payload && typeof payload === 'object') {
            if (Array.isArray(payload.messages)) {
                messages = payload.messages;
            } else if (Array.isArray(payload.items)) {
                messages = payload.items;
            }
        }
        
        const hasMore = payload.has_more ?? (messages.length === state.limit);
        
        if (mode === 'prepend') {
            state.messages = [...messages, ...state.messages];
            state.offset += messages.length;
        } else {
            state.messages = messages;
            state.offset = messages.length;
        }
        
        state.has_more = hasMore;
        return { messages: state.messages, hasMore, state };
    } catch (error) {
        console.error('Ошибка загрузки сообщений:', error);
        showNotification('Не удалось загрузить сообщения', 'error');
        throw error;
    } finally {
        state.loading = false;
        messagesState[chatId] = state;
        if (shouldDisableUi) {
            setMessagesLoading(false);
        }
    }
}

// Отправка сообщения
export async function sendMessage(messageText, chatId) {
    if (!chatId) return;
    
    const response = await fetch(`/api/chats/${chatId}/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({message: messageText})
    });
    
    if (response.ok) {
        const data = await response.json();
        return data;
    } else {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || 'Ошибка отправки');
    }
}

// Получение быстрых ответов
export async function getQuickReplyByText(text) {
    try {
        const response = await fetch('/api/quick-replies', {
            credentials: 'include',
            headers: { 'Accept': 'application/json' }
        });
        if (response.ok) {
            const replies = await response.json();
            const reply = replies.find(r => r.title === text || r.message_text === text);
            return reply ? reply.message_text : null;
        }
    } catch (error) {
        console.error('Ошибка загрузки быстрых ответов:', error);
    }
    return null;
}

