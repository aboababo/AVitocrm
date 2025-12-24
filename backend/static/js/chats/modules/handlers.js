/**
 * Event Handlers Module
 * Обработчики событий и функции, вызываемые из HTML
 */

import * as state from './state.js';
import * as api from './api.js';
import * as render from './render.js';
import * as utils from './utils.js';

// Экспортируем функции в window для использования в HTML
export function setupGlobalHandlers() {
    // Основные функции работы с чатами
    window.selectChat = selectChat;
    window.takeChatFromPool = takeChatFromPool;
    window.returnChatToPool = returnChatToPool;
    window.returnAllChatsToPool = returnAllChatsToPool;
    window.markAsCompleted = markAsCompleted;
    window.blockChat = blockChat;
    window.unblockChat = unblockChat;
    window.restoreChat = restoreChat;
    window.markAsDelivery = markAsDelivery;
    
    // Функции работы с сообщениями
    window.sendMessage = sendMessage;
    window.handleImageUpload = handleImageUpload;
    window.handleVoiceUpload = handleVoiceUpload;
    window.handleMediaUpload = handleMediaUpload;
    window.scrollMessagesBottom = scrollMessagesBottom;
    window.loadOlderMessages = loadOlderMessages;
    
    // Функции фильтрации и сортировки
    window.applySort = applySort;
    window.applySmartFilters = applySmartFilters;
    window.handleSearchInput = handleSearchInput;
    window.searchChats = searchChats;
    
    // Функции работы с быстрыми ответами
    window.showQuickRepliesMenu = showQuickRepliesMenu;
    window.showQuickRepliesManagementModal = showQuickRepliesManagementModal;
    window.closeQuickRepliesManagementModal = closeQuickRepliesManagementModal;
    window.showQuickReplyEditModal = showQuickReplyEditModal;
    window.closeQuickReplyEditModal = closeQuickReplyEditModal;
    window.useQuickReply = useQuickReply;
    
    // Массовые действия
    window.showBulkActionsMenu = showBulkActionsMenu;
    window.toggleChatSelection = toggleChatSelection;
    
    // Рендеринг
    window.renderChatsList = render.renderChatsList;
}

// Выбор чата
function selectChat(chatId) {
    try {
        chatId = Number(chatId);
        if (!chatId || isNaN(chatId) || chatId <= 0) {
            console.error('[SELECT CHAT] Неправильный ID чата:', chatId);
            return;
        }
        
        state.setCurrentChatId(chatId);
        const chat = state.allChats.find(c => Number(c.id) === chatId);
        if (!chat) {
            console.warn('[SELECT CHAT] Чат не найден, перезагружаем список');
            api.loadChats(false, true).then(() => {
                const retryChat = state.allChats.find(c => Number(c.id) === chatId);
                if (retryChat) {
                    selectChat(chatId);
                }
            });
            return;
        }
        
        // Обновляем UI и ARIA атрибуты
        document.querySelectorAll('.chat-card[data-chat-id]').forEach(card => {
            const isActive = Number(card.dataset.chatId) === chatId;
            card.classList.toggle('active', isActive);
            card.setAttribute('aria-selected', isActive ? 'true' : 'false');
            card.setAttribute('aria-current', isActive ? 'page' : 'false');
        });
        
        // Объявляем для screen readers
        if (window.announceToScreenReader) {
            const clientName = chat.client_name || 'Клиент';
            window.announceToScreenReader(`Выбран чат: ${clientName}`, 'polite');
        }
        
        // Загружаем сообщения
        if (window.loadChatMessages) {
            window.loadChatMessages(chatId);
        }
        
        // Обновляем URL
        const params = new URLSearchParams(window.location.search);
        params.set('chat_id', chatId);
        window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
    } catch (error) {
        console.error('[SELECT CHAT] Ошибка при выборе чата:', error);
        utils.showNotification('Ошибка при выборе чата', 'error');
    }
}

// Взять чат из пула
async function takeChatFromPool(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}/take`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат взят из пула', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при взятии чата');
        }
    } catch (error) {
        console.error('Ошибка при взятии чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Вернуть чат в пул
async function returnChatToPool(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}/return`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат возвращен в пул', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при возврате чата');
        }
    } catch (error) {
        console.error('Ошибка при возврате чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Вернуть все чаты в пул
async function returnAllChatsToPool() {
    if (!confirm('Вернуть все ваши чаты в пул?')) return;
    
    try {
        const response = await fetch('/api/chats/return-all-to-pool', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Все чаты возвращены в пул', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при возврате чатов');
        }
    } catch (error) {
        console.error('Ошибка при возврате чатов:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Завершить чат
async function markAsCompleted(chatId) {
    if (!chatId) chatId = state.currentChatId;
    if (!chatId) return;
    
    try {
        const response = await fetch(`/api/chats/${chatId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат завершен', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при завершении чата');
        }
    } catch (error) {
        console.error('Ошибка при завершении чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Заблокировать чат
async function blockChat(chatId) {
    if (!chatId) chatId = state.currentChatId;
    if (!chatId) return;
    
    if (!confirm('Заблокировать этот чат?')) return;
    
    try {
        const response = await fetch(`/api/chats/${chatId}/block`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат заблокирован', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при блокировке чата');
        }
    } catch (error) {
        console.error('Ошибка при блокировке чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Разблокировать чат
async function unblockChat(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}/unblock`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат разблокирован', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при разблокировке чата');
        }
    } catch (error) {
        console.error('Ошибка при разблокировке чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Восстановить чат
async function restoreChat(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}/restore`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат восстановлен', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при восстановлении чата');
        }
    } catch (error) {
        console.error('Ошибка при восстановлении чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Пометить как доставку
async function markAsDelivery() {
    if (!state.currentChatId) return;
    
    try {
        const response = await fetch(`/api/chats/${state.currentChatId}/delivery`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            utils.showNotification('✅ Чат помечен как доставка', 'success');
            await api.loadChats(false, true);
            render.renderChatsList();
        } else {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Ошибка при пометке чата');
        }
    } catch (error) {
        console.error('Ошибка при пометке чата:', error);
        utils.showNotification(`❌ ${error.message}`, 'error');
    }
}

// Отправка сообщения
async function sendMessage() {
    if (!state.currentChatId) return;
    
    const messageInput = document.getElementById('message-text');
    if (!messageInput) return;
    
    let messageText = messageInput.value.trim();
    if (!messageText) {
        utils.showNotification('Введите текст сообщения', 'error');
        return;
    }
    
    // Проверяем быстрый ответ
    const quickReply = await api.getQuickReplyByText(messageText);
    if (quickReply) {
        messageText = quickReply;
    }
    
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    try {
        await api.sendMessage(messageText, state.currentChatId);
        
        // Обновляем сообщения
        if (window.loadChatMessages) {
            await window.loadChatMessages(state.currentChatId);
        }
        
        // Обновляем список чатов в фоне
        api.loadChats(false, true).catch(() => {});
    } catch (error) {
        console.error('Ошибка отправки сообщения:', error);
        utils.showNotification(`❌ ${error.message || 'Ошибка отправки'}`, 'error');
        messageInput.value = messageText;
    }
}

// Загрузка изображения
async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // TODO: Реализовать загрузку изображения
    utils.showNotification('Загрузка изображений будет реализована', 'info');
}

// Загрузка голосового сообщения
async function handleVoiceUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // TODO: Реализовать загрузку голосового сообщения
    utils.showNotification('Загрузка голосовых сообщений будет реализована', 'info');
}

// Загрузка медиа файла
async function handleMediaUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // TODO: Реализовать загрузку медиа файла
    utils.showNotification('Загрузка файлов будет реализована', 'info');
}

// Прокрутка сообщений вниз
function scrollMessagesBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// Загрузка старых сообщений
async function loadOlderMessages() {
    if (!state.currentChatId) return;
    if (window.loadChatMessages) {
        await window.loadChatMessages(state.currentChatId, 'prepend');
    }
}

// Применение сортировки
function applySort(sort, useSmartUpdate = false) {
    state.setCurrentSort(sort);
    
    // Обновляем ARIA атрибуты для фильтров
    document.querySelectorAll('.filter-chip[data-sort]').forEach(chip => {
        const isActive = chip.dataset.sort === sort;
        chip.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
    
    // Фильтрация чатов
    let filtered = [...state.allChats];
    
    switch (sort) {
        case 'my':
            // currentUserId будет определен в main.js из шаблона
            const currentUserId = window.currentUserId || null;
            filtered = filtered.filter(chat => {
                if (chat.status === 'completed' || chat.status === 'blocked') return false;
                return chat.assigned_manager_id === currentUserId;
            });
            break;
        case 'pool':
            filtered = filtered.filter(chat => {
                return chat.status !== 'completed' && 
                       chat.status !== 'blocked' && 
                       !chat.assigned_manager_id;
            });
            break;
        case 'completed':
            filtered = filtered.filter(chat => chat.status === 'completed');
            break;
        case 'blocked':
            filtered = filtered.filter(chat => chat.status === 'blocked');
            break;
        case 'all':
        default:
            filtered = filtered.filter(chat => {
                return chat.status !== 'completed' && chat.status !== 'blocked';
            });
            break;
    }
    
    // Применяем поисковый запрос
    if (state.searchQuery) {
        const query = state.searchQuery.toLowerCase();
        filtered = filtered.filter(chat => {
            const clientName = (chat.client_name || '').toLowerCase();
            const shopName = (chat.shop_name || '').toLowerCase();
            const lastMessage = (chat.last_message || '').toLowerCase();
            return clientName.includes(query) || 
                   shopName.includes(query) || 
                   lastMessage.includes(query);
        });
    }
    
    // Сортировка
    if (state.currentSortOrder === 'newest') {
        filtered.sort((a, b) => {
            const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
            const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
            return timeB - timeA;
        });
    } else {
        filtered.sort((a, b) => {
            const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
            const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
            return timeA - timeB;
        });
    }
    
    state.setFilteredChats(filtered);
    render.renderChatsList();
    render.updateCounters();
    
    // Объявляем для screen readers
    if (window.announceToScreenReader) {
        const sortLabels = {
            'all': 'Общий пул',
            'my': 'Мои чаты',
            'pool': 'Пул',
            'completed': 'Завершенные',
            'blocked': 'Заблокированные'
        };
        window.announceToScreenReader(`Показано ${filtered.length} чатов в категории "${sortLabels[sort] || sort}"`, 'polite');
    }
}

// Применение умных фильтров
function applySmartFilters() {
    applySort(state.currentSort);
}

// Обработка поискового запроса
let searchDebounceTimer = null;
function handleSearchInput(value) {
    state.setSearchQuery(value);
    
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        searchChats(value);
    }, state.DELAYS.SEARCH_DEBOUNCE);
}

// Поиск чатов
function searchChats(query) {
    state.setSearchQuery(query);
    applySort(state.currentSort);
}

// Быстрые ответы
function showQuickRepliesMenu() {
    const menu = document.getElementById('quick-replies-menu');
    if (menu) {
        const isActive = menu.classList.contains('active');
        menu.classList.toggle('active');
        menu.setAttribute('aria-expanded', !isActive ? 'true' : 'false');
    }
}

function showQuickRepliesManagementModal() {
    const modal = document.getElementById('quick-replies-management-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
        // Фокусируемся на первом интерактивном элементе
        const firstButton = modal.querySelector('button[aria-label*="Закрыть"]');
        if (firstButton) {
            setTimeout(() => firstButton.focus(), 100);
        }
    }
}

function closeQuickRepliesManagementModal() {
    const modal = document.getElementById('quick-replies-management-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}

function showQuickReplyEditModal(replyId = null) {
    const modal = document.getElementById('quick-reply-edit-modal');
    if (modal) {
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
        // Фокусируемся на первом поле ввода
        const firstInput = modal.querySelector('input[type="text"], textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeQuickReplyEditModal() {
    const modal = document.getElementById('quick-reply-edit-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}

function useQuickReply(message) {
    const messageInput = document.getElementById('message-text');
    if (messageInput) {
        messageInput.value = message;
        messageInput.focus();
    }
    showQuickRepliesMenu();
}

// Массовые действия
const selectedChats = new Set();

function showBulkActionsMenu() {
    if (selectedChats.size === 0) return;
    
    const action = prompt(`Выбрано чатов: ${selectedChats.size}\n\nВыберите действие:\n1 - Взять из пула\n2 - Вернуть в пул\n3 - Завершить\n4 - Заблокировать\n5 - Отменить выбор`);
    if (!action) return;
    
    switch(action) {
        case '1':
            Array.from(selectedChats).forEach(id => takeChatFromPool(id));
            break;
        case '2':
            Array.from(selectedChats).forEach(id => returnChatToPool(id));
            break;
        case '3':
            Array.from(selectedChats).forEach(id => markAsCompleted(id));
            break;
        case '4':
            Array.from(selectedChats).forEach(id => blockChat(id));
            break;
        case '5':
            selectedChats.clear();
            document.querySelectorAll('.chat-select-checkbox').forEach(cb => cb.checked = false);
            break;
    }
}

function toggleChatSelection(chatId) {
    const checkbox = document.querySelector(`.chat-select-checkbox[data-chat-id="${chatId}"]`);
    if (!checkbox) return;
    
    if (checkbox.checked) {
        selectedChats.add(chatId);
    } else {
        selectedChats.delete(chatId);
    }
    
    const btn = document.getElementById('bulk-actions-btn');
    const countSpan = document.getElementById('selected-count');
    
    if (selectedChats.size > 0) {
        if (btn) btn.style.display = 'inline-flex';
        if (countSpan) countSpan.textContent = selectedChats.size;
    } else {
        if (btn) btn.style.display = 'none';
    }
}

