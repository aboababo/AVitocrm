/**
 * Render Module
 * Функции для рендеринга UI
 */

import { 
    filteredChats, 
    currentChatId, 
    currentSort, 
    searchQuery,
    allChats,
    chatsLoading,
    chatsLoadError,
    isRendering,
    renderScheduled,
    domCache,
    messagesState,
    MESSAGE_PAGE
} from './state.js';
import { debugLog, debugError, escapeHtml, highlightText } from './utils.js';
import { setCurrentChatId, setAllChats, setFilteredChats, setChatsLoading, setChatsLoadError } from './state.js';

// Инициализация кэша DOM элементов
export function initDOMCache() {
    if (!domCache.chatsList) {
        domCache.chatsList = document.getElementById('chats-list');
        domCache.myChatsCount = document.getElementById('my-chats-count');
        domCache.poolChatsCount = document.getElementById('pool-chats-count');
        domCache.archiveCount = document.getElementById('archive-count');
        domCache.blockedCount = document.getElementById('blocked-count');
    }
}

// Скелетон для загрузки
export function getChatsSkeletonMarkup() {
    const skeletonCard = `
        <div class="chat-skeleton-card">
            <div class="chat-skeleton-header">
                <div style="flex:1;">
                    <div class="skeleton skeleton-line large" style="width: 60%; margin-bottom: 0.4rem;"></div>
                    <div class="skeleton skeleton-line" style="width: 40%;"></div>
                </div>
                <div class="skeleton skeleton-line" style="width: 48px; height: 24px;"></div>
            </div>
            <div class="skeleton skeleton-line" style="width: 90%; margin-bottom: 0.35rem;"></div>
            <div class="skeleton skeleton-line" style="width: 80%; margin-bottom: 0.35rem;"></div>
            <div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
                <div class="skeleton skeleton-line" style="width: 80px; height: 24px;"></div>
                <div class="skeleton skeleton-line" style="width: 60px; height: 24px;"></div>
            </div>
        </div>
    `;
    return Array.from({length: 5}).map(() => skeletonCard).join('');
}

// Рендеринг списка чатов (упрощенная версия)
export function renderChatsList() {
    // Предотвращаем множественные одновременные рендеры
    if (isRendering) {
        renderScheduled = true;
        return;
    }
    
    if (renderScheduled) {
        return;
    }
    
    renderScheduled = true;
    
    requestAnimationFrame(() => {
        renderScheduled = false;
        isRendering = true;
        
        try {
            initDOMCache();
            const container = domCache.chatsList;
            
            if (!container) {
                debugError('[RENDER] ❌ КОНТЕЙНЕР НЕ НАЙДЕН!');
                isRendering = false;
                return;
            }

            if (chatsLoading) {
                container.setAttribute('aria-busy', 'true');
                container.innerHTML = getChatsSkeletonMarkup();
                isRendering = false;
                return;
            }

            if (chatsLoadError) {
                container.innerHTML = `
                    <div class="empty-list">
                        <div class="empty-list-icon">⚠️</div>
                        <h3>Не удалось загрузить чаты</h3>
                        <p>Проверьте соединение и обновите страницу</p>
                        <button class="retry-button" onclick="window.loadChats && window.loadChats()">🔄 Повторить</button>
                    </div>
                `;
                isRendering = false;
                return;
            }

            if (filteredChats.length === 0) {
                const emptyMessage = currentSort === 'completed' 
                    ? '<h3>Архив пуст</h3><p>Завершенных чатов пока нет</p>'
                    : currentSort === 'blocked'
                    ? '<h3>Заблокированных чатов нет</h3><p>Нет заблокированных чатов</p>'
                    : currentSort === 'my'
                    ? '<h3>Нет ваших чатов</h3><p>Возьмите чаты из пула</p>'
                    : currentSort === 'all'
                    ? '<h3>Общий пул пуст</h3><p>Нет чатов в общем пуле</p>'
                    : searchQuery
                    ? '<h3>Ничего не найдено</h3><p>Попробуйте изменить запрос</p>'
                    : allChats.length === 0
                    ? '<h3>Чатов нет</h3><p>Синхронизируйте чаты из Avito API</p><button class="retry-button" onclick="window.syncChats && window.syncChats()">🔄 Синхронизировать</button>'
                    : '<h3>Чатов нет</h3><p>Нет чатов по выбранной сортировке</p>';
                
                const icon = currentSort === 'completed' ? '📦' : currentSort === 'blocked' ? '🚫' : currentSort === 'my' ? '👤' : currentSort === 'all' ? '📁' : searchQuery ? '🔍' : allChats.length === 0 ? '🔄' : '😴';
                
                container.innerHTML = `
                    <div class="empty-list">
                        <div class="empty-list-icon">${icon}</div>
                        ${emptyMessage}
                    </div>
                `;
                isRendering = false;
                return;
            }
            
            // Рендерим чаты
            const fragment = document.createDocumentFragment();
            filteredChats.forEach(chat => {
                const chatElement = document.createElement('div');
                chatElement.innerHTML = renderSingleChat(chat);
                fragment.appendChild(chatElement.firstElementChild);
            });
            
            container.innerHTML = '';
            container.appendChild(fragment);
            
        } catch (error) {
            debugError('[RENDER] Ошибка рендеринга:', error);
        } finally {
            isRendering = false;
        }
    });
}

// Рендеринг одного чата (упрощенная версия)
export function renderSingleChat(chat) {
    const isCompleted = chat.status === 'completed';
    const isBlocked = chat.status === 'blocked';
    const isInPool = !chat.assigned_manager_id && !isCompleted && !isBlocked;
    const isActive = currentChatId === chat.id;
    const cardClass = `chat-card ${isActive ? 'active' : ''} ${isInPool ? 'pool' : ''}`;
    const safeClientName = highlightText(chat.client_name || '', searchQuery);
    const safeShopName = highlightText(chat.shop_name || '', searchQuery);
    const safeLastMessage = highlightText(chat.last_message || 'Нет сообщений', searchQuery);
    
    // ARIA labels для доступности
    const statusText = isInPool ? 'В пуле' : isCompleted ? 'Завершен' : isBlocked ? 'Заблокирован' : 'Активен';
    const unreadText = chat.unread_count > 0 ? `${chat.unread_count} непрочитанных сообщений` : '';
    const ariaLabel = `${safeClientName}, ${safeShopName}. ${statusText}. ${unreadText}`;
    
    // Экранируем для HTML атрибутов
    const escapedAriaLabel = ariaLabel.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    
    return `
        <div class="${cardClass}" 
             onclick="selectChat(Number(${chat.id}))" 
             data-chat-id="${chat.id}"
             role="listitem"
             tabindex="0"
             aria-label="${escapedAriaLabel}"
             aria-selected="${isActive ? 'true' : 'false'}"
             aria-current="${isActive ? 'page' : 'false'}">
            <div class="chat-card-header">
                <div class="chat-card-title">
                    <div class="chat-client-name">${safeClientName}</div>
                    <div class="chat-shop-name">${safeShopName}</div>
                </div>
                <div class="chat-badges">
                    ${isInPool ? '<span class="pool-badge" aria-label="Чат в пуле"><span aria-hidden="true">🌊</span> ПУЛ</span>' : ''}
                    ${chat.unread_count > 0 ? `<span class="unread-count" aria-label="${chat.unread_count} непрочитанных сообщений">${chat.unread_count}</span>` : ''}
                </div>
            </div>
            <div class="chat-preview">${safeLastMessage}</div>
            <div class="chat-footer">
                ${isCompleted ? 
                    '<span class="priority-tag priority-completed" aria-label="Чат завершен"><span aria-hidden="true">📦</span> ЗАВЕРШЕН</span>' :
                    isBlocked ?
                    '<span class="priority-tag" style="background: #ef4444; color: white;" aria-label="Чат заблокирован"><span aria-hidden="true">🚫</span> ЗАБЛОКИРОВАН</span>' :
                    ''
                }
            </div>
        </div>
    `;
}

// Рендеринг сообщений (упрощенная версия)
export function renderMessages(chatId, previousHeight = null, previousScrollTop = null, mode = 'replace') {
    const state = messagesState[chatId] || {messages: [], has_more: false};
    const container = document.getElementById('messages-container');
    if (!container) {
        console.error('[RENDER MESSAGES] Контейнер #messages-container не найден!');
        return;
    }
    
    if (!state.messages || state.messages.length === 0) {
        container.innerHTML = `
            <div class="empty-chat">
                <div class="empty-chat-icon">💬</div>
                <h3>Нет сообщений</h3>
                <p>Начните общение с клиентом</p>
            </div>
        `;
        return;
    }
    
    const loadMoreBtn = state.has_more ? `
        <button id="load-more-btn" class="load-more-btn" onclick="loadOlderMessages()">
            ⬆️ Загрузить предыдущие сообщения
        </button>
    ` : '';
    
    const messagesHtml = state.messages.map(msg => messageTemplate(msg)).join('');
    container.innerHTML = loadMoreBtn + messagesHtml;
    
    if (mode === 'prepend' && previousHeight) {
        const newHeight = container.scrollHeight;
        container.scrollTop = newHeight - previousHeight;
    } else if (mode === 'refresh' && previousScrollTop !== null) {
        container.scrollTop = previousScrollTop;
    } else {
        container.scrollTop = container.scrollHeight;
    }
}

// Шаблон сообщения
export function messageTemplate(msg) {
    const isOutgoing = msg.sender_id === 'manager' || msg.sender_name === 'manager';
    const time = new Date(msg.created_at || msg.timestamp).toLocaleString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
    });
    const safeText = escapeHtml(msg.message_text || '');
    
    return `
        <div class="message-row ${isOutgoing ? 'outgoing' : 'incoming'}">
            ${!isOutgoing ? `<div class="message-author">${escapeHtml(msg.sender_name || 'Клиент')}</div>` : ''}
            <div class="message-wrapper">
                <div class="message-bubble">${safeText}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
}

// Обновление счетчиков
export function updateCounters() {
    const completedCount = allChats.filter(chat => chat.status === 'completed').length;
    const blockedCount = allChats.filter(chat => chat.status === 'blocked').length;
    const poolCount = allChats.filter(chat => 
        chat.status !== 'completed' && 
        chat.status !== 'blocked' && 
        !chat.assigned_manager_id
    ).length;
    
    if (domCache.archiveCount) domCache.archiveCount.textContent = `(${completedCount})`;
    if (domCache.blockedCount) domCache.blockedCount.textContent = `(${blockedCount})`;
    if (domCache.poolChatsCount) domCache.poolChatsCount.textContent = `(${poolCount})`;
}

