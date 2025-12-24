/**
 * Main Entry Point
 * Главный файл для инициализации приложения
 * 
 * Этот файл импортирует все модули и инициализирует приложение
 */

// Импортируем модули
import * as state from './modules/state.js';
import * as api from './modules/api.js';
import * as render from './modules/render.js';
import * as utils from './modules/utils.js';
import * as handlers from './modules/handlers.js';
import { initOptimizations } from './modules/optimizations.js';
import { initAccessibility, setupGlobalAccessibility } from './modules/accessibility.js';
import { initErrorHandling } from './modules/error-handler.js';

// Получаем данные пользователя из шаблона (будут определены в HTML)
// Эти переменные должны быть определены в шаблоне перед загрузкой модулей
if (typeof window.currentUserId !== 'undefined') {
    // Данные уже определены в шаблоне
} else {
    // Устанавливаем значения по умолчанию (будут переопределены из шаблона)
    window.currentUserId = null;
    window.currentUsername = '';
    window.currentUserRole = '';
    window.isAdmin = false;
}

// Экспортируем функции в window для обратной совместимости
window.loadChats = api.loadChats;
window.syncChats = api.syncChats;
window.showNotification = utils.showNotification;
window.loadChatMessages = api.loadChatMessages;

// Настраиваем глобальные обработчики
handlers.setupGlobalHandlers();

// Инициализация обработки ошибок (до всего остального)
initErrorHandling();

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('[INIT] Инициализация модульной системы чатов...');
    
    try {
        // Инициализация DOM кэша
        render.initDOMCache();
        
        // Инициализация оптимизаций
        initOptimizations();
        
        // Инициализация доступности
        initAccessibility();
        setupGlobalAccessibility();
    } catch (error) {
        console.error('[INIT ERROR] Ошибка при инициализации модулей:', error);
    }
    
    try {
        // Инициализация обработчиков событий
        const textarea = document.getElementById('message-text');
    if (textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 140) + 'px';
        });

        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                // sendMessage будет определен в handlers.js
                if (window.sendMessage) {
                    window.sendMessage();
                }
            }
        });
    }

    const searchInput = document.getElementById('chat-search');
    if (searchInput) {
        searchInput.addEventListener('input', (event) => {
            // handleSearchInput будет определен в handlers.js
            if (window.handleSearchInput) {
                window.handleSearchInput(event.target.value);
            }
        });
    }

    // Обработчики для фильтров
    document.querySelectorAll('.filter-chip[data-sort]').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            // applySort будет определен в handlers.js
            if (window.applySort) {
                window.applySort(chip.dataset.sort);
            }
        });
    });
    
    // Обработчики для сортировки
    document.querySelectorAll('.sort-chip[data-sort-order]').forEach(chip => {
        chip.addEventListener('click', () => {
            state.setCurrentSortOrder(chip.dataset.sortOrder);
            document.querySelectorAll('.sort-chip[data-sort-order]').forEach(c => {
                c.classList.toggle('active', c.dataset.sortOrder === state.currentSortOrder);
            });
            if (window.applySort) {
                window.applySort(state.currentSort);
            }
        });
    });

    // Проверка chat_id из URL
    const urlParams = new URLSearchParams(window.location.search);
    const urlChatId = urlParams.get('chat_id');
    if (urlChatId) {
        const parsedId = Number(urlChatId);
        if (!Number.isNaN(parsedId)) {
            state.initialChatIdFromUrl = parsedId;
        }
    }

    // Загрузка кеша для мгновенного отображения
    const cachedChats = state.loadChatsFromCache();
    if (cachedChats && cachedChats.length > 0) {
        state.setAllChats(cachedChats);
        // applySort и renderChatsList будут определены в handlers.js
        if (window.applySort) {
            window.applySort(state.currentSort);
        }
        if (window.renderChatsList) {
            window.renderChatsList();
        }
    }
    
    // Первая загрузка чатов
    console.log('[INIT] Вызываем loadChats(true) для первой загрузки...');
    try {
        api.loadChats(true, cachedChats && cachedChats.length > 0).then(() => {
            console.log('[INIT] Чаты загружены успешно');
        }).catch(error => {
            console.error('[INIT] Ошибка при загрузке чатов:', error);
        });
    } catch (error) {
        console.error('[INIT] ОШИБКА при вызове loadChats:', error);
    }
    
    } catch (error) {
        console.error('[INIT ERROR] Ошибка при инициализации обработчиков:', error);
        if (window.showNotification) {
            window.showNotification('Ошибка при инициализации приложения', 'error');
        }
    }
});

// Экспортируем модули для использования в других файлах
export { state, api, render, utils };

