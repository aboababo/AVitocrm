/**
 * Accessibility Module
 * Улучшения доступности: ARIA labels, keyboard navigation, screen reader support
 */

// Инициализация keyboard navigation
export function initKeyboardNavigation() {
    // Навигация по чатам с клавиатуры
    let currentChatIndex = -1;
    const chatCards = () => document.querySelectorAll('.chat-card');
    
    document.addEventListener('keydown', (e) => {
        // Работаем только если фокус не в input/textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const cards = chatCards();
        if (cards.length === 0) return;
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                currentChatIndex = Math.min(currentChatIndex + 1, cards.length - 1);
                cards[currentChatIndex]?.focus();
                cards[currentChatIndex]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                currentChatIndex = Math.max(currentChatIndex - 1, 0);
                cards[currentChatIndex]?.focus();
                cards[currentChatIndex]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                break;
                
            case 'Enter':
                if (currentChatIndex >= 0 && cards[currentChatIndex]) {
                    const chatId = cards[currentChatIndex].dataset.chatId;
                    if (chatId && window.selectChat) {
                        window.selectChat(Number(chatId));
                    }
                }
                break;
                
            case 'Escape':
                // Закрываем модальные окна
                const modals = document.querySelectorAll('.modal-backdrop[style*="flex"]');
                modals.forEach(modal => {
                    const closeBtn = modal.querySelector('button[onclick*="close"]');
                    if (closeBtn) closeBtn.click();
                });
                break;
        }
    });
    
    // Делаем карточки чатов фокусируемыми
    const observer = new MutationObserver(() => {
        chatCards().forEach(card => {
            if (!card.hasAttribute('tabindex')) {
                card.setAttribute('tabindex', '0');
                card.setAttribute('role', 'button');
            }
        });
    });
    
    observer.observe(document.getElementById('chats-list') || document.body, {
        childList: true,
        subtree: true
    });
}

// Добавление ARIA labels
export function addARIALabels() {
    // Поиск
    const searchInput = document.getElementById('chat-search');
    if (searchInput && !searchInput.getAttribute('aria-label')) {
        searchInput.setAttribute('aria-label', 'Поиск чатов');
        searchInput.setAttribute('aria-describedby', 'search-description');
    }
    
    // Кнопки фильтров
    document.querySelectorAll('.filter-chip').forEach((chip, index) => {
        if (!chip.getAttribute('aria-label')) {
            const sort = chip.dataset.sort || 'all';
            const labels = {
                'all': 'Показать все чаты',
                'my': 'Показать мои чаты',
                'pool': 'Показать пул чатов',
                'completed': 'Показать завершенные чаты',
                'blocked': 'Показать заблокированные чаты'
            };
            chip.setAttribute('aria-label', labels[sort] || 'Фильтр чатов');
            chip.setAttribute('role', 'button');
            chip.setAttribute('aria-pressed', chip.classList.contains('active') ? 'true' : 'false');
        }
    });
    
    // Кнопка отправки
    const sendButton = document.querySelector('.send-button');
    if (sendButton && !sendButton.getAttribute('aria-label')) {
        sendButton.setAttribute('aria-label', 'Отправить сообщение');
    }
    
    // Кнопки медиа
    document.querySelectorAll('.media-button').forEach(btn => {
        if (!btn.getAttribute('aria-label')) {
            const title = btn.getAttribute('title') || 'Загрузить файл';
            btn.setAttribute('aria-label', title);
        }
    });
    
    // Модальные окна
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        if (!modal.getAttribute('role')) {
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
        }
    });
    
    // Список чатов
    const chatsList = document.getElementById('chats-list');
    if (chatsList && !chatsList.getAttribute('role')) {
        chatsList.setAttribute('role', 'list');
        chatsList.setAttribute('aria-label', 'Список чатов');
    }
    
    // Область сообщений
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer && !messagesContainer.getAttribute('role')) {
        messagesContainer.setAttribute('role', 'log');
        messagesContainer.setAttribute('aria-label', 'Сообщения чата');
        messagesContainer.setAttribute('aria-live', 'polite');
    }
    
    // Поле ввода сообщения
    const messageInput = document.getElementById('message-text');
    if (messageInput && !messageInput.getAttribute('aria-label')) {
        messageInput.setAttribute('aria-label', 'Введите сообщение');
        messageInput.setAttribute('aria-describedby', 'message-hint');
    }
}

// Обновление ARIA labels при изменении состояния
export function updateARIAStates() {
    // Обновляем aria-pressed для фильтров
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.setAttribute('aria-pressed', chip.classList.contains('active') ? 'true' : 'false');
    });
    
    // Обновляем aria-expanded для выпадающих меню
    const quickRepliesMenu = document.getElementById('quick-replies-menu');
    if (quickRepliesMenu) {
        quickRepliesMenu.setAttribute('aria-expanded', quickRepliesMenu.classList.contains('active') ? 'true' : 'false');
    }
    
    // Обновляем aria-busy для состояния загрузки
    const chatsList = document.getElementById('chats-list');
    if (chatsList) {
        const isLoading = chatsList.querySelector('.chat-skeleton-card') !== null;
        chatsList.setAttribute('aria-busy', isLoading ? 'true' : 'false');
    }
}

// Объявление для screen readers
export function announceToScreenReader(message, priority = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Удаляем через некоторое время
    setTimeout(() => {
        announcement.remove();
    }, 1000);
}

// Инициализация всех улучшений доступности
export function initAccessibility() {
    addARIALabels();
    initKeyboardNavigation();
    
    // Обновляем ARIA labels при изменениях DOM
    const observer = new MutationObserver(() => {
        // Debounce для избежания частых обновлений
        if (observer.updateTimeout) {
            clearTimeout(observer.updateTimeout);
        }
        observer.updateTimeout = setTimeout(() => {
            addARIALabels();
            updateARIAStates();
        }, 100);
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class', 'style']
    });
    
    // Обновляем при изменении классов (для активных состояний) - реже для производительности
    setInterval(updateARIAStates, 2000);
}

