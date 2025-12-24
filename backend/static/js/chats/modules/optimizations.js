/**
 * Оптимизации производительности
 * Виртуализация, lazy loading, и другие оптимизации
 */

import * as state from './state.js';

// Виртуализация списка чатов (показываем только видимые элементы)
export class VirtualizedList {
    constructor(container, itemHeight = 120, overscan = 5) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.overscan = overscan;
        this.scrollTop = 0;
        this.containerHeight = 0;
        this.visibleStart = 0;
        this.visibleEnd = 0;
        
        this.init();
    }
    
    init() {
        if (!this.container) return;
        
        this.containerHeight = this.container.clientHeight;
        this.updateVisibleRange();
        
        this.container.addEventListener('scroll', () => {
            this.scrollTop = this.container.scrollTop;
            this.updateVisibleRange();
        });
        
        // Обновляем при изменении размера
        const resizeObserver = new ResizeObserver(() => {
            this.containerHeight = this.container.clientHeight;
            this.updateVisibleRange();
        });
        resizeObserver.observe(this.container);
    }
    
    updateVisibleRange() {
        const start = Math.floor(this.scrollTop / this.itemHeight);
        const end = Math.ceil((this.scrollTop + this.containerHeight) / this.itemHeight);
        
        // Получаем актуальный список чатов из state
        const chats = state.filteredChats || [];
        this.visibleStart = Math.max(0, start - this.overscan);
        this.visibleEnd = Math.min(chats.length, end + this.overscan);
    }
    
    getVisibleItems() {
        const chats = state.filteredChats || [];
        return chats.slice(this.visibleStart, this.visibleEnd);
    }
    
    getOffsetY() {
        return this.visibleStart * this.itemHeight;
    }
    
    getTotalHeight() {
        const chats = state.filteredChats || [];
        return chats.length * this.itemHeight;
    }
}

// Lazy loading для изображений
export function setupLazyLoading() {
    if (!('IntersectionObserver' in window)) {
        // Fallback для старых браузеров
        document.querySelectorAll('img[data-src]').forEach(img => {
            if (img.dataset.src) {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
            }
        });
        return;
    }
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    img.setAttribute('loading', 'lazy');
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '50px', // Загружаем за 50px до появления
        threshold: 0.01
    });
    
    // Наблюдаем за всеми изображениями с data-src
    const images = document.querySelectorAll('img[data-src]');
    images.forEach(img => {
        imageObserver.observe(img);
    });
    
    // Сохраняем observer для последующего использования
    window._imageObserver = imageObserver;
}

// Оптимизация скролла с requestAnimationFrame
export function optimizeScroll(container, callback) {
    let ticking = false;
    
    container.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                callback();
                ticking = false;
            });
            ticking = true;
        }
    });
}

// Debounce для частых операций
export function debounce(func, wait) {
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

// Throttle для частых операций
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Мемоизация для тяжелых вычислений
const memoCache = new Map();
export function memoize(fn, keyFn) {
    return function(...args) {
        const key = keyFn ? keyFn(...args) : JSON.stringify(args);
        if (memoCache.has(key)) {
            return memoCache.get(key);
        }
        const result = fn(...args);
        memoCache.set(key, result);
        
        // Ограничиваем размер кеша
        if (memoCache.size > 100) {
            const firstKey = memoCache.keys().next().value;
            memoCache.delete(firstKey);
        }
        
        return result;
    };
}

// Оптимизация рендеринга с использованием DocumentFragment
export function renderWithFragment(items, renderFn) {
    const fragment = document.createDocumentFragment();
    items.forEach(item => {
        const element = renderFn(item);
        if (element) {
            fragment.appendChild(element);
        }
    });
    return fragment;
}

// Batch DOM updates
export function batchDOMUpdates(updates) {
    // Используем requestAnimationFrame для батчинга обновлений
    requestAnimationFrame(() => {
        updates.forEach(update => update());
    });
}

// Preload критичных ресурсов
export function preloadCriticalResources() {
    // Preload шрифты, если используются
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'font';
    link.crossOrigin = 'anonymous';
    // Добавьте URL шрифта если нужно
    // document.head.appendChild(link);
}

// Оптимизация производительности при скролле
export function setupSmoothScrolling() {
    // Используем CSS scroll-behavior: smooth для плавного скролла
    const style = document.createElement('style');
    style.textContent = `
        .chats-scroll,
        .messages-view {
            scroll-behavior: smooth;
        }
        
        @media (prefers-reduced-motion: reduce) {
            .chats-scroll,
            .messages-view {
                scroll-behavior: auto;
            }
        }
    `;
    document.head.appendChild(style);
}

// Инициализация всех оптимизаций
export function initOptimizations() {
    try {
        setupLazyLoading();
        setupSmoothScrolling();
        preloadCriticalResources();
        
        // Наблюдаем за изменениями в DOM для lazy loading новых изображений
        if ('MutationObserver' in window) {
            const observer = new MutationObserver((mutations) => {
                // Проверяем, есть ли новые изображения
                let hasNewImages = false;
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) { // Element node
                            if (node.tagName === 'IMG' && node.dataset.src) {
                                hasNewImages = true;
                            } else if (node.querySelectorAll) {
                                const imgs = node.querySelectorAll('img[data-src]');
                                if (imgs.length > 0) {
                                    hasNewImages = true;
                                }
                            }
                        }
                    });
                });
                
                if (hasNewImages && window._imageObserver) {
                    // Наблюдаем за новыми изображениями
                    document.querySelectorAll('img[data-src]').forEach(img => {
                        if (!img._observed) {
                            window._imageObserver.observe(img);
                            img._observed = true;
                        }
                    });
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    } catch (error) {
        console.warn('[OPTIMIZATIONS] Ошибка при инициализации оптимизаций:', error);
    }
}

