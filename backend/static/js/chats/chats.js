let currentChatId = null;
        let allChats = [];
        let filteredChats = [];
        let currentSort = 'all';
        let currentSortOrder = 'newest'; // 'newest' или 'oldest'
        let searchQuery = '';
        let autoRefreshInterval = null;
        let messagesAutoRefreshInterval = null;
        let quickRepliesCache = null;
        let quickRepliesCacheTime = 0;
        const CACHE_DURATION = 60000;
        
        // ОПТИМИЗАЦИЯ: Флаг для отладки (false в production)
        const DEBUG_MODE = false; // Отключено для производительности
        
        // Оптимизированная функция логирования - не выполняет ничего если DEBUG_MODE = false
        function debugLog(...args) {
            if (!DEBUG_MODE) return; // Быстрый выход без создания строк
            console.log(...args);
        }
        
        function debugError(...args) {
            if (!DEBUG_MODE) return;
            console.error(...args);
        }
        
        // ОПТИМИЗАЦИЯ: Кэш DOM элементов для быстрого доступа
        const domCache = {
            chatsList: null,
            myChatsCount: null,
            poolChatsCount: null,
            archiveCount: null,
            blockedCount: null
        };
        
        // ОПТИМИЗАЦИЯ: Флаг для предотвращения множественных одновременных рендеров
        let isRendering = false;
        let renderScheduled = false;
        
        // ОПТИМИЗАЦИЯ: Throttle для автообновления
        let lastAutoRefreshTime = 0;
        const AUTO_REFRESH_THROTTLE = 2000; // Минимум 2 секунды между обновлениями
        
        // Мемоизация для фильтрации чатов (улучшает производительность)
        function memoize(fn, keyFn) {
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
        
        // НОВЫЙ ПОДХОД: Set для отслеживания чатов, которые были взяты локально (до синхронизации с сервером)
        const locallyTakenChats = new Set();
        // Map для хранения timestamp каждого взятого чата (для автоматической очистки)
        const locallyTakenChatsTimestamps = new Map();
        
        // Кеширование чатов в localStorage для мгновенной загрузки
        const CHATS_CACHE_KEY = 'chats_cache';
        const CHATS_CACHE_TIMESTAMP_KEY = 'chats_cache_timestamp';
        const CHATS_CACHE_MAX_AGE = 5 * 60 * 1000; // 5 минут
        
        function saveChatsToCache(chats) {
            try {
                localStorage.setItem(CHATS_CACHE_KEY, JSON.stringify(chats));
                localStorage.setItem(CHATS_CACHE_TIMESTAMP_KEY, Date.now().toString());
            } catch (e) {
                console.warn('[CACHE] Ошибка сохранения в localStorage:', e);
            }
        }
        
        function loadChatsFromCache() {
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
        // Константы для задержек и таймаутов
        const DELAYS = {
            BATCH_TAKE_CLEANUP: 2000,        // Задержка перед очисткой locallyTakenChats
            PRODUCT_URL_EXTRACT: 3000,       // Задержка перед извлечением product_url
            AUTO_EXTRACT: 5000,              // Задержка перед автоматическим извлечением
            SYNC_RETRY: 1000,                // Задержка перед повторной попыткой синхронизации
            SEARCH_DEBOUNCE: 300             // Debounce для поиска (улучшает производительность)
        };
        
        const SEARCH_DEBOUNCE = DELAYS.SEARCH_DEBOUNCE; // Debounce для поиска
        const currentUsername = '{{ user.username if user else "" }}';
        // ВАЖНО: Проверяем на None, так как user.id может быть 0 (валидное значение)
        const currentUserId = {% if user and user.id is not none %}{{ user.id }}{% else %}null{% endif %};
        const currentUserRole = '{{ user.role if user else "" }}';
        const isAdmin = currentUserRole === 'admin' || currentUserRole === 'super_admin';
        const MESSAGE_PAGE = 50;
        let messagesState = {};
        let currentChatHasAvito = true;
        let chatsLoading = false;
        let chatsLoadError = null;
        let searchDebounceTimer = null;
        let initialChatIdFromUrl = null;
        let chatIdFromUrlHandled = false;
        let messagesLoading = false;
        let unreadFromRefresh = 0;

        function escapeHtml(value) {
            if (value === null || value === undefined) return '';
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function escapeRegExp(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }

        function highlightText(text, query) {
            const safe = escapeHtml(text || '');
            const q = (query || '').trim();
            if (!q) return safe;
            const pattern = new RegExp(escapeRegExp(q), 'gi');
            return safe.replace(pattern, (m) => `<mark>${m}</mark>`);
        }

        function getChatsSkeletonMarkup() {
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

        // Загрузка чатов (глобальная функция)
        window.loadChats = async function loadChats(doSync = false, silent = false) {
            debugLog('========================================');
            debugLog('[LOAD CHATS] Начинаем загрузку чатов');
            debugLog('[LOAD CHATS] doSync:', doSync, 'silent:', silent);
            debugLog('[LOAD CHATS] Время:', new Date().toISOString());
            
            try {
            debugLog('========================================');
            
            const isFirstLoad = allChats.length === 0;
            
            // ВСЕГДА показываем кеш сразу, если он есть (даже при первой загрузке)
            const cachedChats = loadChatsFromCache();
            if (cachedChats && cachedChats.length > 0) {
                allChats = cachedChats;
                resetTimerBaseTimes();
                applySort(currentSort);
                renderChatsList();
                // Обновляем таймеры для кешированных чатов
                updateResponseTimers();
                debugLog('[LOAD CHATS] ✅ Показаны кешированные чаты мгновенно, обновляем в фоне...');
            } else if (isFirstLoad && !silent) {
                // Только если нет кеша и это первая загрузка - показываем скелетон
            chatsLoading = true;
            chatsLoadError = null;
            renderChatsList();
            }
            
            // Синхронизация ТОЛЬКО в фоне, не блокируем UI
            // Запускаем синхронизацию асинхронно, не ждем её завершения
            if (doSync || isFirstLoad) {
                // Запускаем синхронизацию в фоне, не блокируя загрузку чатов
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
                        // После синхронизации обновляем чаты тихо
                        loadChats(false, true).then(() => {
                            // Автоматически извлекаем product_url для чатов без него
                            setTimeout(() => {
                                autoExtractProductUrls();
                            }, DELAYS.PRODUCT_URL_EXTRACT);
                        }).catch(() => {});
                    } else {
                        syncResponse.json().then(errorData => {
                            debugLog('[LOAD CHATS] Синхронизация не удалась, продолжаем загрузку:', errorData);
                        }).catch(() => {});
                    }
                }).catch(syncError => {
                    debugLog('[LOAD CHATS] Ошибка синхронизации, продолжаем загрузку:', syncError);
                });
            }

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
                
                // ОПТИМИЗАЦИЯ: Улучшенная обработка ошибок с retry логикой
                const MAX_RETRIES = 3;
                let lastError = null;
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
                    lastError = error;
                    // Если есть кеш, не показываем ошибку, используем кеш
                    if (allChats.length > 0) {
                        chatsLoading = false;
                        return;
                    }
                    // Показываем понятное сообщение пользователю
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
                
                // Обрабатываем успешный ответ
                if (!response || !response.ok) {
                    if (allChats.length > 0) {
                        chatsLoading = false;
                        return;
                    }
                    throw lastError || new Error('Не удалось загрузить чаты');
                }
                
                const data = await response.json();
                
                const items = Array.isArray(data) ? data : (Array.isArray(data.items) ? data.items : []);
            
            // Валидация данных чатов перед использованием
            function validateChatData(chat) {
                if (!chat || typeof chat !== 'object') return false;
                if (typeof chat.id !== 'number' || chat.id <= 0) return false;
                if (typeof chat.status !== 'string') return false;
                if (chat.assigned_manager_id !== null && chat.assigned_manager_id !== undefined && 
                    typeof chat.assigned_manager_id !== 'number') return false;
                return true;
            }
            
            const validChats = items.filter(validateChatData);
            if (validChats.length !== items.length) {
                debugLog(`[LOAD CHATS] Отфильтровано ${items.length - validChats.length} невалидных чатов из ${items.length}`);
            }
            
            // Сохраняем количество существующих чатов для определения, нужно ли полное обновление
            const existingChatsCount = allChats.length;
            
                // НОВЫЙ ПОДХОД: Обновляем allChats данными с сервера
                // Но сохраняем локальные изменения для чатов, которые были взяты локально
                allChats = validChats;
                
                debugLog('[LOAD CHATS] Загружено чатов:', items.length, 'было:', existingChatsCount);
                
                // ВАЖНО: Обновляем локальные изменения для чатов, которые были взяты локально
                // но сервер еще не обновил (или обновил неправильно)
                if (DEBUG_MODE) {
                    debugLog('[LOAD CHATS] Локально взятые чаты перед обновлением:', Array.from(locallyTakenChats));
                    debugLog('[LOAD CHATS] currentUserId:', currentUserId, 'currentUsername:', currentUsername);
                }
                
                locallyTakenChats.forEach(chatId => {
                    const chatIndex = allChats.findIndex(c => c.id === chatId);
                    if (chatIndex !== -1) {
                        const chat = allChats[chatIndex];
                        if (DEBUG_MODE) {
                            debugLog('[LOAD CHATS] Обрабатываем локально взятый чат', chatId, {
                                assigned_manager_id: chat.assigned_manager_id,
                                assigned_manager_name: chat.assigned_manager_name,
                                currentUserId: currentUserId
                            });
                        }
                        
                        // Если чат был взят локально, но сервер еще не обновил assigned_manager_id,
                        // сохраняем локальные изменения
                        if (!chat.assigned_manager_id || chat.assigned_manager_id === null || chat.assigned_manager_id === undefined) {
                            chat.assigned_manager_id = currentUserId;
                            chat.assigned_manager_name = currentUsername;
                            debugLog('[LOAD CHATS] ✅ Сохранены локальные изменения для чата', chatId, 'assigned_manager_id установлен в', currentUserId);
                        } else if (chat.assigned_manager_id === currentUserId) {
                            // Сервер подтвердил, что чат взят - можно удалить из Set
                            debugLog('[LOAD CHATS] ✅ Сервер подтвердил назначение чата', chatId, 'удаляем из locallyTakenChats');
                            locallyTakenChats.delete(chatId);
                            locallyTakenChatsTimestamps.delete(chatId);
                        } else {
                            // Сервер вернул другой ID - это странно, но сохраняем локальное значение
                            if (DEBUG_MODE) {
                                console.warn('[LOAD CHATS] ⚠️ Сервер вернул другой assigned_manager_id для чата', chatId, 
                                           'ожидали:', currentUserId, 'получили:', chat.assigned_manager_id);
                            }
                            // Сохраняем локальное значение, так как мы взяли чат локально
                            chat.assigned_manager_id = currentUserId;
                            chat.assigned_manager_name = currentUsername;
                        }
                    } else {
                        if (DEBUG_MODE) {
                            console.warn('[LOAD CHATS] ⚠️ Локально взятый чат', chatId, 'не найден в allChats после загрузки с сервера');
                        }
                    }
                });
                
                if (DEBUG_MODE) {
                    debugLog('[LOAD CHATS] Локально взятые чаты после обновления:', Array.from(locallyTakenChats));
                }
                
                // Сбрасываем базовое время для таймеров при обновлении данных с сервера
                resetTimerBaseTimes();
                
                // Сохраняем в кеш для мгновенной загрузки в следующий раз
                saveChatsToCache(allChats);
                
                // Обновляем таймеры сразу после загрузки, чтобы они отображались
                updateResponseTimers();
                
                // Автоматически извлекаем product_url для новых чатов без него (только при первой загрузке)
                if (isFirstLoad) {
                    // Запускаем автоматическое извлечение после загрузки
                    setTimeout(() => {
                        autoExtractProductUrls();
                    }, DELAYS.PRODUCT_URL_EXTRACT);
                }
                
                const completedCount = allChats.filter(chat => chat.status === 'completed').length;
                const blockedCount = allChats.filter(chat => chat.status === 'blocked').length;
                const poolCount = allChats.filter(chat => 
                    chat.status !== 'completed' && 
                    chat.status !== 'blocked' && 
                    !chat.assigned_manager_id
                ).length;
                const myChatsCount = allChats.filter(chat => {
                    if (chat.status === 'completed' || chat.status === 'blocked') return false;
                    if (!chat.assigned_manager_id) return false;
                    // Проверяем по ID (более надежно) или по имени
                    return chat.assigned_manager_id === currentUserId || 
                           chat.assigned_manager_name === currentUsername ||
                           (chat.assigned_manager_name && currentUsername && 
                            chat.assigned_manager_name.includes(currentUsername));
                }).length;
                
                document.getElementById('archive-count').textContent = `(${completedCount})`;
                document.getElementById('blocked-count').textContent = `(${blockedCount})`;
                document.getElementById('my-chats-count').textContent = `(${myChatsCount})`;
                
                // Применяем сортировку и фильтрацию
                // При первой загрузке или если список был пуст, используем полную перерисовку
                // Иначе используем умное обновление для избежания мерцания
                const wasEmpty = existingChatsCount === 0;
                const shouldUseSmartUpdate = !isFirstLoad && !wasEmpty && existingChatsCount > 0;
                
                debugLog('[LOAD CHATS] Применяем сортировку. isFirstLoad:', isFirstLoad, 'wasEmpty:', wasEmpty, 'shouldUseSmartUpdate:', shouldUseSmartUpdate);
                
                applySort(currentSort, shouldUseSmartUpdate);
                // ВСЕГДА обновляем список, чтобы новые чаты появлялись
                // Умное обновление применяется внутри applySort, но renderChatsList нужен для новых элементов
                renderChatsList();
                attemptOpenChatFromUrl();
                
                // Автоматическое извлечение product_url для чатов без него (в фоне)
                // Запускаем через функцию autoExtractProductUrls, которая обрабатывает батчами
                if (isFirstLoad) {
                    setTimeout(() => {
                        autoExtractProductUrls();
                    }, DELAYS.AUTO_EXTRACT);
                }
            } catch (error) {
            console.error('[LOAD CHATS] Ошибка загрузки чатов:', error);
            showNotification('Не удалось загрузить чаты: ' + error.message, 'error');
            chatsLoadError = error;
        } finally {
            chatsLoading = false;
            debugLog('[LOAD CHATS] finally блок: вызываем renderChatsList()...');
            try {
                renderChatsList();
                debugLog('[LOAD CHATS] finally: renderChatsList() вызван успешно');
            } catch (error) {
                debugError('[LOAD CHATS] finally: ОШИБКА при вызове renderChatsList():', error);
            }
        }
    }

        function attemptOpenChatFromUrl() {
            if (chatIdFromUrlHandled || !initialChatIdFromUrl) return;
            const chatIdNum = Number(initialChatIdFromUrl);
            if (Number.isNaN(chatIdNum)) {
                chatIdFromUrlHandled = true;
                return;
            }
            const chat = allChats.find(c => c.id === chatIdNum);
            if (chat) {
                chatIdFromUrlHandled = true;
                selectChat(chatIdNum);
            } else if (allChats.length > 0) {
                showNotification('Чат из URL не найден', 'error');
                chatIdFromUrlHandled = true;
            }
        }

        // Поиск
        function searchChats(query) {
            searchQuery = query.toLowerCase().trim();
            try {
            applySort(currentSort);
            } catch (error) {
                console.error('Error in chat search:', error);
            }
        }

        function handleSearchInput(value) {
            // Используем debounce для оптимизации производительности
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(() => {
                searchChats(value);
            }, DELAYS.SEARCH_DEBOUNCE);
        }

        // Синхронизация чатов (переопределяем для использования локальных функций)
        window.syncChats = async function syncChats() {
            const btn = document.getElementById('sync-btn');
            if (!btn) {
                console.error('Кнопка синхронизации не найдена');
                return;
            }
            const originalText = btn.innerHTML;

            try {
                btn.classList.add('syncing');
                btn.innerHTML = '⏳ Синхронизация...';
                btn.disabled = true;

                const response = await fetch('/api/chats/sync', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({})
                });


                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    console.error('[SYNC] Ошибка ответа:', errorData);
                    throw new Error(errorData.error || `Ошибка синхронизации: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.success) {
                    showNotification(`✅ Синхронизировано ${result.synced_count || 0} чатов`, 'success');
                } else {
                    showNotification(`⚠️ ${result.error || 'Синхронизация завершена с ошибками'}`, 'error');
                }
                
                // Обновляем чаты после синхронизации
                await loadChats(false); // Без повторной синхронизации
            } catch (error) {
                console.error('[SYNC] Ошибка синхронизации:', error);
                showNotification(`❌ ${error.message}`, 'error');
            } finally {
                btn.classList.remove('syncing');
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        };

        // Мемоизированная функция фильтрации
        const memoizedFilterChats = memoize(
            (chats, sort, userId, username, locallyTakenSet) => {
                let baseChats = [];
                
                // Фильтрация по статусу и типу
                if (sort === 'completed') {
                    baseChats = chats.filter(chat => chat.status === 'completed');
                } else if (sort === 'blocked') {
                    baseChats = chats.filter(chat => chat.status === 'blocked');
                } else if (sort === 'all') {
                    baseChats = chats.filter(chat => {
                        if (locallyTakenSet.has(chat.id)) return false;
                        const isNotAssigned = chat.assigned_manager_id === null || 
                                            chat.assigned_manager_id === undefined || 
                                            chat.assigned_manager_id === false;
                        const isValidStatus = chat.status !== 'completed' && chat.status !== 'blocked';
                        return isNotAssigned && isValidStatus;
                    });
                } else if (sort === 'my') {
                    baseChats = chats.filter(chat => {
                        if (chat.status === 'completed' || chat.status === 'blocked') return false;
                        if (!chat.assigned_manager_id) return false;
                        const isAssignedToMe = chat.assigned_manager_id === userId;
                        const isAssignedByName = !isAssignedToMe && (
                            chat.assigned_manager_name === username ||
                            (chat.assigned_manager_name && username && 
                             chat.assigned_manager_name.includes(username))
                        );
                        const isLocallyTaken = locallyTakenSet.has(chat.id);
                        if (isLocallyTaken && (!chat.assigned_manager_id || chat.assigned_manager_id === null)) {
                            chat.assigned_manager_id = userId;
                            chat.assigned_manager_name = username;
                        }
                        return isAssignedToMe || isAssignedByName || isLocallyTaken;
                    });
                } else {
                    baseChats = chats.filter(chat => chat.status === 'active');
                }
                
                return baseChats;
            },
            (chats, sort, userId, username, locallyTakenSet) => 
                `${chats.length}-${sort}-${userId}-${username}-${locallyTakenSet.size}`
        );
        
        // Применение сортировки и фильтрации - МГНОВЕННО, без запросов к серверу
        function applySort(sort, useSmartUpdate = false) {
            // Мгновенно обновляем активный фильтр в UI
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            const activeChip = document.querySelector(`.filter-chip[data-sort="${sort}"]`);
            if (activeChip) activeChip.classList.add('active');
            
            currentSort = sort;
            
            // Используем мемоизированную фильтрацию для улучшения производительности
            let baseChats = memoizedFilterChats(allChats, sort, currentUserId, currentUsername, locallyTakenChats);
            
            if (DEBUG_MODE && sort === 'my') {
                debugLog('[APPLY SORT] Фильтр "Мои чаты": currentUserId=', currentUserId, 'currentUsername=', currentUsername);
                debugLog('[APPLY SORT] Всего чатов в allChats:', allChats.length);
                debugLog('[APPLY SORT] Отфильтровано чатов для "Мои чаты":', baseChats.length);
                debugLog('[APPLY SORT] Локально взятые чаты:', Array.from(locallyTakenChats));
            }

            debugLog('[APPLY SORT] После фильтрации по статусу:', baseChats.length, 'из', allChats.length);

            // Умные фильтры
            const filterShop = document.getElementById('filter-shop')?.value || '';
            const filterManager = document.getElementById('filter-manager')?.value || '';
            const filterTime = document.getElementById('filter-time')?.value || '';
            
            if (filterShop) {
                baseChats = baseChats.filter(chat => chat.shop_id && String(chat.shop_id) === filterShop);
            }
            if (filterManager) {
                baseChats = baseChats.filter(chat => chat.assigned_manager_id && String(chat.assigned_manager_id) === filterManager);
            }
            if (filterTime) {
                const minTime = parseInt(filterTime);
                baseChats = baseChats.filter(chat => {
                    const timer = typeof chat.response_timer === 'number' ? chat.response_timer : (parseInt(chat.response_timer) || 0);
                    return timer >= minTime;
                });
            }

            // Поиск
            if (searchQuery) {
                const beforeSearch = baseChats.length;
                baseChats = baseChats.filter(chat => {
                    const name = (chat.client_name || '').toLowerCase();
                    const phone = (chat.client_phone || '').toLowerCase();
                    const message = (chat.last_message || '').toLowerCase();
                    const shop = (chat.shop_name || '').toLowerCase();
                    return name.includes(searchQuery) || 
                           phone.includes(searchQuery) || 
                           message.includes(searchQuery) ||
                           shop.includes(searchQuery);
                });
                debugLog('[APPLY SORT] После поиска:', beforeSearch, '->', baseChats.length);
            }

            // Сортировка по времени без ответа (response_timer)
            debugLog('[APPLY SORT] Перед сортировкой:', baseChats.length, 'чатов');
            filteredChats = baseChats.sort((a, b) => {
                // Функция для получения response_timer (время без ответа в минутах)
                const getResponseTimer = (chat) => {
                    const timer = chat.response_timer;
                    if (timer === null || timer === undefined) return 0;
                    return typeof timer === 'number' ? timer : (parseInt(timer) || 0);
                };
                
                const timerA = getResponseTimer(a);
                const timerB = getResponseTimer(b);
                
                // Сортировка только по времени без ответа (приоритеты убраны)
                
                // Затем сортируем по времени без ответа (response_timer)
                // Сначала чаты с неотвеченными сообщениями (timer > 0), затем отвеченные (timer = 0)
                if (timerA > 0 && timerB === 0) return -1; // a выше (есть неотвеченные)
                if (timerA === 0 && timerB > 0) return 1;  // b выше (есть неотвеченные)
                
                // Если оба имеют timer > 0 или оба имеют timer = 0, сортируем по timer
                if (currentSortOrder === 'oldest') {
                    // Старые сверху: больший timer сверху (больше времени без ответа = старее)
                    return timerB - timerA;
                } else {
                    // Новые сверху: меньший timer сверху (меньше времени без ответа = новее, только что пришли)
                    return timerA - timerB;
                }
            });
            
            debugLog('[APPLY SORT] Итоговое количество отфильтрованных чатов:', filteredChats.length);
            try {
                if (useSmartUpdate) {
                    // Используем умное обновление для избежания мерцания
                    updateChatsListSmart();
                } else {
                    // Полная перерисовка только при необходимости (изменение фильтра, поиск и т.д.)
                    renderChatsList();
                }
            } catch (error) {
                console.error('[APPLY SORT] ОШИБКА при обновлении списка чатов:', error);
                // Fallback на полную перерисовку при ошибке
                if (!useSmartUpdate) {
                    renderChatsList();
                }
            }
            // Обновляем активные фильтры
            document.querySelectorAll('.filter-chip[data-sort]').forEach(chip => {
                chip.classList.toggle('active', chip.dataset.sort === sort);
            });
            
            // Обновляем активную сортировку
            document.querySelectorAll('.sort-chip[data-sort-order]').forEach(chip => {
                chip.classList.toggle('active', chip.dataset.sortOrder === currentSortOrder);
            });
            
            // Показываем/скрываем кнопку "Вернуть все в пул" только для фильтра "Мои чаты"
            const returnAllBtn = document.getElementById('return-all-btn');
            if (returnAllBtn) {
                if (sort === 'my') {
                    returnAllBtn.classList.remove('hidden');
                } else {
                    returnAllBtn.classList.add('hidden');
                }
            }
        }

        // ОПТИМИЗАЦИЯ: Инициализация кэша DOM элементов
        function initDOMCache() {
            if (!domCache.chatsList) {
                domCache.chatsList = document.getElementById('chats-list');
                domCache.myChatsCount = document.getElementById('my-chats-count');
                domCache.poolChatsCount = document.getElementById('pool-chats-count');
                domCache.archiveCount = document.getElementById('archive-count');
                domCache.blockedCount = document.getElementById('blocked-count');
            }
        }
        
        // ОПТИМИЗАЦИЯ: Отрисовка списка чатов с использованием requestAnimationFrame и DocumentFragment
        function renderChatsList() {
            // Предотвращаем множественные одновременные рендеры
            if (isRendering) {
                renderScheduled = true;
                return;
            }
            
            // Используем requestAnimationFrame для плавного рендеринга
            if (renderScheduled) {
                return;
            }
            
            renderScheduled = true;
            // Оптимизация: разбиваем рендеринг на части для больших списков
            const CHUNK_SIZE = 50; // Рендерим по 50 чатов за раз
            const totalChats = filteredChats.length;
            
            requestAnimationFrame(() => {
                renderScheduled = false;
                isRendering = true;
                
                try {
                    // Инициализируем кэш DOM элементов
                    initDOMCache();
                    const container = domCache.chatsList;
                    
                    if (!container) {
                        debugError('[RENDER] ❌ КОНТЕЙНЕР НЕ НАЙДЕН!');
                        isRendering = false;
                        return;
                    }

                    if (chatsLoading) {
                        isRendering = false;
                        return;
                    }

                    if (chatsLoadError) {
                        container.innerHTML = `
                            <div class="empty-list">
                                <div class="empty-list-icon">⚠️</div>
                                <h3>Не удалось загрузить чаты</h3>
                                <p>Проверьте соединение и обновите страницу</p>
                                <button class="retry-button" onclick="loadChats()">🔄 Повторить</button>
                            </div>
                        `;
                        isRendering = false;
                        return;
                    }

                    if (filteredChats.length === 0) {
                        debugLog('[RENDER] Нет отфильтрованных чатов. allChats:', allChats.length, 'currentSort:', currentSort, 'searchQuery:', searchQuery);
                        if (allChats.length > 0 && DEBUG_MODE) {
                            debugLog('[RENDER] Примеры чатов из allChats:', allChats.slice(0, 3).map(c => ({
                                id: c.id,
                                client_name: c.client_name,
                                status: c.status,
                                assigned_manager_id: c.assigned_manager_id,
                                priority: c.priority
                            })));
                        }
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
                    
                        debugLog('[RENDER] Отрисовываем', filteredChats.length, 'чатов');

                        const html = filteredChats.map((chat, index) => {
                            const isCompleted = chat.status === 'completed';
                            const isBlocked = chat.status === 'blocked';
                            const isInPool = !chat.assigned_manager_id && !isCompleted && !isBlocked;
                            const isMyChat = chat.assigned_manager_id && 
                                (chat.assigned_manager_id === currentUserId || 
                                 chat.assigned_manager_name === currentUsername ||
                                 (chat.assigned_manager_name && currentUsername && 
                                  chat.assigned_manager_name.includes(currentUsername)));
                            // Убеждаемся, что response_timer - это число
                            const responseTimer = typeof chat.response_timer === 'number' ? chat.response_timer : (parseInt(chat.response_timer) || 0);
                            const timerClass = getTimerClass(responseTimer);
                            const timerText = formatTimer(responseTimer);
                            // Добавляем класс blink-red если чат без ответа более 20 минут
                            const blinkClass = (!isCompleted && !isBlocked && responseTimer >= 20) ? 'blink-red' : '';
                            const cardClass = `chat-card ${currentChatId === chat.id ? 'active' : ''} ${isInPool ? 'pool' : ''} ${blinkClass}`;
                            const avitoOk = chat.avito_credentials_status === 'ok' || chat.has_avito_creds;
                            const webhookOk = !!chat.webhook_registered;
                            const safeClientName = highlightText(chat.client_name || '', searchQuery);
                            const safeShopName = highlightText(chat.shop_name || '', searchQuery);
                            const safeLastMessage = highlightText(chat.last_message || 'Нет сообщений', searchQuery);
                            
                            return `
                    <div class="${cardClass}" onclick="selectChat(Number(${chat.id}))" data-chat-id="${chat.id}" data-shop-id="${chat.shop_id || ''}" data-manager-id="${chat.assigned_manager_id || ''}" data-response-timer="${responseTimer}">
                        <div class="chat-card-header" style="display: flex; align-items: start; gap: 0.5rem;">
                            <input type="checkbox" class="chat-select-checkbox" onclick="event.stopPropagation(); toggleChatSelection(${chat.id})" style="margin-top: 0.25rem; cursor: pointer; width: 18px; height: 18px; flex-shrink: 0;" data-chat-id="${chat.id}">
                            <div style="flex: 1; min-width: 0;">
                            <div class="chat-card-title">
                                <div class="chat-client-name">${safeClientName}</div>
                                <div class="chat-shop-name">${safeShopName}</div>
                            </div>
                            </div>
                            </div>
                            <div class="chat-badges" style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                                ${isInPool ? '<span class="pool-badge">🌊 ПУЛ</span>' : ''}
                                ${chat.unread_count > 0 ? `<span class="unread-count">${chat.unread_count}</span>` : ''}
                                ${isAdmin ? (avitoOk ? '<span class="pool-badge" style="background: #10b981;">🔑 Avito</span>' : '<span class="pool-badge" style="background: #ef4444;">🔑 Нет ключей</span>') : ''}
                                ${isAdmin && webhookOk ? '<span class="pool-badge" style="background: #6b7280;">🔔 Webhook</span>' : ''}
                                ${isInPool ? `
                                    <button class="quick-take-btn" onclick="event.stopPropagation(); takeChatFromPool(${chat.id})" title="Взять чат из пула">
                                        📥 Взять
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                        <div class="chat-preview">${safeLastMessage}</div>
                        <div class="chat-footer">
                            ${isCompleted ? 
                                '<span class="priority-tag priority-completed">📦 ЗАВЕРШЕН</span>' :
                                isBlocked ?
                                '<span class="priority-tag" style="background: #ef4444; color: white;">🚫 ЗАБЛОКИРОВАН</span>' :
                                ''
                            }
                            ${!isCompleted && !isBlocked && responseTimer > 0 ? `<span class="response-time ${timerClass} ${responseTimer >= 20 ? 'blink' : ''}" style="${responseTimer >= 20 ? 'color: #ef4444; font-weight: 700;' : ''}" title="Время без ответа">⏱️ ${timerText}</span>` : ''}
                        </div>
                        ${isMyChat ? `
                            <div class="chat-card-actions">
                                <button class="quick-action-btn return" onclick="event.stopPropagation(); returnChatToPool(${chat.id})" title="Вернуть в пул">
                                    📤 Вернуть
                            </button>
                                <button class="quick-action-btn" onclick="event.stopPropagation(); markAsCompleted(${chat.id})" title="Завершить чат">
                                    ✅ Завершить
                            </button>
                                <button class="quick-action-btn" onclick="event.stopPropagation(); blockChat(${chat.id})" title="Заблокировать чат">
                                    🚫 Заблокировать
                                </button>
                            </div>
                        ` : ''}
                            </div>
                            `;
                        }).join('');
                        
                        debugLog('[RENDER] Сгенерировано HTML, длина:', html.length);
                        
                        // ОПТИМИЗАЦИЯ: Используем DocumentFragment для batch DOM операций
                        const fragment = document.createDocumentFragment();
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = html;
                        
                        // Перемещаем все элементы в fragment
                        while (tempDiv.firstChild) {
                            fragment.appendChild(tempDiv.firstChild);
                        }
                        
                        // ОПТИМИЗАЦИЯ: Временно скрываем контейнер для избежания моргания при обновлении
                        const originalDisplay = container.style.display;
                        container.style.display = 'none';
                        container.innerHTML = '';
                        container.appendChild(fragment);
                        // Восстанавливаем display сразу (без requestAnimationFrame для мгновенного обновления)
                        container.style.display = originalDisplay;
                        isRendering = false;
                } catch (error) {
                    debugError('[RENDER] ❌ ОШИБКА в renderChatsList:', error);
                    if (DEBUG_MODE) console.error('[RENDER] Stack:', error.stack);
                } finally {
                    isRendering = false;
                }
            });
        }

        /**
         * Умное обновление списка чатов без полной перерисовки
         * Обновляет только измененные элементы, добавляет новые, удаляет удаленные
         */
        function updateChatsListSmart() {
            const container = domCache.chatsList;
            if (!container) {
                // Если контейнер не найден, используем полную перерисовку
                debugLog('[SMART UPDATE] Контейнер не найден, используем полную перерисовку');
                renderChatsList();
                return;
            }
            
            // Если список пуст, используем полную перерисовку
            if (filteredChats.length === 0) {
                debugLog('[SMART UPDATE] Список пуст, используем полную перерисовку');
                renderChatsList();
                return;
            }
            
            debugLog('[SMART UPDATE] Начинаем умное обновление. Всего чатов:', filteredChats.length);
            
            // Получаем текущие элементы чатов из DOM
            const existingChats = new Map();
            container.querySelectorAll('.chat-card').forEach(card => {
                const chatId = card.getAttribute('data-chat-id');
                if (chatId) {
                    existingChats.set(Number(chatId), card);
                }
            });
            
            // Создаем Map новых чатов для быстрого поиска
            const newChatsMap = new Map();
            filteredChats.forEach(chat => {
                newChatsMap.set(chat.id, chat);
            });
            
            // Находим чаты для обновления, добавления и удаления
            const chatsToUpdate = [];
            const chatsToAdd = [];
            const chatsToRemove = [];
            
            // Проверяем существующие чаты
            existingChats.forEach((card, chatId) => {
                if (newChatsMap.has(chatId)) {
                    // Чат существует - проверяем, нужно ли обновить
                    chatsToUpdate.push(chatId);
                } else {
                    // Чат удален
                    chatsToRemove.push(card);
                }
            });
            
            // Находим новые чаты (с учетом правильного порядка)
            filteredChats.forEach(chat => {
                if (!existingChats.has(chat.id)) {
                    chatsToAdd.push(chat);
                }
            });
            
            debugLog('[SMART UPDATE] Найдено для обновления:', chatsToUpdate.length, 'для добавления:', chatsToAdd.length, 'для удаления:', chatsToRemove.length);
            
            // ОПТИМИЗАЦИЯ: Batch updates для обновления существующих чатов
            // Группируем все DOM операции и выполняем их в одном batch через requestAnimationFrame
            // Это предотвращает множественные reflow/repaint операции
            const updateBatch = [];
            
            chatsToUpdate.forEach(chatId => {
                const chat = newChatsMap.get(chatId);
                const existingCard = existingChats.get(chatId);
                if (!chat || !existingCard) return;
                
                // Обновляем только ключевые элементы, которые могут измениться
                const isActive = currentChatId === chatId;
                const responseTimer = typeof chat.response_timer === 'number' ? chat.response_timer : (parseInt(chat.response_timer) || 0);
                const isCompleted = chat.status === 'completed';
                const isBlocked = chat.status === 'blocked';
                const blinkClass = (!isCompleted && !isBlocked && responseTimer >= 20) ? 'blink-red' : '';
                
                // Добавляем все операции обновления в batch
                updateBatch.push(() => {
                    // Обновляем классы
                    existingCard.className = `chat-card ${isActive ? 'active' : ''} ${!chat.assigned_manager_id && !isCompleted && !isBlocked ? 'pool' : ''} ${blinkClass}`;
                    
                    // Обновляем счетчик непрочитанных
                    const unreadBadge = existingCard.querySelector('.unread-count');
                    if (chat.unread_count > 0) {
                        if (!unreadBadge) {
                            const badges = existingCard.querySelector('.chat-badges');
                            if (badges) {
                                const badge = document.createElement('span');
                                badge.className = 'unread-count';
                                badge.textContent = chat.unread_count;
                                try {
                                    if (badges.firstChild) {
                                        badges.insertBefore(badge, badges.firstChild);
                                    } else {
                                        badges.appendChild(badge);
                                    }
                                } catch (error) {
                                    // Если не удалось вставить перед firstChild, просто добавляем
                                    badges.appendChild(badge);
                                }
                            }
                        } else {
                            unreadBadge.textContent = chat.unread_count;
                        }
                    } else if (unreadBadge) {
                        unreadBadge.remove();
                    }
                    
                    // Обновляем таймер ответа
                    const timerElement = existingCard.querySelector('.response-time');
                    if (responseTimer > 0 && !isCompleted && !isBlocked) {
                        const timerText = formatTimer(responseTimer);
                        const timerClass = getTimerClass(responseTimer);
                        if (timerElement) {
                            timerElement.textContent = `⏱️ ${timerText}`;
                            timerElement.className = `response-time ${timerClass} ${responseTimer >= 20 ? 'blink' : ''}`;
                            timerElement.style.color = responseTimer >= 20 ? '#ef4444' : '';
                            timerElement.style.fontWeight = responseTimer >= 20 ? '700' : '';
                        } else {
                            const footer = existingCard.querySelector('.chat-footer');
                            if (footer) {
                                const timer = document.createElement('span');
                                timer.className = `response-time ${timerClass} ${responseTimer >= 20 ? 'blink' : ''}`;
                                timer.style.color = responseTimer >= 20 ? '#ef4444' : '';
                                timer.style.fontWeight = responseTimer >= 20 ? '700' : '';
                                timer.textContent = `⏱️ ${timerText}`;
                                timer.title = 'Время без ответа';
                                footer.appendChild(timer);
                            }
                        }
                    } else if (timerElement) {
                        timerElement.remove();
                    }
                    
                    // Обновляем последнее сообщение
                    const preview = existingCard.querySelector('.chat-preview');
                    if (preview) {
                        const safeLastMessage = highlightText(chat.last_message || 'Нет сообщений', searchQuery);
                        preview.innerHTML = safeLastMessage;
                    }
                });
            });
            
            // Выполняем все обновления в одном batch через requestAnimationFrame
            // Это предотвращает множественные reflow/repaint операции
            if (updateBatch.length > 0) {
                requestAnimationFrame(() => {
                    updateBatch.forEach(updateFn => updateFn());
                });
            }
            
            // Удаляем удаленные чаты в batch
            if (chatsToRemove.length > 0) {
                requestAnimationFrame(() => {
                    chatsToRemove.forEach(card => card.remove());
                });
            }
            
            // ОПТИМИЗАЦИЯ: Batch updates для добавления новых чатов
            // Используем DocumentFragment для batch операций DOM
            if (chatsToAdd.length > 0) {
                debugLog('[SMART UPDATE] Добавляем', chatsToAdd.length, 'новых чатов (batch mode)');
                
                // Создаем DocumentFragment для batch операций
                const fragment = document.createDocumentFragment();
                const insertions = []; // Массив для отслеживания позиций вставки
                
                // Подготавливаем все новые элементы в fragment
                chatsToAdd.forEach(chat => {
                    const chatHtml = renderSingleChat(chat);
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = chatHtml;
                    const newCard = tempDiv.firstChild;
                    if (!newCard) {
                        debugLog('[SMART UPDATE] Не удалось создать элемент для чата', chat.id);
                        return;
                    }
                    
                    // Находим правильную позицию для вставки
                    let insertBefore = null;
                    for (let i = 0; i < filteredChats.length; i++) {
                        if (filteredChats[i].id === chat.id) {
                            // Находим следующий существующий элемент после этого чата
                            for (let j = i + 1; j < filteredChats.length; j++) {
                                const nextChat = filteredChats[j];
                                const nextCard = container.querySelector(`[data-chat-id="${nextChat.id}"]`);
                                if (nextCard) {
                                    insertBefore = nextCard;
                                    break;
                                }
                            }
                            break;
                        }
                    }
                    
                    insertions.push({ card: newCard, insertBefore: insertBefore, chatId: chat.id });
                });
                
                // Выполняем все вставки в одном batch через requestAnimationFrame
                requestAnimationFrame(() => {
                    insertions.forEach(({ card, insertBefore, chatId }) => {
                        try {
                            if (insertBefore && container.contains(insertBefore)) {
                                // Проверяем, что insertBefore все еще является дочерним элементом container
                                container.insertBefore(card, insertBefore);
                                debugLog('[SMART UPDATE] Добавлен новый чат', chatId, 'перед', insertBefore.getAttribute('data-chat-id'));
                            } else {
                                // Если insertBefore не найден или больше не является дочерним, добавляем в конец
                                container.appendChild(card);
                                debugLog('[SMART UPDATE] Добавлен новый чат', chatId, 'в конец списка (insertBefore невалиден)');
                            }
                        } catch (error) {
                            // Если произошла ошибка, просто добавляем в конец
                            console.warn('[SMART UPDATE] Ошибка при вставке чата', chatId, error);
                            try {
                                container.appendChild(card);
                                debugLog('[SMART UPDATE] Добавлен новый чат', chatId, 'в конец списка (после ошибки)');
                            } catch (appendError) {
                                console.error('[SMART UPDATE] Критическая ошибка при добавлении чата', chatId, appendError);
                            }
                        }
                    });
                });
            }
            
            // Если порядок чатов изменился из-за сортировки, проверяем необходимость переупорядочивания
            // Но переупорядочивание делаем только если порядок изменился значительно
            // (более чем на 3 позиции для большинства чатов)
            if (chatsToAdd.length === 0 && chatsToRemove.length === 0 && filteredChats.length > 0) {
                const currentCards = Array.from(container.querySelectorAll('.chat-card'));
                if (currentCards.length === filteredChats.length) {
                    let reorderCount = 0;
                    for (let i = 0; i < Math.min(filteredChats.length, 10); i++) {
                        const expectedChatId = filteredChats[i].id;
                        const actualCard = currentCards[i];
                        if (!actualCard) break;
                        const actualChatId = Number(actualCard.getAttribute('data-chat-id'));
                        if (expectedChatId !== actualChatId) {
                            reorderCount++;
                        }
                    }
                    
                    // Если порядок изменился для более чем 30% проверенных чатов, перерисовываем
                    // Это редкий случай (например, при изменении сортировки), поэтому используем полную перерисовку
                    if (reorderCount > 3) {
                        renderChatsList();
                        return;
                    }
                }
            }
        }
        
        /**
         * Рендерит HTML для одного чата
         */
        function renderSingleChat(chat) {
            const isCompleted = chat.status === 'completed';
            const isBlocked = chat.status === 'blocked';
            const isInPool = !chat.assigned_manager_id && !isCompleted && !isBlocked;
            const isMyChat = chat.assigned_manager_id && chat.assigned_manager_name === currentUsername;
            const responseTimer = typeof chat.response_timer === 'number' ? chat.response_timer : (parseInt(chat.response_timer) || 0);
            const timerClass = getTimerClass(responseTimer);
            const timerText = formatTimer(responseTimer);
            const blinkClass = (!isCompleted && !isBlocked && responseTimer >= 20) ? 'blink-red' : '';
            const cardClass = `chat-card ${currentChatId === chat.id ? 'active' : ''} ${isInPool ? 'pool' : ''} ${blinkClass}`;
            const avitoOk = chat.avito_credentials_status === 'ok' || chat.has_avito_creds;
            const webhookOk = !!chat.webhook_registered;
            const safeClientName = highlightText(chat.client_name || '', searchQuery);
            const safeShopName = highlightText(chat.shop_name || '', searchQuery);
            const safeLastMessage = highlightText(chat.last_message || 'Нет сообщений', searchQuery);
            
                            return `
                    <div class="${cardClass}" onclick="selectChat(Number(${chat.id}))" data-chat-id="${chat.id}" data-shop-id="${chat.shop_id || ''}" data-manager-id="${chat.assigned_manager_id || ''}" data-response-timer="${responseTimer}">
                        <div class="chat-card-header" style="display: flex; align-items: start; gap: 0.5rem;">
                            <input type="checkbox" class="chat-select-checkbox" onclick="event.stopPropagation(); toggleChatSelection(${chat.id})" style="margin-top: 0.25rem; cursor: pointer;" data-chat-id="${chat.id}">
                        <div class="chat-card-header">
                        <div class="chat-card-title">
                            <div class="chat-client-name">${safeClientName}</div>
                            <div class="chat-shop-name">${safeShopName}</div>
                        </div>
                        <div class="chat-badges" style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                            ${isInPool ? '<span class="pool-badge">🌊 ПУЛ</span>' : ''}
                            ${chat.unread_count > 0 ? `<span class="unread-count">${chat.unread_count}</span>` : ''}
                            ${isAdmin ? (avitoOk ? '<span class="pool-badge" style="background: #10b981;">🔑 Avito</span>' : '<span class="pool-badge" style="background: #ef4444;">🔑 Нет ключей</span>') : ''}
                            ${isAdmin && webhookOk ? '<span class="pool-badge" style="background: #6b7280;">🔔 Webhook</span>' : ''}
                            ${isInPool ? `
                                <button class="quick-take-btn" onclick="event.stopPropagation(); takeChatFromPool(${chat.id})" title="Взять чат из пула">
                                    📥 Взять
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="chat-preview">${safeLastMessage}</div>
                    <div class="chat-footer">
                        ${isCompleted ? 
                            '<span class="priority-tag priority-completed">📦 ЗАВЕРШЕН</span>' :
                            isBlocked ?
                            '<span class="priority-tag" style="background: #ef4444; color: white;">🚫 ЗАБЛОКИРОВАН</span>' :
                            ''
                        }
                        ${!isCompleted && !isBlocked && responseTimer > 0 ? `<span class="response-time ${timerClass} ${responseTimer >= 20 ? 'blink' : ''}" style="${responseTimer >= 20 ? 'color: #ef4444; font-weight: 700;' : ''}" title="Время без ответа">⏱️ ${timerText}</span>` : ''}
                    </div>
                    ${isMyChat ? `
                        <div class="chat-card-actions">
                            <button class="quick-action-btn return" onclick="event.stopPropagation(); returnChatToPool(${chat.id})" title="Вернуть в пул">
                                📤 Вернуть
                        </button>
                            <button class="quick-action-btn" onclick="event.stopPropagation(); markAsCompleted(${chat.id})" title="Завершить чат">
                                ✅ Завершить
                        </button>
                            <button class="quick-action-btn" onclick="event.stopPropagation(); blockChat(${chat.id})" title="Заблокировать чат">
                                🚫 Заблокировать
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // Выбор чата
        // ВЕРСИЯ: 2025-01-15 - Удалена проверка chatId === allChats.length
        function selectChat(chatId) {
            // Преобразуем в число, если это строка
            chatId = Number(chatId);
            
            // Проверяем, что передан правильный ID
            if (!chatId || isNaN(chatId) || chatId <= 0) {
                console.error('[SELECT CHAT] ❌ Неправильный ID чата:', chatId, 'тип:', typeof chatId);
                return;
            }
            
            currentChatId = chatId;
            const chat = allChats.find(c => Number(c.id) === chatId);
            if (!chat) {
                // Чат не найден - возможно, он еще не загружен или был удален
                // Пытаемся перезагрузить список чатов и повторить попытку
                debugLog('[SELECT CHAT] Чат не найден, перезагружаем список чатов. ID:', chatId, 'allChats.length:', allChats.length);
                if (typeof window.loadChats === 'function') {
                    window.loadChats(false, true).then(() => {
                        // После загрузки пытаемся снова найти чат
                        const retryChat = allChats.find(c => Number(c.id) === chatId);
                        if (retryChat) {
                            selectChat(chatId); // Рекурсивный вызов после загрузки
                        } else {
                            console.error('[SELECT CHAT] ❌ Чат не найден после перезагрузки. ID:', chatId);
                            showNotification('Чат не найден', 'error');
                        }
                    }).catch(() => {
                        console.error('[SELECT CHAT] ❌ Ошибка при перезагрузке чатов');
                        showNotification('Чат не найден', 'error');
                    });
                } else {
                    console.error('[SELECT CHAT] ❌ Чат не найден в allChats. ID:', chatId, 'allChats.length:', allChats.length);
                    showNotification('Чат не найден', 'error');
                }
                return;
            }
            const params = new URLSearchParams(window.location.search);
            params.set('chat_id', chatId);
            window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
            const isCompleted = chat && chat.status === 'completed';
            currentChatHasAvito = (chat.avito_credentials_status === 'ok') || !!chat.has_avito_creds;
            messagesState[chatId] = {
                offset: 0,
                limit: MESSAGE_PAGE,
                messages: [],
                has_more: true,
                loading: false
            };
            
            // Обновляем выделение активного чата умно, без полной перерисовки
            updateChatsListSmart();
            
            const emptyChat = document.getElementById('empty-chat');
            const chatContent = document.getElementById('chat-content');
            if (emptyChat) emptyChat.style.display = 'none';
            if (chatContent) {
                chatContent.style.display = 'flex';
                chatContent.style.width = '100%';
                chatContent.style.height = '100%';
            }
            
            document.getElementById('chat-client-name').textContent = chat.client_name || '';
            
            // Формируем детали чата - скрываем техническую информацию для менеджеров
            let headerDetails = `
                <span>📞 ${escapeHtml(chat.client_phone || '')}</span>
                <span>•</span>
                <span>🏪 ${escapeHtml(chat.shop_name || '')}</span>
            `;
            
            // Показываем Avito ключи и webhooks только для админов
            if (isAdmin) {
                headerDetails += `
                <span>•</span>
                <span style="color: ${currentChatHasAvito ? '#10b981' : '#ef4444'}; font-weight: 700;">
                    ${currentChatHasAvito ? 'Avito ключи: OK' : 'Ключи не заданы'}
                </span>
                <span>•</span>
                <span style="color: ${chat.webhook_registered ? '#10b981' : '#f59e0b'};">
                    ${chat.webhook_registered ? 'Webhook: OK' : 'Webhook: нет'}
                </span>
            `;
            }
            
            document.getElementById('chat-header-details').innerHTML = headerDetails;

            const actionsDiv = document.getElementById('chat-header-actions');
            if (actionsDiv) {
                actionsDiv.innerHTML = `
                    <button class="btn-outline" onclick="addToBlacklist()" title="Добавить в черный список" style="padding: 0.5rem 0.75rem; font-size: 0.875rem;">
                        <span>🚫</span> Blacklist
                    </button>
                `;
            }
            if (!actionsDiv) {
                console.error('[SELECT CHAT] chat-header-actions не найден!');
                return;
            }
            if (isCompleted) {
                actionsDiv.innerHTML = `
                    <button class="header-action-btn" onclick="restoreChat(${chatId})" style="background: var(--success); color: white; border-color: transparent;">
                        🔄 Восстановить
                    </button>
                `;
            } else if (chat.status === 'blocked') {
                actionsDiv.innerHTML = `
                    <button class="header-action-btn" onclick="unblockChat(${chatId})" style="background: var(--success); color: white; border-color: transparent;">
                        🔓 Разблокировать
                    </button>
                `;
            } else {
                const isInPool = !chat.assigned_manager_id;
                const isMyChat = chat.assigned_manager_id && 
                    (chat.assigned_manager_id === currentUserId || 
                     chat.assigned_manager_name === currentUsername ||
                     (chat.assigned_manager_name && currentUsername && 
                      chat.assigned_manager_name.includes(currentUsername)));
                actionsDiv.innerHTML = `
                    ${isInPool ? `
                        <button class="header-action-btn" onclick="takeChatFromPool(${chatId})" style="background: linear-gradient(135deg, #10b981, #059669); color: white; border-color: transparent;">
                            📥 Взять из пула
                        </button>
                    ` : isMyChat ? `
                        <button class="header-action-btn" onclick="returnChatToPool(${chatId})" style="background: var(--warning); color: white; border-color: transparent;">
                            📤 Вернуть в пул
                        </button>
                    ` : ''}
                    <button class="header-action-btn" onclick="markAsDelivery()">🚚 В доставку</button>
                    <button class="header-action-btn" onclick="markAsCompleted()">✅ Завершить</button>
                    <button class="header-action-btn" onclick="blockChat(${chatId})" style="background: #ef4444; color: white; border-color: transparent;">🚫 Заблокировать</button>
                    <button class="header-action-btn" onclick="addToBlacklist()" style="background: #7c3aed; color: white; border-color: transparent;">🚫 Blacklist</button>
                `;
            }

            if (!isCompleted) {
                document.getElementById('message-text').focus();
            }

            updateSendAvailability();
            const container = document.getElementById('messages-container');
            if (container) {
                container.addEventListener('scroll', () => toggleScrollBottomButton(container));
            }
            loadChatMessages(chatId);
            // Загружаем объявление в правую панель
            loadListingToSidebar(chatId);
            startMessagesAutoRefresh();
        }

        function setMessagesLoadingState(isLoading) {
            messagesLoading = isLoading;
            const quickActionButtons = document.querySelectorAll('.quick-action');
            quickActionButtons.forEach(btn => btn.classList.toggle('is-disabled', isLoading));
            updateSendAvailability();
        }

        // Загрузка сообщений (с пагинацией)
        async function loadChatMessages(chatId, mode = 'replace') {
            if (!chatId) return;
            const state = messagesState[chatId] || {offset: 0, limit: MESSAGE_PAGE, messages: [], has_more: true, loading: false};
            if (state.loading) return;
            state.loading = true;
            messagesState[chatId] = state;
            const shouldDisableUi = mode !== 'refresh';
            if (shouldDisableUi) {
                setMessagesLoadingState(true);
            }

            const fetchOffset = mode === 'prepend' ? state.offset : 0;
            const params = new URLSearchParams({
                limit: state.limit,
                offset: fetchOffset
            });
            const prevIds = new Set((state.messages || []).map(m => m.id || `${m.timestamp}-${m.message_text}`));
            // Синхронизация с Avito при первой загрузке или обновлении, если есть ключи
            const chat = allChats.find(c => c.id === chatId);
            if (chat && (chat.has_avito_creds || chat.avito_credentials_status === 'ok')) {
                // Синхронизируем при первой загрузке (replace) или при refresh
                if (mode === 'replace') {
                    params.set('sync', 'true');
                } else if (mode === 'refresh') {
                    // При refresh синхронизируем чаще (каждые 5 секунд вместо 10) для более быстрого получения новых сообщений
                    const now = Date.now();
                    const lastSync = lastSyncTime.get(chatId) || 0;
                    const timeSinceLastSync = (now - lastSync) / 1000; // в секундах
                    
                    if (timeSinceLastSync >= 5) { // Минимум 5 секунд между синхронизациями (было 10)
                        params.set('sync', 'true');
                        lastSyncTime.set(chatId, now);
                    } else {
                        // Не синхронизируем, просто загружаем из БД
                        params.set('sync', 'false');
                    }
                }
            } else {
            }

            const container = document.getElementById('messages-container');
            const previousHeight = container ? container.scrollHeight : 0;
            const previousScrollTop = container ? container.scrollTop : 0;

            if (state.messages.length === 0 && mode === 'replace' && container) {
                // Оптимизировано: не показываем loading, просто оставляем пустым
                container.innerHTML = '';
            } else if (mode === 'prepend') {
                const btn = document.getElementById('load-more-btn');
                if (btn) btn.disabled = true;
            }

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
                
                // Правильный парсинг: проверяем массив напрямую или объект с ключом messages
                let messages = [];
                if (Array.isArray(payload)) {
                    messages = payload;
                } else if (payload && typeof payload === 'object') {
                    if (Array.isArray(payload.messages)) {
                        messages = payload.messages;
                    } else if (Array.isArray(payload.items)) {
                        messages = payload.items;
                    } else if (payload.messages && typeof payload.messages === 'object') {
                        // Если messages - объект, пытаемся извлечь массив
                        messages = [];
                        console.warn('[LOAD MESSAGES] payload.messages не массив:', payload.messages);
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
                renderMessages(
                    chatId,
                    mode === 'prepend' ? previousHeight : null,
                    mode === 'refresh' ? previousScrollTop : null,
                    mode
                );
                if (mode === 'refresh') {
                    const container = document.getElementById('messages-container');
                    if (container) {
                        const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
                        const newlyLoaded = messages.filter(msg => {
                            const key = msg.id || `${msg.timestamp}-${msg.message_text}`;
                            return !prevIds.has(key);
                        });
                        if (distanceFromBottom > 200 && newlyLoaded.length > 0) {
                            unreadFromRefresh += newlyLoaded.length;
                            updateUnreadIndicator(container, state.messages);
                        }
                    }
                }
            } catch (error) {
                console.error('Ошибка загрузки сообщений:', error);
                showNotification('Не удалось загрузить сообщения', 'error');
            } finally {
                state.loading = false;
                messagesState[chatId] = state;
                const btn = document.getElementById('load-more-btn');
                if (btn) btn.disabled = false;
                if (shouldDisableUi) {
                    setMessagesLoadingState(false);
                }
            }
        }

        function renderMessages(chatId, previousHeight = null, previousScrollTop = null, mode = 'replace') {
            const state = messagesState[chatId] || {messages: [], has_more: false};
            const container = document.getElementById('messages-container');
            if (!container) {
                console.error('[RENDER MESSAGES] Контейнер #messages-container не найден!');
                return;
            }
            
            // Убеждаемся, что контейнер видим и правильно позиционирован
            const chatContent = document.getElementById('chat-content');
            if (chatContent && chatContent.style.display === 'none') {
                console.warn('[RENDER MESSAGES] chat-content скрыт, пытаемся показать');
                chatContent.style.display = 'flex';
            }
            
            // Убеждаемся, что контейнер имеет правильные размеры
            if (container.offsetWidth === 0 || container.offsetHeight === 0) {
                console.warn('[RENDER MESSAGES] Контейнер имеет нулевые размеры!', {
                    width: container.offsetWidth,
                    height: container.offsetHeight,
                    display: window.getComputedStyle(container).display
                });
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
                <button id="load-more-btn" class="load-more-btn" ${state.loading ? 'disabled' : ''} onclick="loadOlderMessages()">
                    ⬆️ Загрузить предыдущие сообщения
                </button>
            ` : '';

            const messagesHtml = state.messages.map(messageTemplate).join('');
            container.innerHTML = `${loadMoreBtn}${messagesHtml}`;
            
            // Принудительно обновляем layout после вставки сообщений
            container.offsetHeight; // Trigger reflow

            if (mode === 'refresh' && previousScrollTop !== null) {
                container.scrollTop = previousScrollTop;
            } else if (previousHeight !== null) {
                const newHeight = container.scrollHeight;
                container.scrollTop = newHeight - previousHeight;
            } else {
                container.scrollTop = container.scrollHeight;
            }

            toggleScrollBottomButton(container);
            updateUnreadIndicator(container, state.messages);
        }

        function messageTemplate(msg) {
                    const messageClass = msg.message_type === 'incoming' ? 'incoming' : 'outgoing';
                    // Форматирование времени сообщения
                    let time = 'Неизвестно';
                    try {
                        const msgDate = new Date(msg.timestamp);
                        if (!isNaN(msgDate.getTime())) {
                            time = msgDate.toLocaleString('ru-RU', {
                        hour: '2-digit',
                        minute: '2-digit',
                        day: '2-digit',
                                month: '2-digit',
                                year: 'numeric'
                    });
                        }
                    } catch (e) {
                        console.error('[RENDER MESSAGES] Ошибка форматирования времени:', e, 'timestamp:', msg.timestamp);
                    }
            // Для исходящих сообщений показываем имя отправителя, заменяя "Система" на username текущего пользователя
            let displayManager = msg.manager_name || currentUsername || 'Система';
            if (messageClass === 'outgoing' && displayManager === 'Система' && currentUsername) {
                displayManager = currentUsername;
            }
            const safeManager = escapeHtml(displayManager);
            const safeText = escapeHtml(msg.message_text || '');
            // Показываем имя отправителя для всех исходящих сообщений
            const managerName = (messageClass === 'outgoing') ? `<div class="message-author">${safeManager}</div>` : '';

                    return `
                        <div class="message-row ${messageClass}">
                            ${managerName}
                            <div class="message-wrapper">
                        <div class="message-bubble">${safeText}</div>
                                <div class="message-time">${time}</div>
                            </div>
                        </div>
                    `;
        }

        async function loadOlderMessages() {
            if (!currentChatId) return;
            const container = document.getElementById('messages-container');
            const previousHeight = container ? container.scrollHeight : null;
            await loadChatMessages(currentChatId, 'prepend');
            if (previousHeight !== null) {
                // Мгновенная прокрутка без requestAnimationFrame
                    container.scrollTop = container.scrollHeight - previousHeight;
            }
        }

        function scrollMessagesBottom() {
            const container = document.getElementById('messages-container');
            if (container) {
                container.scrollTo({top: container.scrollHeight, behavior: 'smooth'});
                unreadFromRefresh = 0;
                updateUnreadIndicator(container, messagesState[currentChatId]?.messages || []);
            }
        }

        function toggleScrollBottomButton(container) {
            const btn = document.getElementById('scroll-bottom-btn');
            if (!container || !btn) return;
            const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
            btn.classList.toggle('show', distanceFromBottom > 200);
        }

        function updateUnreadIndicator(container, messages) {
            const btn = document.getElementById('scroll-bottom-btn');
            if (!btn) return;
            const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
            if (distanceFromBottom <= 200) {
                unreadFromRefresh = 0;
            }
            const badge = btn.querySelector('.unread-indicator');
            if (!badge && unreadFromRefresh > 0) {
                btn.insertAdjacentHTML('beforeend', `<span class="unread-indicator">${unreadFromRefresh}</span>`);
            } else if (badge) {
                badge.textContent = unreadFromRefresh;
                badge.style.display = unreadFromRefresh > 0 ? 'flex' : 'none';
            }
        }

        // Отправка сообщения
        async function sendMessage() {
            if (!currentChatId) return;
            if (messagesLoading) return;
            if (!currentChatHasAvito) {
                showNotification('Для этого магазина не заданы OAuth ключи Avito', 'error');
                return;
            }

            const messageInput = document.getElementById('message-text');
            let messageText = messageInput.value.trim();

            if (!messageText) {
                showNotification('Введите текст сообщения', 'error');
                return;
            }

            const quickReply = await getQuickReplyByText(messageText);
            if (quickReply) {
                messageText = quickReply;
            }

            const messageTextToShow = messageText;
            messageInput.value = '';
            messageInput.style.height = 'auto';

            const container = document.getElementById('messages-container');
            if (container.querySelector('.empty-chat')) {
                container.innerHTML = '';
            }
            
            const now = new Date();
            // Форматирование времени для отправленного сообщения
            const timeStr = now.toLocaleString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit',
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
            
            const tempId = 'temp-' + Date.now();
            // Показываем имя отправителя для временного сообщения
            const senderName = currentUsername || 'Магазин';
            const managerNameHtml = `<div class="message-author">${escapeHtml(senderName)}</div>`;
            container.insertAdjacentHTML('beforeend', `
                <div class="message-row outgoing" id="${tempId}">
                    ${managerNameHtml}
                    <div class="message-wrapper">
                        <div class="message-bubble">${escapeHtml(messageTextToShow)}</div>
                        <div class="message-time">${timeStr}</div>
                    </div>
                </div>
            `);
            container.scrollTop = container.scrollHeight;

            const sendButton = document.querySelector('.send-button');
            if (sendButton) sendButton.disabled = true;

            fetch(`/api/chats/${currentChatId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({message: messageText})
            }).then(response => {
                if (response.ok) return response.json();
                return response.json().catch(() => ({})).then(err => {
                    const msg = err.error || 'Ошибка отправки';
                    throw new Error(msg);
                });
            }).then(data => {
                // Показываем уведомление только если есть предупреждение
                if (data.warning) {
                    showNotification(`⚠️ ${data.warning}`, 'warning');
                }
                
                // Оптимизация: обновляем только сообщения, список чатов обновим в фоне
                loadChatMessages(currentChatId).then(() => {
                    const temp = document.getElementById(tempId);
                    if (temp) temp.remove();
                });
                // Обновляем список чатов в фоне без блокировки UI
                loadChats(false, true).catch(() => {});
            }).catch(error => {
                console.error('Ошибка отправки сообщения:', error);
                showNotification(`❌ ${error.message || 'Ошибка отправки'}`, 'error');
                messageInput.value = messageTextToShow;
                const temp = document.getElementById(tempId);
                if (temp) temp.remove();
            }).finally(() => {
                if (sendButton) sendButton.disabled = false;
            });
        }

        // Загрузка и отправка изображения
        async function handleImageUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            // Проверяем тип файла
            if (!file.type.startsWith('image/')) {
                showNotification('❌ Выберите файл изображения', 'error');
                return;
            }

            // Проверяем размер (24 МБ максимум)
            const maxSize = 24 * 1024 * 1024; // 24 МБ
            if (file.size > maxSize) {
                showNotification('❌ Файл слишком большой (максимум 24 МБ)', 'error');
                return;
            }

            if (!currentChatId) {
                showNotification('❌ Выберите чат', 'error');
                return;
            }

            showNotification('📤 Загрузка изображения...', 'info');

            try {
                // Загружаем изображение
                const formData = new FormData();
                formData.append('file', file);

                const uploadResponse = await fetch('/api/upload/image', {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (!uploadResponse.ok) {
                    const error = await uploadResponse.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка загрузки изображения');
                }

                const uploadData = await uploadResponse.json();
                const imageId = uploadData.image_id;

                if (!imageId) {
                    throw new Error('Не удалось получить image_id');
                }

                // Отправляем изображение в чат
                const sendResponse = await fetch(`/api/chats/${currentChatId}/messages/image`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({image_id: imageId})
                });

                if (!sendResponse.ok) {
                    const error = await sendResponse.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка отправки изображения');
                }

                // Обновляем сообщения
                await loadChatMessages(currentChatId);
                loadChats(false, true).catch(() => {});

            } catch (error) {
                console.error('Ошибка отправки изображения:', error);
                showNotification(`❌ ${error.message || 'Ошибка отправки изображения'}`, 'error');
            } finally {
                // Очищаем input
                event.target.value = '';
            }
        }

        // Обработка загрузки голосовых сообщений и аудио
        async function handleVoiceUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            // Проверяем тип файла
            const isAudio = file.type.startsWith('audio/');
            const isVideo = file.type === 'video/mp4'; // Avito поддерживает opus в mp4 контейнере
            
            if (!isAudio && !isVideo) {
                showNotification('❌ Выберите аудио файл или видео (mp4)', 'error');
                return;
            }

            // Проверяем размер (для аудио обычно меньше, но проверим)
            const maxSize = 50 * 1024 * 1024; // 50 МБ для аудио/видео
            if (file.size > maxSize) {
                showNotification('❌ Файл слишком большой (максимум 50 МБ)', 'error');
                return;
            }

            if (!currentChatId) {
                showNotification('❌ Выберите чат', 'error');
                return;
            }

            showNotification('📤 Загрузка аудио файла...', 'info');

            try {
                // Загружаем файл
                const formData = new FormData();
                formData.append('file', file);
                formData.append('file_type', isAudio ? 'audio' : 'video');

                const uploadResponse = await fetch('/api/upload/media', {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (!uploadResponse.ok) {
                    const error = await uploadResponse.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка загрузки аудио файла');
                }

                const uploadData = await uploadResponse.json();
                const attachmentId = uploadData.attachment_id || uploadData.id;

                if (!attachmentId) {
                    throw new Error('Не удалось получить attachment_id');
                }

                // Отправляем файл в чат как вложение
                const messageText = document.getElementById('message-text').value || '';
                const sendResponse = await fetch(`/api/chats/${currentChatId}/messages`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        message: messageText,
                        attachments: [{'id': attachmentId}]
                    })
                });

                if (!sendResponse.ok) {
                    const error = await sendResponse.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка отправки аудио файла');
                }

                // Очищаем поле сообщения
                document.getElementById('message-text').value = '';

                // Обновляем сообщения
                await loadChatMessages(currentChatId);
                loadChats(false, true).catch(() => {});

            } catch (error) {
                console.error('Ошибка отправки аудио файла:', error);
                showNotification(`❌ ${error.message || 'Ошибка отправки аудио файла'}`, 'error');
            } finally {
                // Очищаем input
                event.target.value = '';
            }
        }

        // Обработка загрузки других медиа файлов
        async function handleMediaUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            // Проверяем размер
            const maxSize = 50 * 1024 * 1024; // 50 МБ
            if (file.size > maxSize) {
                showNotification('❌ Файл слишком большой (максимум 50 МБ)', 'error');
                return;
            }

            if (!currentChatId) {
                showNotification('❌ Выберите чат', 'error');
                return;
            }

            showNotification('📤 Загрузка файла...', 'info');

            try {
                // Определяем тип файла
                let fileType = 'document';
                if (file.type.startsWith('video/')) {
                    fileType = 'video';
                } else if (file.type.startsWith('audio/')) {
                    fileType = 'audio';
                } else if (file.type.startsWith('image/')) {
                    fileType = 'photo';
                }

                // Загружаем файл
                const formData = new FormData();
                formData.append('file', file);
                formData.append('file_type', fileType);

                const uploadResponse = await fetch('/api/upload/media', {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (!uploadResponse.ok) {
                    const error = await uploadResponse.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка загрузки файла');
                }

                const uploadData = await uploadResponse.json();
                const attachmentId = uploadData.attachment_id || uploadData.id;

                if (!attachmentId) {
                    throw new Error('Не удалось получить attachment_id');
                }

                // Отправляем файл в чат как вложение
                const messageText = document.getElementById('message-text').value || '';
                const sendResponse = await fetch(`/api/chats/${currentChatId}/messages`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        message: messageText,
                        attachments: [{'id': attachmentId}]
                    })
                });

                if (!sendResponse.ok) {
                    const error = await sendResponse.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка отправки файла');
                }

                // Очищаем поле сообщения
                document.getElementById('message-text').value = '';

                // Обновляем сообщения
                await loadChatMessages(currentChatId);
                loadChats(false, true).catch(() => {});

            } catch (error) {
                console.error('Ошибка отправки файла:', error);
                showNotification(`❌ ${error.message || 'Ошибка отправки файла'}`, 'error');
            } finally {
                // Очищаем input
                event.target.value = '';
            }
        }

        // Добавление в blacklist
        async function addToBlacklist() {
            if (!currentChatId) {
                showNotification('❌ Выберите чат', 'error');
                return;
            }

            try {
                // Получаем информацию о чате
                const chatResponse = await fetch(`/api/chats/${currentChatId}`, {
                    credentials: 'include'
                });

                if (!chatResponse.ok) {
                    throw new Error('Не удалось получить информацию о чате');
                }

                const chatData = await chatResponse.json();
                const chat = chatData.chat;

                if (!chat) {
                    throw new Error('Чат не найден');
                }

                // Запрашиваем причину
                const reason = prompt('Введите причину добавления в blacklist (необязательно):');
                if (reason === null) {
                    return; // Пользователь отменил
                }

                showNotification('📤 Добавление в blacklist...', 'info');

                // Получаем user_id магазина из чата
                const shopResponse = await fetch(`/api/chats/${currentChatId}`, {
                    credentials: 'include'
                });
                const shopData = await shopResponse.json();
                const shopUserId = shopData.chat?.shop_user_id;

                if (!shopUserId) {
                    throw new Error('Не удалось получить user_id магазина');
                }

                // Добавляем в blacklist
                const blacklistData = {
                    user_id: shopUserId,
                    phone: chat.client_phone || null,
                    user_id_to_block: chat.client_user_id || null,
                    reason: reason || null
                };

                const response = await fetch('/api/blacklist', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    credentials: 'include',
                    body: JSON.stringify(blacklistData)
                });

                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка добавления в blacklist');
                }

                showNotification('✅ Пользователь добавлен в blacklist', 'success');
            } catch (error) {
                console.error('Ошибка добавления в blacklist:', error);
                showNotification(`❌ ${error.message || 'Ошибка добавления в blacklist'}`, 'error');
            }
        }

        // Быстрые ответы
        async function getQuickReplyByText(text) {
            try {
                const now = Date.now();
                if (!quickRepliesCache || (now - quickRepliesCacheTime) > CACHE_DURATION) {
                    const response = await fetch('/api/quick-replies', {
                        credentials: 'include'
                    });
                    quickRepliesCache = await response.json();
                    quickRepliesCacheTime = now;
                }

                const normalizedText = text.toLowerCase().trim();
                const reply = quickRepliesCache.find(r => {
                    const shortcutRaw = r.shortcut || '';
                    const shortcut = shortcutRaw.toLowerCase().replace(/^\//, '');
                    return shortcut === normalizedText || shortcutRaw.toLowerCase() === normalizedText;
                });
                return reply ? reply.message : null;
            } catch (error) {
                return null;
            }
        }

        async function showQuickRepliesMenu() {
            const menu = document.getElementById('quick-replies-menu');
            menu.classList.toggle('active');

            if (menu.classList.contains('active')) {
                try {
                    const now = Date.now();
                    if (!quickRepliesCache || (now - quickRepliesCacheTime) > CACHE_DURATION) {
                        const response = await fetch('/api/quick-replies', {
                            credentials: 'include'
                        });
                        quickRepliesCache = await response.json();
                        quickRepliesCacheTime = now;
                    }

                    const replies = quickRepliesCache || [];
                    document.getElementById('quick-replies-total').textContent = replies.length;
                    document.getElementById('quick-replies-count').textContent = replies.length > 0 ? `(${replies.length})` : '';

                    if (replies.length === 0) {
                        document.getElementById('quick-replies-list').innerHTML = `
                            <div class="quick-replies-empty">
                                <div class="quick-replies-empty-icon">⚡</div>
                                <div class="quick-replies-empty-title">Нет быстрых ответов</div>
                                <div style="font-size: 0.875rem; opacity: 0.8;">Создайте быстрые ответы для ускорения работы</div>
                                <a href="/quick-replies" class="quick-replies-empty-link">➕ Создать первый</a>
                            </div>
                        `;
                    } else {
                        document.getElementById('quick-replies-list').innerHTML = replies.map(reply => {
                            const shortcut = reply.shortcut.replace(/^\//, '');
                            const previewRaw = reply.message || '';
                            const preview = previewRaw.length > 80 ? previewRaw.substring(0, 80) + '...' : previewRaw;
                            const safePreview = escapeHtml(preview);
                            const safeMessageAttr = reply.message.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                            const charCount = reply.message.length;
                            return `
                                <div class="quick-reply-item" onclick="useQuickReply('${safeMessageAttr}')">
                                    <span class="quick-reply-shortcut">${shortcut}</span>
                                    <div class="quick-reply-content">
                                        <div class="quick-reply-text">${safePreview}</div>
                                        <div class="quick-reply-meta">
                                            <span>📝 ${charCount} символов</span>
                                        </div>
                                    </div>
                                    <button class="quick-reply-send" onclick="event.stopPropagation(); sendQuickReply('${safeMessageAttr}').catch(err => console.error('Ошибка отправки быстрого ответа:', err))">
                                        <span>📤</span>
                                        <span>Отправить</span>
                                    </button>
                                </div>
                            `;
                        }).join('');
                    }
                } catch (error) {
                    console.error('Ошибка загрузки быстрых ответов:', error);
                }
            }
        }


        function useQuickReply(message) {
            document.getElementById('message-text').value = message;
            document.getElementById('quick-replies-menu').classList.remove('active');
        }

        async function sendQuickReply(message) {
            document.getElementById('message-text').value = message;
            document.getElementById('quick-replies-menu').classList.remove('active');
            await sendMessage();
        }

        // Управление быстрыми ответами через модальное окно
        async function showQuickRepliesManagementModal() {
            const modal = document.getElementById('quick-replies-management-modal');
            modal.style.display = 'flex';
            await loadQuickRepliesManagementList();
        }

        function closeQuickRepliesManagementModal() {
            const modal = document.getElementById('quick-replies-management-modal');
            modal.style.display = 'none';
        }

        async function loadQuickRepliesManagementList() {
            try {
                const response = await fetch('/api/quick-replies/all', {
                    credentials: 'include'
                });
                const replies = await response.json();
                const container = document.getElementById('quick-replies-management-list');

                if (replies.length === 0) {
                    container.innerHTML = `
                        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
                            <div style="font-size: 3rem; margin-bottom: 1rem;">⚡</div>
                            <div style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.5rem;">Нет быстрых ответов</div>
                            <div style="font-size: 0.875rem; opacity: 0.8;">Создайте первый быстрый ответ для ускорения работы</div>
                        </div>
                    `;
                    return;
                }

                container.innerHTML = replies.map(reply => {
                    const shortcut = reply.shortcut?.replace(/^\//, '') || '';
                    const preview = (reply.message || '').length > 100 
                        ? (reply.message || '').substring(0, 100) + '...' 
                        : (reply.message || '');
                    const isActive = reply.is_active !== 0;
                    return `
                        <div style="background: var(--bg-secondary); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem;">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                                <div style="flex: 1;">
                                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                        <span style="font-weight: 700; color: var(--primary);">${shortcut}</span>
                                        ${!isActive ? '<span style="font-size: 0.75rem; padding: 0.25rem 0.5rem; background: rgba(239, 68, 68, 0.1); color: #ef4444; border-radius: 4px;">Неактивен</span>' : ''}
                                    </div>
                                    <div style="color: var(--text-muted); font-size: 0.875rem; line-height: 1.5;">${escapeHtml(preview)}</div>
                                </div>
                            </div>
                            <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                                <button onclick="editQuickReply(${reply.id})" style="padding: 0.5rem 1rem; background: var(--primary); color: white; border: none; border-radius: var(--radius); cursor: pointer; font-weight: 600; font-size: 0.875rem;">✏️ Редактировать</button>
                                <button onclick="deleteQuickReply(${reply.id})" style="padding: 0.5rem 1rem; background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: var(--radius); cursor: pointer; font-weight: 600; font-size: 0.875rem;">🗑️ Удалить</button>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (error) {
                console.error('Ошибка загрузки быстрых ответов:', error);
                showNotification('❌ Ошибка загрузки быстрых ответов', 'error');
            }
        }

        function showQuickReplyEditModal(replyId = null) {
            const modal = document.getElementById('quick-reply-edit-modal');
            const title = document.getElementById('quick-reply-edit-title');
            const form = document.getElementById('quick-reply-edit-form');
            const idInput = document.getElementById('quick-reply-edit-id');
            const shortcutInput = document.getElementById('quick-reply-edit-shortcut');
            const messageInput = document.getElementById('quick-reply-edit-message');

            if (replyId) {
                // Редактирование существующего
                title.textContent = 'Редактировать быстрый ответ';
                idInput.value = replyId;
                
                // Загружаем данные
                fetch('/api/quick-replies/all', { credentials: 'include' })
                    .then(res => res.json())
                    .then(replies => {
                        const reply = replies.find(r => r.id === replyId);
                        if (reply) {
                            shortcutInput.value = reply.shortcut?.replace(/^\//, '') || '';
                            messageInput.value = reply.message || '';
                        }
                    })
                    .catch(err => {
                        console.error('Ошибка загрузки быстрого ответа:', err);
                        showNotification('❌ Ошибка загрузки данных', 'error');
                    });
            } else {
                // Добавление нового
                title.textContent = 'Добавить быстрый ответ';
                idInput.value = '';
                shortcutInput.value = '';
                messageInput.value = '';
            }

            modal.style.display = 'flex';
        }

        function closeQuickReplyEditModal() {
            const modal = document.getElementById('quick-reply-edit-modal');
            modal.style.display = 'none';
        }

        async function saveQuickReply(event) {
            event.preventDefault();
            
            const idInput = document.getElementById('quick-reply-edit-id');
            const shortcutInput = document.getElementById('quick-reply-edit-shortcut');
            const messageInput = document.getElementById('quick-reply-edit-message');

            const replyId = idInput.value;
            let shortcut = shortcutInput.value.trim();
            const message = messageInput.value.trim();

            if (!shortcut || !message) {
                showNotification('❌ Заполните все поля', 'error');
                return;
            }

            // Убираем "/" если он есть в начале
            if (shortcut.startsWith('/')) {
                shortcut = shortcut.substring(1);
            }

            try {
                let response;
                if (replyId) {
                    // Обновление
                    response = await fetch(`/api/quick-replies/${replyId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            shortcut: shortcut,
                            message: message
                        })
                    });
                } else {
                    // Создание
                    response = await fetch('/api/quick-replies', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'include',
                        body: JSON.stringify({
                            shortcut: shortcut,
                            message: message
                        })
                    });
                }

                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка сохранения');
                }

                showNotification(replyId ? '✅ Быстрый ответ обновлен' : '✅ Быстрый ответ создан', 'success');
                closeQuickReplyEditModal();
                
                // Обновляем список в модальном окне управления
                await loadQuickRepliesManagementList();
                
                // Обновляем кэш и меню быстрых ответов
                quickRepliesCache = null;
                quickRepliesCacheTime = 0;
                if (document.getElementById('quick-replies-menu').classList.contains('active')) {
                    showQuickRepliesMenu();
                }
            } catch (error) {
                console.error('Ошибка сохранения быстрого ответа:', error);
                showNotification(`❌ ${error.message || 'Ошибка сохранения'}`, 'error');
            }
        }

        async function deleteQuickReply(replyId) {
            if (!confirm('Вы уверены, что хотите удалить этот быстрый ответ?')) {
                return;
            }

            try {
                const response = await fetch(`/api/quick-replies/${replyId}`, {
                    method: 'DELETE',
                    credentials: 'include'
                });

                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.error || 'Ошибка удаления');
                }

                showNotification('✅ Быстрый ответ удален', 'success');
                
                // Обновляем список в модальном окне управления
                await loadQuickRepliesManagementList();
                
                // Обновляем кэш и меню быстрых ответов
                quickRepliesCache = null;
                quickRepliesCacheTime = 0;
                if (document.getElementById('quick-replies-menu').classList.contains('active')) {
                    showQuickRepliesMenu();
                }
            } catch (error) {
                console.error('Ошибка удаления быстрого ответа:', error);
                showNotification(`❌ ${error.message || 'Ошибка удаления'}`, 'error');
            }
        }

        function editQuickReply(replyId) {
            showQuickReplyEditModal(replyId);
        }

        // Закрытие модальных окон при клике на backdrop
        document.addEventListener('click', (e) => {
            const managementModal = document.getElementById('quick-replies-management-modal');
            const editModal = document.getElementById('quick-reply-edit-modal');
            
            if (e.target === managementModal) {
                closeQuickRepliesManagementModal();
            }
            if (e.target === editModal) {
                closeQuickReplyEditModal();
            }
        });

        // Действия с чатом
        async function apiAction(url, options, successMessage, onSuccess, onError) {
            try {
                // Убеждаемся, что credentials включены по умолчанию
                if (!options.credentials) {
                    options.credentials = 'include';
                }
                const response = await fetch(url, options);
                if (!response.ok) {
                    const errJson = await response.json().catch(() => ({}));
                    const msg = errJson.error || `HTTP ${response.status}`;
                    throw new Error(msg);
                }
                if (onSuccess) await onSuccess();
                if (successMessage) showNotification(successMessage, 'success');
            } catch (error) {
                if (onError) {
                    onError(error);
                } else {
                showNotification(`❌ ${error.message || 'Ошибка'}`, 'error');
                }
            }
        }

        function markAsDelivery() {
            if (!currentChatId) return;
            apiAction('/api/deliveries', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({chat_id: currentChatId, status: 'processing'})
            }, '✅ Чат переведен в доставку', () => loadChats());
        }

        function markAsCompleted(chatId) {
            // Поддерживаем вызов как с параметром, так и без (для текущего чата)
            const targetChatId = chatId || currentChatId;
            if (!targetChatId) return;
            apiAction(`/api/chats/${targetChatId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({status: 'completed'})
            }, '✅ Чат завершен', async () => {
                await loadChats();
                if (currentSort === 'completed') {
                    applySort('all');
                }
                // Если чат был открыт, закрываем его
                if (targetChatId === currentChatId) {
                    currentChatId = null;
                    document.getElementById('empty-chat').style.display = 'flex';
                    document.getElementById('chat-content').style.display = 'none';
                }
            });
        }

        // Очередь для массового назначения чатов (оптимизация производительности)
        let batchTakeQueue = [];
        let batchTakeTimer = null;
        let batchTakeInProgress = false; // Блокировка для предотвращения race condition
        const BATCH_TAKE_DELAY = 300; // 300мс задержка для группировки запросов
        const BATCH_TAKE_SIZE = 50; // Максимум чатов в одном батче
        
        // Функция для отправки батча чатов на сервер
        async function flushBatchTakeQueue() {
            if (batchTakeQueue.length === 0) return;
            
            // Предотвращаем параллельные запросы
            if (batchTakeInProgress) {
                console.warn('[BATCH TAKE] Уже выполняется, пропускаем');
                return;
            }
            
            batchTakeInProgress = true;
            const chatIds = [...batchTakeQueue];
            batchTakeQueue = [];
            
            if (chatIds.length === 0) {
                batchTakeInProgress = false;
                return;
            }
            
            try {
                // Используем улучшенную функцию fetch с retry
                const response = await fetchWithRetry('/api/chats/batch-take', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({ chat_ids: chatIds })
                }, 3);
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    // Обрабатываем успешные назначения
                    const taken = data.taken || [];
                    const errors = data.errors || [];
                    
                    // Убеждаемся, что все успешно назначенные чаты имеют правильные данные
                    taken.forEach(chatId => {
                        const chatIndex = allChats.findIndex(c => c.id === chatId);
                        if (chatIndex !== -1) {
                            // Убеждаемся, что assigned_manager_id установлен правильно
                            if (!allChats[chatIndex].assigned_manager_id || allChats[chatIndex].assigned_manager_id === true) {
                                allChats[chatIndex].assigned_manager_id = currentUserId;
                            }
                            // Убеждаемся, что assigned_manager_name установлен правильно
                            if (!allChats[chatIndex].assigned_manager_name || allChats[chatIndex].assigned_manager_name !== currentUsername) {
                                allChats[chatIndex].assigned_manager_name = currentUsername;
                            }
                        }
                    });
                    
                    // Обновляем счетчики один раз для всего батча
                    updateCounters();
                    
                    if (errors.length > 0) {
                        // Откатываем оптимистичные обновления для чатов с ошибками
                        errors.forEach(err => {
                            const chatId = err.chat_id;
                            locallyTakenChats.delete(chatId);
                            locallyTakenChatsTimestamps.delete(chatId);
                            const chatIndex = allChats.findIndex(c => c.id === chatId);
                            if (chatIndex !== -1) {
                                allChats[chatIndex].assigned_manager_id = null;
                                allChats[chatIndex].assigned_manager_name = null;
                            }
                        });
                        
                        // Восстанавливаем чаты в DOM если нужно
                        if (currentSort === 'all' && errors.length > 0) {
                            applySort('all');
                            renderChatsList();
                        }
                    }
                    
                    // Если есть успешно назначенные чаты, обновляем список для текущего фильтра
                    if (taken.length > 0) {
                        // ВАЖНО: Сохраняем информацию о взятых чатах перед загрузкой
                        // чтобы не потерять их при обновлении с сервера
                        const takenChatsData = taken.map(chatId => {
                            const chatIndex = allChats.findIndex(c => c.id === chatId);
                            if (chatIndex !== -1) {
                                return {
                                    id: chatId,
                                    assigned_manager_id: allChats[chatIndex].assigned_manager_id,
                                    assigned_manager_name: allChats[chatIndex].assigned_manager_name
                                };
                            }
                            return null;
                        }).filter(Boolean);
                        
                        // Перезагружаем чаты с сервера для получения актуальных данных
                        if (typeof window.loadChats === 'function') {
                            window.loadChats(false, true).then(() => {
                                // Восстанавливаем данные для взятых чатов, если сервер их не обновил
                                takenChatsData.forEach(takenChat => {
                                    const chatIndex = allChats.findIndex(c => c.id === takenChat.id);
                                    if (chatIndex !== -1) {
                                        const chat = allChats[chatIndex];
                                        // Если сервер не обновил assigned_manager_id, восстанавливаем локальное значение
                                        if (!chat.assigned_manager_id || chat.assigned_manager_id === null) {
                                            chat.assigned_manager_id = takenChat.assigned_manager_id || currentUserId;
                                            chat.assigned_manager_name = takenChat.assigned_manager_name || currentUsername;
                                            debugLog('[BATCH TAKE] Восстановлены локальные данные для чата', takenChat.id);
                                        } else if (chat.assigned_manager_id !== currentUserId) {
                                            // Если сервер вернул другой ID, проверяем - возможно это ошибка
                                            if (DEBUG_MODE) {
                                                console.warn('[BATCH TAKE] Сервер вернул другой assigned_manager_id для чата', takenChat.id, 
                                                           'ожидали:', currentUserId, 'получили:', chat.assigned_manager_id);
                                            }
                                        }
                                    }
                                });
                                
                                // После загрузки применяем текущую сортировку
                                applySort(currentSort);
                                renderChatsList();
                                
                                // Дополнительная проверка: убеждаемся что все взятые чаты видны в "Мои чаты"
                                if (currentSort === 'my') {
                                    let missingChats = [];
                                    taken.forEach(chatId => {
                                        const chatIndex = allChats.findIndex(c => c.id === chatId);
                                        if (chatIndex !== -1) {
                                            const chat = allChats[chatIndex];
                                            // Убеждаемся, что assigned_manager_id установлен правильно
                                            if (!chat.assigned_manager_id || chat.assigned_manager_id !== currentUserId) {
                                                chat.assigned_manager_id = currentUserId;
                                                chat.assigned_manager_name = currentUsername;
                                                missingChats.push(chatId);
                                            }
                                        } else {
                                            missingChats.push(chatId);
                                        }
                                    });
                                    if (missingChats.length > 0) {
                                        debugLog('[BATCH TAKE] Исправлены данные для чатов:', missingChats);
                                        // Перерисовываем список еще раз
                                        applySort(currentSort);
                                        renderChatsList();
                                    }
                                }
                            }).catch(() => {
                                // Если загрузка не удалась, используем локальные данные
                                applySort(currentSort);
                                renderChatsList();
                            });
                        } else {
                            // Если loadChats недоступна, просто обновляем список с текущими данными
                            applySort(currentSort);
                            renderChatsList();
                        }
                        
                        // ВАЖНО: Очищаем locallyTakenChats для успешно назначенных чатов через небольшую задержку
                        // Это дает серверу время обновить данные перед следующей синхронизацией
                        setTimeout(() => {
                            taken.forEach(chatId => {
                                const chatIndex = allChats.findIndex(c => c.id === chatId);
                                if (chatIndex !== -1) {
                                    const chat = allChats[chatIndex];
                                    // Если сервер подтвердил назначение, удаляем из Set
                                    if (chat.assigned_manager_id && chat.assigned_manager_id === currentUserId) {
                                        locallyTakenChats.delete(chatId);
                                        locallyTakenChatsTimestamps.delete(chatId);
                                        debugLog('[BATCH TAKE] Удален чат', chatId, 'из locallyTakenChats после подтверждения сервера');
                                    }
                                }
                            });
                        }, DELAYS.BATCH_TAKE_CLEANUP); // Задержка для обновления на сервере
                    }
                } else {
                    // При ошибке откатываем все оптимистичные обновления
                    chatIds.forEach(chatId => {
                        locallyTakenChats.delete(chatId);
                        locallyTakenChatsTimestamps.delete(chatId);
                        const chatIndex = allChats.findIndex(c => c.id === chatId);
                        if (chatIndex !== -1) {
                            allChats[chatIndex].assigned_manager_id = null;
                            allChats[chatIndex].assigned_manager_name = null;
                        }
                    });
                    
                    if (currentSort === 'all') {
                        applySort('all');
                        renderChatsList();
                    }
                    
                    showNotification(`❌ Ошибка массового назначения чатов`, 'error');
                }
            } catch (error) {
                debugError('Ошибка при массовом назначении чатов:', error);
                // Откатываем все оптимистичные обновления
                chatIds.forEach(chatId => {
                    locallyTakenChats.delete(chatId);
                    locallyTakenChatsTimestamps.delete(chatId);
                    const chatIndex = allChats.findIndex(c => c.id === chatId);
                    if (chatIndex !== -1) {
                        allChats[chatIndex].assigned_manager_id = null;
                        allChats[chatIndex].assigned_manager_name = null;
                    }
                });
                showNotification(`❌ Ошибка сети при назначении чатов`, 'error');
            } finally {
                batchTakeInProgress = false;
                
                if (currentSort === 'all') {
                    applySort('all');
                    renderChatsList();
                }
            }
        }
        
        // Оптимизированная функция обновления счетчиков
        function updateCounters() {
            initDOMCache();
            const myChatsCountEl = domCache.myChatsCount;
            const poolCountEl = domCache.poolChatsCount;
            if (!myChatsCountEl && !poolCountEl) return;
            
            let myCount = 0, poolCount = 0;
            for (let i = 0; i < allChats.length; i++) {
                const c = allChats[i];
                if (c.status === 'completed' || c.status === 'blocked') continue;
                // Проверяем по ID (более надежно) или по имени
                const isMyChat = c.assigned_manager_id && c.assigned_manager_id !== null && c.assigned_manager_id !== undefined && 
                    (c.assigned_manager_id === currentUserId || c.assigned_manager_name === currentUsername);
                if (isMyChat) {
                    myCount++;
                } else if (!c.assigned_manager_id || c.assigned_manager_id === null || c.assigned_manager_id === undefined || c.assigned_manager_id === false) {
                    poolCount++;
                }
            }
            if (myChatsCountEl) myChatsCountEl.textContent = `(${myCount})`;
            if (poolCountEl) poolCountEl.textContent = `(${poolCount})`;
        }
        
        function takeChatFromPool(chatId) {
            chatId = Number(chatId);
            if (!chatId || isNaN(chatId)) return;
            
            // Находим чат в массиве allChats для оптимистичного обновления
            const chatIndex = allChats.findIndex(c => c.id === chatId);
            if (chatIndex === -1) return;
            
            const chat = allChats[chatIndex];
            
            // Проверяем, не взят ли уже чат
            if (chat.assigned_manager_id) return;
            
            // Добавляем чат в Set локально взятых чатов
            locallyTakenChats.add(chatId);
            
            // Оптимистичное обновление данных чата
            // Убеждаемся, что currentUserId установлен, иначе не можем взять чат
            if (currentUserId === null || currentUserId === undefined) {
                debugError('[TAKE CHAT] currentUserId не установлен, невозможно взять чат');
                locallyTakenChats.delete(chatId);
                locallyTakenChatsTimestamps.delete(chatId);
                showNotification('❌ Ошибка: не удалось определить ID пользователя', 'error');
                return;
            }
            chat.assigned_manager_id = currentUserId;
            chat.assigned_manager_name = currentUsername;
            
            // Мгновенно удаляем чат из filteredChats и DOM только если мы в фильтре "Общий пул"
            if (currentSort === 'all') {
                const filteredIndex = filteredChats.findIndex(c => c.id === chatId);
                if (filteredIndex !== -1) {
                    filteredChats.splice(filteredIndex, 1);
                }
                
                // Удаляем карточку чата из DOM только если мы в "Общий пул"
                const chatCard = document.querySelector(`[data-chat-id="${chatId}"]`);
                if (chatCard) {
                    chatCard.remove();
                }
            } else if (currentSort === 'my') {
                // Если мы в фильтре "Мои чаты", добавляем чат в filteredChats если его там еще нет
                const filteredIndex = filteredChats.findIndex(c => c.id === chatId);
                if (filteredIndex === -1) {
                    // Проверяем, что чат проходит фильтр "Мои чаты" (по ID или имени)
                    const isMyChat = chat.assigned_manager_id && 
                        (chat.assigned_manager_id === currentUserId || 
                         chat.assigned_manager_name === currentUsername ||
                         (chat.assigned_manager_name && currentUsername && 
                          chat.assigned_manager_name.includes(currentUsername)));
                    if (isMyChat &&
                        chat.status !== 'completed' &&
                        chat.status !== 'blocked') {
                        filteredChats.push(chat);
                        // Применяем сортировку и перерисовываем список
                        applySort(currentSort);
                        renderChatsList();
                    }
                }
            }
            
            // Добавляем в очередь для батч-обработки
            if (!batchTakeQueue.includes(chatId)) {
                batchTakeQueue.push(chatId);
            }
            
            // Если очередь достигла размера батча, отправляем сразу
            if (batchTakeQueue.length >= BATCH_TAKE_SIZE) {
                if (batchTakeTimer) {
                    clearTimeout(batchTakeTimer);
                    batchTakeTimer = null;
                }
                flushBatchTakeQueue();
            } else {
                // Иначе устанавливаем таймер для отправки через задержку
                if (batchTakeTimer) {
                    clearTimeout(batchTakeTimer);
                }
                batchTakeTimer = setTimeout(flushBatchTakeQueue, BATCH_TAKE_DELAY);
            }
            
            // Обновляем счетчики сразу (оптимистично)
            updateCounters();
        }

        function returnChatToPool(chatId) {
            chatId = Number(chatId);
            if (!chatId || isNaN(chatId)) return;
            
            // Находим чат в массиве allChats для оптимистичного обновления
            const chatIndex = allChats.findIndex(c => c.id === chatId);
            if (chatIndex === -1) return;
            
            const chat = allChats[chatIndex];
            // УБРАЛИ ПРОВЕРКУ - делаем оптимистичное обновление сразу, проверка на сервере
            // if (!chat || !chat.assigned_manager_id) return; // Уже в пуле или не мой чат
            
            // НОВЫЙ ПОДХОД: Удаляем из Set локально взятых чатов
            locallyTakenChats.delete(chatId);
            locallyTakenChatsTimestamps.delete(chatId);
            
            // Сохраняем оригинальные значения для возможного отката
            const originalManagerId = chat.assigned_manager_id;
            const originalManagerName = chat.assigned_manager_name;
            
            // МГНОВЕННО удаляем карточку чата из DOM если мы в фильтре "Мои чаты"
            if (currentSort === 'my') {
                const chatCard = document.querySelector(`[data-chat-id="${chatId}"]`);
                if (chatCard) chatCard.remove();
            }
            
            // Оптимистичное обновление данных чата
            chat.assigned_manager_id = null;
            chat.assigned_manager_name = null;
            
            // МГНОВЕННО обновляем счетчики напрямую (без фильтрации всего массива)
            const myChatsCountEl = document.getElementById('my-chats-count');
            const poolCountEl = document.getElementById('pool-chats-count');
            if (myChatsCountEl || poolCountEl) {
                let myCount = 0, poolCount = 0;
                for (let i = 0; i < allChats.length; i++) {
                    const c = allChats[i];
                    if (c.status === 'completed' || c.status === 'blocked') continue;
                    // Проверяем по ID (более надежно) или по имени
                    const isMyChat = c.assigned_manager_id && 
                        (c.assigned_manager_id === currentUserId || c.assigned_manager_name === currentUsername);
                    if (isMyChat) myCount++;
                    else if (!c.assigned_manager_id) poolCount++;
                }
                if (myChatsCountEl) myChatsCountEl.textContent = `(${myCount})`;
                if (poolCountEl) poolCountEl.textContent = `(${poolCount})`;
            }
            
            // Если мы в фильтре "Общий пул", добавляем чат в список
            if (currentSort === 'all' && chat.status !== 'completed' && chat.status !== 'blocked') {
                applySort('all');
                renderChatsList();
            }
            
            // Отправляем запрос на сервер в фоне (полностью асинхронно)
            fetch(`/api/chats/${chatId}/return`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include'
            }).then(response => {
                return response.json().then(data => ({ response, data })).catch(() => ({ response, data: {} }));
            }).then(({ response, data }) => {
                
                if (!response.ok) {
                    const errorMessage = data.error || `HTTP ${response.status}`;
                    const errorCode = data.code || 'UNKNOWN';
                    
                    // При ошибке откатываем оптимистичное обновление
                    if (chatIndex !== -1 && allChats[chatIndex]) {
                        allChats[chatIndex].assigned_manager_id = originalManagerId;
                        allChats[chatIndex].assigned_manager_name = originalManagerName;
                    }
                    
                    // Восстанавливаем чат в DOM если нужно
                    if (currentSort === 'my') {
                        applySort('my');
                        renderChatsList();
                    }
                    
                    // Показываем ошибку
                    let userMessage = 'Ошибка возврата чата';
                    if (errorCode === 'NOT_ASSIGNED_TO_YOU') userMessage = 'Этот чат назначен другому менеджеру';
                    else if (errorCode === 'ALREADY_IN_POOL') userMessage = 'Чат уже в пуле';
                    else if (errorCode === 'NOT_FOUND') userMessage = 'Чат не найден';
                    else userMessage = errorMessage || 'Ошибка возврата чата';
                    
                    showNotification(`❌ ${userMessage}`, 'error');
                    return;
                }
                
                // Успех - НЕ вызываем loadChats, чтобы чат не вернулся обратно
                // Данные уже обновлены оптимистично
                // Обновляем filteredChats, чтобы чат не появился при следующей перерисовке
                if (currentSort === 'my') {
                    // Удаляем чат из filteredChats, если он там есть
                    const filteredIndex = filteredChats.findIndex(c => c.id === chatId);
                    if (filteredIndex !== -1) {
                        filteredChats.splice(filteredIndex, 1);
                    }
                } else if (currentSort === 'all') {
                    // Добавляем чат в filteredChats, если он должен быть в пуле
                    if (chat.status !== 'completed' && chat.status !== 'blocked') {
                        const exists = filteredChats.find(c => c.id === chatId);
                        if (!exists) {
                            filteredChats.push(chat);
                            applySort('all');
                            renderChatsList();
                        }
                    }
                }
            }).catch(error => {
                // Обработка сетевых ошибок
                console.error('Сетевая ошибка при возврате чата в пул:', error);
                
                // Откатываем оптимистичное обновление
                if (chatIndex !== -1 && allChats[chatIndex]) {
                    // Восстанавливаем данные - перезагружаем
                    loadChats(false, true).catch(() => {});
                }
                
                showNotification('❌ Ошибка сети. Проверьте подключение.', 'error');
                loadChats(false, true).catch(() => {});
            });
        }

        // Автоматическое извлечение product_url для чатов без него (без подтверждения)
        async function autoExtractProductUrls() {
            const chatsWithoutUrl = allChats.filter(chat => !chat.product_url || chat.product_url === null).length;
            
            if (chatsWithoutUrl === 0) {
                return; // Все чаты уже имеют product_url
            }
            
            // Ограничиваем количество чатов для автоматической обработки (чтобы не перегружать API)
            const MAX_AUTO_EXTRACT = 20; // Максимум 20 чатов за раз
            
            // Автоматическое извлечение product_url отключено
            // Эндпоинты /api/chats/extract-all-product-urls не реализованы
            // Если нужно извлечь product_url для конкретного чата, используйте кнопку в интерфейсе
            debugLog('[AUTO-EXTRACT] Автоматическое извлечение product_url отключено');
        }
        
        // Ручное извлечение (для совместимости, если где-то еще вызывается)
        async function extractAllProductUrls() {
            // Просто вызываем автоматическое извлечение
            await autoExtractProductUrls();
        }

        // Функция для возврата всех чатов в пул
        function returnAllChatsToPool() {
            // Находим все мои чаты
            const myChats = allChats.filter(chat => {
                const isMyChat = chat.assigned_manager_id && 
                    (chat.assigned_manager_id === currentUserId || 
                     chat.assigned_manager_name === currentUsername ||
                     (chat.assigned_manager_name && currentUsername && 
                      chat.assigned_manager_name.includes(currentUsername)));
                return isMyChat &&
                    chat.status !== 'completed' &&
                    chat.status !== 'blocked';
            });
            
            if (myChats.length === 0) {
                showNotification('ℹ️ Нет чатов для возврата в пул', 'info');
                return;
            }
            
            // Подтверждение
            if (!confirm(`Вернуть все ${myChats.length} чатов в пул?`)) {
                return;
            }
            
            // МГНОВЕННО обновляем все чаты оптимистично
            const chatIds = [];
            myChats.forEach(chat => {
                chatIds.push(chat.id);
                locallyTakenChats.delete(chat.id);
                locallyTakenChatsTimestamps.delete(chat.id);
                chat.assigned_manager_id = null;
                chat.assigned_manager_name = null;
            });
            
            // МГНОВЕННО удаляем все карточки из DOM если мы в фильтре "Мои чаты"
            if (currentSort === 'my') {
                chatIds.forEach(chatId => {
                    const chatCard = document.querySelector(`[data-chat-id="${chatId}"]`);
                    if (chatCard) chatCard.remove();
                });
            }
            
            // МГНОВЕННО обновляем счетчики
            initDOMCache();
            const myChatsCountEl = domCache.myChatsCount;
            const poolCountEl = domCache.poolChatsCount;
            if (myChatsCountEl || poolCountEl) {
                let myCount = 0, poolCount = 0;
                for (let i = 0; i < allChats.length; i++) {
                    const c = allChats[i];
                    if (c.status === 'completed' || c.status === 'blocked') continue;
                    // Проверяем по ID (более надежно) или по имени
                    const isMyChat = c.assigned_manager_id && 
                        (c.assigned_manager_id === currentUserId || c.assigned_manager_name === currentUsername);
                    if (isMyChat) myCount++;
                    else if (!c.assigned_manager_id) poolCount++;
                }
                if (myChatsCountEl) myChatsCountEl.textContent = `(${myCount})`;
                if (poolCountEl) poolCountEl.textContent = `(${poolCount})`;
            }
            
            // Если мы в фильтре "Общий пул", добавляем чаты в список
            if (currentSort === 'all') {
                applySort('all');
                renderChatsList();
            }
            
            // Отправляем запрос на сервер в фоне
            fetch('/api/chats/return-all', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include'
            }).then(response => {
                return response.json().then(data => ({ response, data })).catch(() => ({ response, data: {} }));
            }).then(({ response, data }) => {
                if (!response.ok) {
                    const errorMessage = data.error || `HTTP ${response.status}`;
                    
                    // При ошибке откатываем оптимистичное обновление
                    myChats.forEach(chat => {
                        const chatIndex = allChats.findIndex(c => c.id === chat.id);
                        if (chatIndex !== -1) {
                            allChats[chatIndex].assigned_manager_id = currentUserId;
                            allChats[chatIndex].assigned_manager_name = currentUsername;
                        }
                    });
                    
                    // Восстанавливаем чаты в DOM
                    if (currentSort === 'my') {
                        applySort('my');
                        renderChatsList();
                    }
                    
                    showNotification(`❌ ${errorMessage}`, 'error');
                    return;
                }
                
                // Успех
                showNotification(`✅ Возвращено ${data.count || myChats.length} чатов в пул`, 'success');
            }).catch(error => {
                debugError('Сетевая ошибка при возврате всех чатов:', error);
                
                // Откатываем оптимистичное обновление
                myChats.forEach(chat => {
                    const chatIndex = allChats.findIndex(c => c.id === chat.id);
                    if (chatIndex !== -1) {
                        allChats[chatIndex].assigned_manager_id = currentUserId;
                        allChats[chatIndex].assigned_manager_name = currentUsername;
                    }
                });
                
                // Восстанавливаем чаты в DOM
                if (currentSort === 'my') {
                    applySort('my');
                    renderChatsList();
                }
                
                showNotification('❌ Ошибка сети. Проверьте подключение.', 'error');
            });
        }

        function restoreChat(chatId) {
            chatId = Number(chatId);
            if (!chatId || isNaN(chatId)) return;
            apiAction(`/api/chats/${chatId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({status: 'active'})
            }, '✅ Чат восстановлен', async () => {
                await loadChats();
                applySort('all');
                selectChat(chatId);
            });
        }

        function blockChat(chatId) {
            chatId = Number(chatId);
            if (!chatId || isNaN(chatId)) return;
            if (!confirm('Вы уверены, что хотите заблокировать этот чат?')) return;
            apiAction(`/api/chats/${chatId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({status: 'blocked'})
            }, '🚫 Чат заблокирован', async () => {
                await loadChats();
                if (currentSort === 'blocked') {
                    applySort('all');
                }
            });
        }

        function unblockChat(chatId) {
            chatId = Number(chatId);
            if (!chatId || isNaN(chatId)) return;
            apiAction(`/api/chats/${chatId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                credentials: 'include',
                body: JSON.stringify({status: 'active'})
            }, '🔓 Чат разблокирован', async () => {
                await loadChats();
                applySort('all');
                selectChat(chatId);
            });
        }

        // Вспомогательные функции
        function getPriorityIcon(priority) {
            const icons = {'urgent': '🔥', 'new': '🆕', 'active': '💬', 'delivery': '🚚'};
            return icons[priority] || '💬';
        }

        function getPriorityText(priority) {
            const texts = {'urgent': 'СРОЧНО', 'new': 'НОВЫЙ', 'active': 'АКТИВ', 'delivery': 'ДОСТАВКА'};
            return texts[priority] || 'ЧАТ';
        }

        /**
         * Получение класса для таймера ответа
         * 
         * Возвращает класс CSS в зависимости от времени ответа:
         * - urgent: >= 20 минут (красный, мигает)
         * - warning: >= 10 минут (желтый)
         * - normal: < 10 минут (зеленый)
         * 
         * @function getTimerClass
         * @param {number} timer - Время ответа в минутах
         * @returns {string} CSS класс
         */
        function getTimerClass(timer) {
            if (timer >= 20) return 'urgent';
            if (timer >= 10) return 'warning';
            return 'normal';
        }

        /**
         * Форматирование времени ответа
         * 
         * Преобразует минуты в читаемый формат:
         * - Меньше 60 минут: "X мин"
         * - Больше 60 минут: "Xч Yм"
         * 
         * @function formatTimer
         * @param {number} minutes - Время в минутах
         * @returns {string} Отформатированное время
         */
        function formatTimer(minutes) {
            // Проверяем, что minutes - это число
            const mins = typeof minutes === 'number' ? minutes : (parseInt(minutes) || 0);
            
            if (mins === 0) return '0 мин';
            
            // Показываем точное количество минут для первых 60 минут
            if (mins < 60) {
                return `${Math.floor(mins)} мин`;
            }
            
            // Для более часа показываем часы и минуты
            const hours = Math.floor(mins / 60);
            const remainingMins = Math.floor(mins % 60);
            
            // Если больше 24 часов, показываем дни
            if (hours >= 24) {
                const days = Math.floor(hours / 24);
                const remainingHours = hours % 24;
                if (remainingHours === 0 && remainingMins === 0) {
                    return `${days}д`;
                } else if (remainingHours === 0) {
                    return `${days}д ${remainingMins}м`;
                } else if (remainingMins === 0) {
                    return `${days}д ${remainingHours}ч`;
                }
                return `${days}д ${remainingHours}ч ${remainingMins}м`;
            }
            
            // Меньше 24 часов - показываем часы и минуты
            if (remainingMins === 0) {
                return `${hours}ч`;
            }
            return `${hours}ч ${remainingMins}м`;
        }

        // Кэш для отслеживания последней синхронизации каждого чата
        const lastSyncTime = new Map();
        const SYNC_COOLDOWN = 5000; // Минимум 5 секунд между синхронизациями одного чата
        
        function startMessagesAutoRefresh() {
            if (messagesAutoRefreshInterval) clearInterval(messagesAutoRefreshInterval);
            // Обновление каждые 3 секунды для быстрого получения новых сообщений из Авито
            // Оптимизированное обновление сообщений с debounce и проверкой видимости
            let lastMessageUpdate = 0;
            const MESSAGE_UPDATE_INTERVAL = 10000; // 10 секунд (оптимизировано для производительности)
            let consecutiveErrors = 0;
            const MAX_CONSECUTIVE_ERRORS = 3;
            
            messagesAutoRefreshInterval = setInterval(() => {
                if (currentChatId && document.visibilityState === 'visible') {
                    const now = Date.now();
                    // Обновляем только если прошло достаточно времени и страница видима
                    if (now - lastMessageUpdate >= MESSAGE_UPDATE_INTERVAL) {
                        lastMessageUpdate = now;
                        
                        // Загружаем сообщения с обработкой ошибок
                        loadChatMessages(currentChatId, 'refresh').then(() => {
                            consecutiveErrors = 0; // Сбрасываем счетчик ошибок при успехе
                        }).catch((error) => {
                            consecutiveErrors++;
                            if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
                                debugLog('[AUTO REFRESH] Много ошибок подряд, увеличиваем интервал');
                                // При ошибках увеличиваем интервал до 30 секунд
                                clearInterval(messagesAutoRefreshInterval);
                                messagesAutoRefreshInterval = setInterval(() => {
                                    if (currentChatId && document.visibilityState === 'visible') {
                                        loadChatMessages(currentChatId, 'refresh').then(() => {
                                            consecutiveErrors = 0;
                                            // Возвращаемся к нормальному интервалу
                                            clearInterval(messagesAutoRefreshInterval);
                                            startMessagesAutoRefresh();
                                        });
                                    }
                                }, 30000);
                            }
                        });
                    }
                }
            }, MESSAGE_UPDATE_INTERVAL);
        }

        /**
         * Обновление времени response_timer для всех отображенных чатов
         * Вычисляет время на основе текущего момента и базового времени с сервера
         * Исправлено: корректно обрабатывает смену даты
         */
        // Кеш для DOM элементов таймеров (обновляется только при рендеринге)
        let chatCardsCache = null;
        let cacheTimestamp = 0;
        const CACHE_REFRESH_INTERVAL = 5000; // Обновляем кеш каждые 5 секунд
        
        function updateResponseTimers() {
            if (!allChats || allChats.length === 0) return;
            
            const now = Date.now();
            const nowDate = new Date(now);
            const today = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate()).getTime();
            
            // Оптимизация: обновляем кеш DOM элементов только периодически
            if (!chatCardsCache || (now - cacheTimestamp) > CACHE_REFRESH_INTERVAL) {
                const container = document.querySelector('.chats-list');
                if (!container) return;
                
                chatCardsCache = new Map();
                container.querySelectorAll('.chat-card').forEach(card => {
                    const chatId = card.getAttribute('data-chat-id');
                    if (chatId) {
                        chatCardsCache.set(Number(chatId), {
                            card: card,
                            timerElement: card.querySelector('.response-time')
                        });
                    }
                });
                cacheTimestamp = now;
            }
            
            // Обновляем только видимые чаты (оптимизация для большого количества чатов)
            const visibleChats = allChats.filter(chat => {
                if (chat.status === 'completed' || chat.status === 'blocked') return false;
                const cached = chatCardsCache?.get(chat.id);
                return cached && cached.card.offsetParent !== null; // Проверяем видимость
            });
            
            // Обновляем только видимые элементы таймеров
            visibleChats.forEach(chat => {
                // Если у чата нет базового времени обновления, сохраняем текущее
                if (!chat._timerBaseTime) {
                    chat._timerBaseTime = now;
                    chat._timerBaseValue = chat.response_timer || 0;
                    chat._timerBaseDate = today;
                    return;
                }
                
                // Проверяем, изменилась ли дата с момента последнего обновления
                const baseDate = chat._timerBaseDate || today;
                const dateChanged = baseDate !== today;
                
                // Если дата изменилась, сбрасываем базовые значения
                if (dateChanged) {
                    chat._timerBaseTime = now;
                    chat._timerBaseValue = chat.response_timer || 0;
                    chat._timerBaseDate = today;
                }
                
                // Вычисляем сколько минут прошло с момента последнего обновления данных
                const timeDiff = now - chat._timerBaseTime;
                const minutesPassed = Math.floor(timeDiff / 60000);
                
                // Обновляем response_timer на основе базового значения + прошедшее время
                let newTimer = (chat._timerBaseValue || 0) + minutesPassed;
                
                // Защита от отрицательных значений и нереально больших значений
                if (newTimer < 0 || newTimer > 10000) {
                    chat._timerBaseTime = now;
                    chat._timerBaseValue = chat.response_timer || 0;
                    chat._timerBaseDate = today;
                    newTimer = chat._timerBaseValue || 0;
                }
                
                // Обновляем только если значение изменилось на целую минуту или больше
                const currentTimer = chat.response_timer || 0;
                if (Math.abs(newTimer - currentTimer) >= 1 || dateChanged) {
                    chat.response_timer = Math.max(0, newTimer);
                    chat._timerBaseTime = now;
                    chat._timerBaseValue = chat.response_timer;
                    chat._timerBaseDate = today;
                    
                    // Используем кешированные элементы
                    const cached = chatCardsCache?.get(chat.id);
                    if (cached) {
                        const chatCard = cached.card;
                        const timerElement = cached.timerElement;
                        
                        // Обновляем класс мигания карточки
                        if (chat.response_timer >= 20) {
                            chatCard.classList.add('blink-red');
                        } else {
                            chatCard.classList.remove('blink-red');
                        }
                        
                        if (timerElement && chat.response_timer > 0) {
                            const timerClass = getTimerClass(chat.response_timer);
                            const timerText = formatTimer(chat.response_timer);
                            const isUrgent = chat.response_timer >= 20;
                            timerElement.className = `response-time ${timerClass} ${isUrgent ? 'blink' : ''}`;
                            timerElement.textContent = `⏱️ ${timerText}`;
                            timerElement.style.color = isUrgent ? '#ef4444' : '';
                            timerElement.style.fontWeight = isUrgent ? '700' : '';
                            timerElement.style.display = '';
                        } else if (timerElement && chat.response_timer === 0) {
                            timerElement.style.display = 'none';
                        }
                    }
                }
            });
        }

        /**
         * Сброс базового времени для таймеров при обновлении данных с сервера
         * Исправлено: сохраняет информацию о текущей дате для корректной обработки смены даты
         */
        function resetTimerBaseTimes() {
            const now = Date.now();
            const nowDate = new Date(now);
            const today = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate()).getTime();
            
            allChats.forEach(chat => {
                chat._timerBaseTime = now;
                chat._timerBaseValue = chat.response_timer || 0;
                chat._timerBaseDate = today;
            });
        }

        window.showNotification = function showNotification(message, type = 'info') {
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

        function updateSendAvailability() {
            const sendButton = document.querySelector('.send-button');
            const textarea = document.getElementById('message-text');
            const warning = document.getElementById('avito-warning');
            const disabled = !currentChatHasAvito || !currentChatId || messagesLoading;
            if (sendButton) sendButton.disabled = disabled;
            if (textarea) textarea.disabled = disabled;
            if (warning) warning.style.display = disabled ? 'block' : 'none';
            document.querySelectorAll('.quick-action').forEach(btn => {
                btn.classList.toggle('is-disabled', messagesLoading);
            });
        }

        // Инициализация
        // ЯВНОЕ ЛОГИРОВАНИЕ ПРИ ЗАГРУЗКЕ СТРАНИЦЫ
        
        document.addEventListener('DOMContentLoaded', function() {
            const textarea = document.getElementById('message-text');
            if (textarea) {
                textarea.addEventListener('input', function() {
                    this.style.height = 'auto';
                    this.style.height = Math.min(this.scrollHeight, 140) + 'px';
                });

                textarea.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                    }
                });
            }

            const searchInput = document.getElementById('chat-search');
            if (searchInput) {
                searchInput.addEventListener('input', (event) => handleSearchInput(event.target.value));
            }

            // Обработчики для фильтров - мгновенное переключение без запросов к серверу
            document.querySelectorAll('.filter-chip[data-sort]').forEach(chip => {
                chip.addEventListener('click', () => {
                    // Мгновенно обновляем активный фильтр
                    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    // Мгновенно применяем фильтр (работает на клиенте, без запросов)
                    applySort(chip.dataset.sort);
                });
            });
            
            // Обработчики для сортировки (новые/старые)
            document.querySelectorAll('.sort-chip[data-sort-order]').forEach(chip => {
                chip.addEventListener('click', () => {
                    currentSortOrder = chip.dataset.sortOrder;
                    // Обновляем активную сортировку
                    document.querySelectorAll('.sort-chip[data-sort-order]').forEach(c => {
                        c.classList.toggle('active', c.dataset.sortOrder === currentSortOrder);
                    });
                    applySort(currentSort); // Применяем текущий фильтр с новым порядком
                });
            });

            document.addEventListener('click', function(event) {
                if (!event.target.closest('#quick-replies-menu') && !event.target.closest('.quick-action')) {
                    document.getElementById('quick-replies-menu').classList.remove('active');
                }
            });

            const urlParams = new URLSearchParams(window.location.search);
            const urlChatId = urlParams.get('chat_id');
            if (urlChatId) {
                const parsedId = Number(urlChatId);
                if (!Number.isNaN(parsedId)) {
                    initialChatIdFromUrl = parsedId;
                }
            }

            // Сначала загружаем кеш для мгновенного отображения
            const cachedChats = loadChatsFromCache();
            if (cachedChats && cachedChats.length > 0) {
                allChats = cachedChats;
                resetTimerBaseTimes();
                applySort(currentSort);
                renderChatsList();
            }
            
            // ========== УМНЫЕ ФИЛЬТРЫ ==========
            function initializeSmartFilters() {
                // Заполняем фильтры магазинами и менеджерами
                const shopSelect = document.getElementById('filter-shop');
                const managerSelect = document.getElementById('filter-manager');
                
                if (shopSelect) {
                    const shops = [...new Map(allChats.map(c => [c.shop_id, { id: c.shop_id, name: c.shop_name }]).filter(s => s[1].id && s[1].name))].values();
                    shops.forEach(shop => {
                        const option = document.createElement('option');
                        option.value = shop.id;
                        option.textContent = shop.name;
                        shopSelect.appendChild(option);
                    });
                }
                
                if (managerSelect) {
                    const managers = [...new Map(allChats.map(c => [c.assigned_manager_id, { id: c.assigned_manager_id, name: c.assigned_manager_name }]).filter(m => m[1].id && m[1].name))].values();
                    managers.forEach(manager => {
                        const option = document.createElement('option');
                        option.value = manager.id;
                        option.textContent = manager.name;
                        managerSelect.appendChild(option);
                    });
                }
            }
            
            function applySmartFilters() {
                applySort(currentSort);
            }
            
            // ========== МАССОВЫЕ ДЕЙСТВИЯ ==========
            const selectedChats = new Set();
            
            function toggleChatSelection(chatId) {
                const checkbox = document.querySelector(`.chat-select-checkbox[data-chat-id="${chatId}"]`);
                if (!checkbox) return;
                
                if (checkbox.checked) {
                    selectedChats.add(chatId);
                } else {
                    selectedChats.delete(chatId);
                }
                
                updateBulkActionsButton();
            }
            
            function updateBulkActionsButton() {
                const btn = document.getElementById('bulk-actions-btn');
                const countSpan = document.getElementById('selected-count');
                
                if (selectedChats.size > 0) {
                    if (btn) btn.style.display = 'inline-flex';
                    if (countSpan) countSpan.textContent = selectedChats.size;
                } else {
                    if (btn) btn.style.display = 'none';
                }
            }
            
            function showBulkActionsMenu() {
                if (selectedChats.size === 0) return;
                
                const action = prompt(`Выбрано чатов: ${selectedChats.size}\n\nВыберите действие:\n1 - Взять из пула\n2 - Вернуть в пул\n3 - Завершить\n4 - Заблокировать\n5 - Отменить выбор`);
                if (!action) return;
                
                switch(action) {
                    case '1': bulkTakeChats(); break;
                    case '2': bulkReturnChats(); break;
                    case '3': bulkCompleteChats(); break;
                    case '4': bulkBlockChats(); break;
                    case '5': clearSelection(); break;
                }
            }
            
            function bulkTakeChats() {
                const chatIds = Array.from(selectedChats);
                chatIds.forEach(id => takeChatFromPool(id));
                clearSelection();
            }
            
            function bulkReturnChats() {
                const chatIds = Array.from(selectedChats);
                chatIds.forEach(id => returnChatToPool(id));
                clearSelection();
            }
            
            function bulkCompleteChats() {
                const chatIds = Array.from(selectedChats);
                chatIds.forEach(id => markAsCompleted(id));
                clearSelection();
            }
            
            function bulkBlockChats() {
                const chatIds = Array.from(selectedChats);
                chatIds.forEach(id => blockChat(id));
                clearSelection();
            }
            
            function clearSelection() {
                selectedChats.clear();
                document.querySelectorAll('.chat-select-checkbox').forEach(cb => cb.checked = false);
                updateBulkActionsButton();
            }
            
            // Автоматическая очистка старых записей из locallyTakenChats
            // Очищаем чаты, которые были взяты более 10 минут назад
            // (если сервер не подтвердил назначение за это время, вероятно что-то пошло не так)
            setInterval(() => {
                const now = Date.now();
                const MAX_LOCAL_AGE = 10 * 60 * 1000; // 10 минут
                
                locallyTakenChatsTimestamps.forEach((timestamp, chatId) => {
                    if (now - timestamp > MAX_LOCAL_AGE) {
                        // Проверяем, подтвердил ли сервер назначение
                        const chat = allChats.find(c => c.id === chatId);
                        if (!chat || !chat.assigned_manager_id || chat.assigned_manager_id !== currentUserId) {
                            // Сервер не подтвердил - удаляем из Set
                            locallyTakenChats.delete(chatId);
                            locallyTakenChatsTimestamps.delete(chatId);
                            debugLog(`[CLEANUP] Удален старый локально взятый чат ${chatId} (старше ${MAX_LOCAL_AGE}мс)`);
                        } else {
                            // Сервер подтвердил - удаляем timestamp, но оставляем в Set до следующей загрузки
                            locallyTakenChatsTimestamps.delete(chatId);
                        }
                    }
                });
            }, 60000); // Проверяем каждую минуту
            
            // Индикатор подключения (online/offline)
            let isOnline = navigator.onLine;
            const connectionIndicator = document.createElement('div');
            connectionIndicator.id = 'connection-indicator';
            connectionIndicator.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.875rem;
                z-index: 10000;
                display: none;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            `;
            document.body.appendChild(connectionIndicator);
            
            function updateConnectionIndicator() {
                if (isOnline) {
                    connectionIndicator.style.display = 'none';
                } else {
                    connectionIndicator.style.display = 'block';
                    connectionIndicator.style.background = '#ef4444';
                    connectionIndicator.style.color = 'white';
                    connectionIndicator.textContent = '⚠️ Нет подключения';
                }
            }
            
            window.addEventListener('online', () => {
                isOnline = true;
                updateConnectionIndicator();
                showNotification('✅ Подключение восстановлено', 'success');
                // Перезагружаем чаты после восстановления подключения
                if (typeof window.loadChats === 'function') {
                    window.loadChats(false, true);
                }
            });
            
            window.addEventListener('offline', () => {
                isOnline = false;
                updateConnectionIndicator();
                showNotification('⚠️ Нет подключения к интернету', 'warning');
            });
            
            updateConnectionIndicator();
            
            // Инициализация умных фильтров
            initializeSmartFilters();
            
            // Инициализируем видимость кнопки "Вернуть все в пул"
            const returnAllBtn = document.getElementById('return-all-btn');
            if (returnAllBtn) {
                if (currentSort === 'my') {
                    returnAllBtn.classList.remove('hidden');
                } else {
                    returnAllBtn.classList.add('hidden');
                }
            }
            
            debugLog('[INIT] Вызываем loadChats(true) для первой загрузки...');
            try {
                loadChats(true, cachedChats && cachedChats.length > 0); // Тихое обновление если есть кеш
            } catch (error) {
                debugError('[INIT] ОШИБКА при вызове loadChats:', error);
            }
            
            // ========== ОПТИМИЗИРОВАННАЯ СИСТЕМА ОБНОВЛЕНИЙ ==========
            // Централизованное управление всеми интервалами для оптимизации производительности
            
            let lastFullSync = Date.now();
            
            // Константы интервалов (оптимизировано для производительности)
            const CHATS_SYNC_INTERVAL = 30000; // 30 секунд - полная синхронизация
            const TIMER_UPDATE_INTERVAL = 30000; // 30 секунд - обновление таймеров (уменьшено для плавности)
            
            // Debounce функция для предотвращения частых запросов
            function debounce(func, wait) {
                let timeout;
                return function executedFunction(...args) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            }
            
            // Оптимизированная полная синхронизация
            let isSyncing = false; // Флаг для предотвращения параллельных синхронизаций
            async function performFullSync() {
                // Предотвращаем параллельные синхронизации
                if (isSyncing) {
                    debugLog('[AUTO SYNC] Синхронизация уже выполняется, пропускаем');
                    return;
                }
                
                // ВАЖНО: Не синхронизируем, если есть чаты в очереди назначения или недавно были назначения
                // Это предотвращает потерю локальных изменений
                if (batchTakeQueue.length > 0 || locallyTakenChats.size > 0) {
                    debugLog('[AUTO SYNC] Пропускаем синхронизацию: есть чаты в очереди назначения или локально взятые чаты');
                    return;
                }
                
                isSyncing = true;
                debugLog('[AUTO SYNC] Начинаем автоматическую синхронизацию чатов...');
                
                try {
                    const syncResponse = await fetch('/api/chats/sync', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        credentials: 'include',
                        body: JSON.stringify({}),
                        signal: AbortSignal.timeout(30000) // Таймаут 30 секунд
                    });
                    
                    if (syncResponse.ok) {
                        const syncData = await syncResponse.json();
                        debugLog('[AUTO SYNC] Синхронизация завершена:', syncData);
                        
                        // ВАЖНО: Сохраняем локальные изменения перед загрузкой
                        const savedLocalChanges = new Map();
                        locallyTakenChats.forEach(chatId => {
                            const chatIndex = allChats.findIndex(c => c.id === chatId);
                            if (chatIndex !== -1) {
                                savedLocalChanges.set(chatId, {
                                    assigned_manager_id: allChats[chatIndex].assigned_manager_id,
                                    assigned_manager_name: allChats[chatIndex].assigned_manager_name
                                });
                            }
                        });
                        
                        // Обновляем список чатов после синхронизации
                        if (typeof window.loadChats === 'function') {
                            await window.loadChats(false, true);
                            
                            // Восстанавливаем локальные изменения, если сервер их не обновил
                            savedLocalChanges.forEach((data, chatId) => {
                                const chatIndex = allChats.findIndex(c => c.id === chatId);
                                if (chatIndex !== -1) {
                                    const chat = allChats[chatIndex];
                                    if (!chat.assigned_manager_id || chat.assigned_manager_id === null) {
                                        chat.assigned_manager_id = data.assigned_manager_id || currentUserId;
                                        chat.assigned_manager_name = data.assigned_manager_name || currentUsername;
                                        debugLog('[AUTO SYNC] Восстановлены локальные изменения для чата', chatId);
                                    }
                                }
                            });
                            
                            // Применяем сортировку и обновляем отображение
                            if (typeof applySort === 'function') {
                                applySort(currentSort, true);
                            } else {
                                // Если applySort недоступна, просто обновляем список
                                if (typeof renderChatsList === 'function') {
                                    renderChatsList();
                                }
                            }
                        }
                    } else {
                        debugLog('[AUTO SYNC] Синхронизация не удалась:', syncResponse.status);
                    }
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        debugLog('[AUTO SYNC] Ошибка синхронизации:', error);
                    }
                } finally {
                    isSyncing = false;
                }
            }
            
            // Централизованный интервал для полной синхронизации
            // Полная синхронизация каждые 30 секунд (оптимизировано для производительности)
            const FULL_SYNC_INTERVAL = 30000; // 30 секунд
            const autoUpdateInterval = setInterval(() => {
                // Проверяем, что страница видима
                if (document.visibilityState !== 'visible') {
                    return; // Не обновляем, если страница не видна
                }
                
                // Полная синхронизация
                performFullSync();
            }, FULL_SYNC_INTERVAL);
            
            // При возврате на страницу сразу делаем полную синхронизацию
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') {
                    performFullSync();
                } else if (document.visibilityState === 'hidden') {
                    // При скрытии страницы отправляем очередь назначений
                    if (batchTakeQueue.length > 0) {
                        flushBatchTakeQueue();
                    }
                }
            });
            
            // При закрытии страницы отправляем очередь назначений
            window.addEventListener('beforeunload', () => {
                if (batchTakeQueue.length > 0) {
                    // Используем navigator.sendBeacon для надежной отправки при закрытии
                    navigator.sendBeacon('/api/chats/batch-take', JSON.stringify({ chat_ids: batchTakeQueue }));
                }
            });
            
            // Оптимизированное обновление таймеров
            // Используем requestAnimationFrame для плавного обновления только видимых элементов
            let lastTimerUpdate = 0;
            let timerUpdateScheduled = false;
            
            function scheduleTimerUpdate() {
                if (timerUpdateScheduled) return;
                timerUpdateScheduled = true;
                
                requestAnimationFrame(() => {
                    const now = Date.now();
                    if (now - lastTimerUpdate >= TIMER_UPDATE_INTERVAL) {
                        lastTimerUpdate = now;
                        // Обновляем только видимые таймеры для оптимизации
                        updateResponseTimers();
                    }
                    timerUpdateScheduled = false;
                });
            }
            
            // Запускаем обновление таймеров каждые 30 секунд (оптимизировано)
            setInterval(scheduleTimerUpdate, TIMER_UPDATE_INTERVAL);
            
            // ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА через 2 секунды (только если нет кеша)
            if (!cachedChats || cachedChats.length === 0) {
                setTimeout(() => {
                    if (allChats.length === 0 && typeof window.loadChats === 'function') {
                        window.loadChats(true);
                    }
                }, 2000);
            }
        });
        
        // Логирование ошибок
        window.addEventListener('error', function(e) {
            console.error('[GLOBAL ERROR]', e.error, e.message, e.filename, e.lineno);
        });
        
        // Логирование необработанных промисов
        window.addEventListener('unhandledrejection', function(e) {
            console.error('[UNHANDLED PROMISE REJECTION]', e.reason);
        });

        // Функции для работы с модальным окном объявления
        // Загрузка объявления в правую панель
        async function loadListingToSidebar(chatId) {
            console.log('[LISTING SIDEBAR] Загрузка объявления для чата:', chatId);
            const sidebarContent = document.getElementById('listing-sidebar-content');
            if (!sidebarContent) {
                console.error('[LISTING SIDEBAR] Элемент listing-sidebar-content не найден');
                return;
            }
            
            if (!chatId) {
                console.log('[LISTING SIDEBAR] chatId не указан, показываем пустое состояние');
                sidebarContent.innerHTML = `
                    <div class="listing-sidebar-empty">
                        <div class="listing-sidebar-empty-icon">📦</div>
                        <p>Выберите чат, чтобы увидеть объявление</p>
                    </div>
                `;
                return;
            }
            
            // Проверяем, есть ли у чата product_url
            const chat = allChats.find(c => Number(c.id) === chatId);
            if (!chat || !chat.product_url) {
                console.log('[LISTING SIDEBAR] У чата нет product_url, пытаемся извлечь из сообщений...');
                sidebarContent.innerHTML = `
                    <div class="listing-sidebar-empty">
                        <div class="listing-sidebar-empty-icon">⏳</div>
                        <p>Поиск объявления в сообщениях...</p>
                    </div>
                `;
                
                // Автоматически пытаемся извлечь product_url из сообщений
                try {
                    const extractResponse = await fetch(`/api/chats/${chatId}/extract-product-url`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        credentials: 'include'
                    });
                    
                    // Обрабатываем ответ независимо от статуса (200 или 404)
                    let extractData = null;
                    try {
                        extractData = await extractResponse.json();
                    } catch (jsonError) {
                        console.error('[LISTING SIDEBAR] Ошибка парсинга JSON ответа:', jsonError);
                        extractData = { success: false, error: 'Invalid response format' };
                    }
                    
                    if (extractResponse.ok || extractResponse.status === 200) {
                        if (extractData && extractData.success && extractData.product_url) {
                            console.log('[LISTING SIDEBAR] product_url успешно извлечен:', extractData.product_url);
                            // Обновляем chat в allChats
                            if (chat) {
                                chat.product_url = extractData.product_url;
                            }
                            // Обновляем список чатов для получения актуальных данных
                            await loadChats(false, true);
                            // Повторно вызываем loadListingToSidebar с обновленными данными
                            setTimeout(() => loadListingToSidebar(chatId), 500);
                            return;
                        } else {
                            // product_url не найден, но это не ошибка
                            console.log('[LISTING SIDEBAR] product_url не найден в сообщениях:', extractData?.message || extractData?.error || 'Неизвестная причина');
                            sidebarContent.innerHTML = `
                                <div class="listing-sidebar-empty">
                                    <div class="listing-sidebar-empty-icon">📦</div>
                                    <p>У этого чата нет объявления</p>
                                    <p style="font-size: 0.875rem; opacity: 0.7; margin-top: 0.5rem;">Объявление не найдено в сообщениях</p>
                                </div>
                            `;
                            return;
                        }
                    } else if (extractResponse.status === 404) {
                        // Чат не найден или endpoint не существует
                        console.log('[LISTING SIDEBAR] Endpoint не найден или чат не существует:', extractResponse.status);
                        sidebarContent.innerHTML = `
                            <div class="listing-sidebar-empty">
                                <div class="listing-sidebar-empty-icon">📦</div>
                                <p>У этого чата нет объявления</p>
                            </div>
                        `;
                        return;
                    } else {
                        // Другая ошибка сервера
                        console.error('[LISTING SIDEBAR] Ошибка сервера при извлечении product_url:', extractResponse.status, extractData);
                        sidebarContent.innerHTML = `
                            <div class="listing-sidebar-empty">
                                <div class="listing-sidebar-empty-icon">📦</div>
                                <p>У этого чата нет объявления</p>
                                <p style="font-size: 0.875rem; opacity: 0.7; margin-top: 0.5rem;">Ошибка при поиске объявления</p>
                            </div>
                        `;
                        return;
                    }
                } catch (extractError) {
                    console.error('[LISTING SIDEBAR] Ошибка при попытке извлечь product_url:', extractError);
                    sidebarContent.innerHTML = `
                        <div class="listing-sidebar-empty">
                            <div class="listing-sidebar-empty-icon">📦</div>
                            <p>У этого чата нет объявления</p>
                        </div>
                    `;
                    return;
                }
            }
            
            // Показываем загрузку
            sidebarContent.innerHTML = `
                <div class="listing-sidebar-empty">
                    <div class="listing-sidebar-empty-icon">⏳</div>
                    <p>Загрузка объявления...</p>
                </div>
            `;
            
            try {
                console.log('[LISTING SIDEBAR] Запрос к API:', `/api/chats/${chatId}/listing`);
                const response = await fetch(`/api/chats/${chatId}/listing`, {
                    credentials: 'include',
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                console.log('[LISTING SIDEBAR] Ответ от API:', response.status, response.statusText);
                
                let data;
                try {
                    data = await response.json();
                } catch (jsonError) {
                    console.error('[LISTING SIDEBAR] Ошибка парсинга JSON:', jsonError);
                    data = {};
                }
                
                console.log('[LISTING SIDEBAR] Ответ от API:', response.status, data);
                
                // Если есть ошибка, но есть product_url, показываем базовую информацию
                if (!response.ok || data.error) {
                    const errorMessage = data.error || `HTTP ${response.status}`;
                    console.error('[LISTING SIDEBAR] Ошибка API:', errorMessage);
                    
                    // Если есть product_url, пытаемся показать хотя бы ссылку
                    if (data.product_url) {
                        const urlToShow = data.product_url;
                        // Пытаемся извлечь название из URL
                        let title = 'Объявление';
                        try {
                            const urlParts = urlToShow.split('/').filter(p => p);
                            if (urlParts.length > 0) {
                                const lastPart = urlParts[urlParts.length - 1];
                                let extractedTitle = lastPart.replace(/_\d+$/, '');
                                extractedTitle = extractedTitle.replace(/_/g, ' ').replace(/-/g, ' ');
                                extractedTitle = extractedTitle.replace(/\s+/g, ' ').trim();
                                if (extractedTitle.length > 0) {
                                    extractedTitle = extractedTitle.split(' ')
                                        .map(word => {
                                            if (/^\d+/.test(word) || word.length <= 2) {
                                                return word;
                                            }
                                            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
                                        })
                                        .join(' ');
                                    title = extractedTitle.length > 80 ? extractedTitle.substring(0, 80) + '...' : extractedTitle;
                                }
                            }
                        } catch (e) {
                            console.warn('[LISTING SIDEBAR] Ошибка извлечения названия из URL:', e);
                        }
                        
                        sidebarContent.innerHTML = `
                            <div class="listing-card">
                                <h3 class="listing-card-title">${escapeHtml(title)}</h3>
                                <div style="padding: 0.75rem; background: rgba(239, 68, 68, 0.1); border-radius: var(--radius); margin-bottom: 1rem; font-size: 0.875rem; color: #ef4444;">
                                    ⚠️ Не удалось загрузить полные данные объявления
                                </div>
                                <div class="listing-card-actions">
                                    <a href="${escapeHtml(urlToShow)}" target="_blank" rel="noopener noreferrer" class="listing-card-link">Открыть на Avito →</a>
                                </div>
                            </div>
                        `;
                        return;
                    }
                    
                    // Если нет product_url, показываем ошибку
                    sidebarContent.innerHTML = `
                        <div class="listing-sidebar-empty">
                            <div class="listing-sidebar-empty-icon">⚠️</div>
                            <p>${escapeHtml(errorMessage)}</p>
                        </div>
                    `;
                    return;
                }
                
                console.log('[LISTING SIDEBAR] Данные получены:', data);
                console.log('[LISTING SIDEBAR] listing объект:', data.listing);
                console.log('[LISTING SIDEBAR] Ключи в listing:', data.listing ? Object.keys(data.listing) : 'нет listing');
                
                const listing = data.listing || {};
                
                // Улучшенное извлечение изображений
                let images = listing.images || listing.photos || listing.pictures || [];
                // Если images - массив объектов, извлекаем URL
                if (images.length > 0 && typeof images[0] === 'object') {
                    images = images.map(img => 
                        img.url || 
                        img.urls?.large || 
                        img.urls?.medium || 
                        img.urls?.small ||
                        img.full ||
                        img.original ||
                        img.src ||
                        img
                    ).filter(url => url);
                }
                // Если images - массив строк, оставляем как есть
                
                // Улучшенное извлечение данных
                // Если данных нет, пытаемся извлечь из URL или используем значения по умолчанию
                let title = listing.title || listing.name;
                
                // Если title нет, пытаемся извлечь из URL
                if (!title) {
                    const urlToParse = listing.url || data.product_url;
                    if (urlToParse) {
                        try {
                            // Пытаемся извлечь название из URL (последняя часть после последнего слэша)
                            const urlParts = urlToParse.split('/').filter(p => p);
                            if (urlParts.length > 0) {
                                const lastPart = urlParts[urlParts.length - 1];
                                
                                // Убираем ID из конца, если есть (формат: название_1234567890)
                                let extractedTitle = lastPart.replace(/_\d+$/, '');
                                
                                // Заменяем подчеркивания и дефисы на пробелы (ВАЖНО: делаем это ДО других операций)
                                extractedTitle = extractedTitle.replace(/_/g, ' ').replace(/-/g, ' ');
                                
                                // Убираем лишние пробелы
                                extractedTitle = extractedTitle.replace(/\s+/g, ' ').trim();
                                
                                // Улучшаем форматирование: делаем заглавными первые буквы слов
                                if (extractedTitle.length > 0) {
                                    extractedTitle = extractedTitle.split(' ')
                                        .map(word => {
                                            // Пропускаем числа и короткие слова (но не меняем их)
                                            if (/^\d+/.test(word) || word.length <= 2) {
                                                return word;
                                            }
                                            // Делаем первую букву заглавной, остальные строчными
                                            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
                                        })
                                        .join(' ');
                                    
                                    title = extractedTitle;
                                    if (title.length > 80) {
                                        title = title.substring(0, 80) + '...';
                                    }
                                }
                            }
                        } catch (e) {
                            console.warn('[LISTING SIDEBAR] Ошибка извлечения названия из URL:', e);
                        }
                    }
                }
                title = title || 'Объявление';
                
                // Извлекаем цену из различных возможных полей
                let price = listing.price;
                if (price === null || price === undefined || price === '') {
                    // Пробуем извлечь из price_info
                    if (listing.price_info) {
                        if (typeof listing.price_info === 'object') {
                            price = listing.price_info.value || listing.price_info.price;
                        } else {
                            price = listing.price_info;
                        }
                    }
                }
                if (price === null || price === undefined || price === '') {
                    // Пробуем другие варианты
                    price = listing.priceValue || listing.price_value || listing.price_string || 0;
                }
                
                // Если price_string есть, но price нет, пытаемся извлечь число из строки
                if ((price === 0 || price === null || price === undefined) && listing.price_string) {
                    const priceMatch = listing.price_string.toString().match(/(\d[\d\s]*)/);
                    if (priceMatch) {
                        try {
                            price = parseFloat(priceMatch[1].replace(/\s/g, ''));
                        } catch (e) {
                            console.warn('[LISTING SIDEBAR] Ошибка парсинга price_string:', e);
                        }
                    }
                }
                
                // Преобразуем в число
                price = typeof price === 'string' ? parseFloat(price.replace(/\s/g, '')) || 0 : (Number(price) || 0);
                
                const description = listing.description || listing.text || listing.content || '';
                const address = listing.address || listing.location?.name || listing.location?.address || listing.location?.fullName || listing.location?.full_name || '';
                const category = listing.category || {};
                const categoryName = (typeof category === 'object' ? (category.name || category.title || category.label) : category) || '';
                const status = listing.status || listing.state || '';
                
                // Форматируем цену только если она больше 0
                let formattedPrice = '';
                if (price > 0) {
                    formattedPrice = new Intl.NumberFormat('ru-RU', {
                        style: 'currency',
                        currency: 'RUB',
                        minimumFractionDigits: 0
                    }).format(price);
                }
                
                console.log('[LISTING SIDEBAR] Отображаем объявление:', { 
                    title, 
                    price, 
                    formattedPrice,
                    price_string: listing.price_string,
                    price_info: listing.price_info,
                    status, 
                    imagesCount: images.length,
                    hasDescription: !!description,
                    address,
                    categoryName
                });
                
                // Формируем HTML - только самое важное: одно фото, название, цена, ссылка
                const mainImage = images.length > 0 ? images[0] : null;
                const urlToShow = listing.url || data.product_url;
                
                sidebarContent.innerHTML = `
                    <div class="listing-card">
                        ${mainImage ? `<img src="${escapeHtml(mainImage)}" alt="${escapeHtml(title)}" class="listing-card-image" loading="lazy" onerror="this.style.display='none'">` : ''}
                        <h3 class="listing-card-title">${escapeHtml(title)}</h3>
                        ${formattedPrice ? `<div class="listing-card-price">${formattedPrice}</div>` : ''}
                        <div class="listing-card-actions">
                            ${urlToShow ? `<a href="${escapeHtml(urlToShow)}" target="_blank" rel="noopener noreferrer" class="listing-card-link">Открыть на Avito →</a>` : ''}
                        </div>
                    </div>
                `;
            } catch (error) {
                console.error('[LISTING SIDEBAR] Ошибка загрузки:', error);
                sidebarContent.innerHTML = `
                    <div class="listing-sidebar-empty">
                        <div class="listing-sidebar-empty-icon">⚠️</div>
                        <p>Не удалось загрузить объявление</p>
                        <p style="font-size: 0.75rem; margin-top: 0.5rem; color: var(--text-muted);">${escapeHtml(error.message || 'Неизвестная ошибка')}</p>
                    </div>
                `;
            }
        }
        
        // Делаем функцию глобальной для отладки
        window.loadListingToSidebar = loadListingToSidebar;