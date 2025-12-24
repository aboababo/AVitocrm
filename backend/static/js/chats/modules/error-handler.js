/**
 * Error Handler Module
 * Централизованная обработка ошибок
 */

// Глобальный обработчик ошибок
export function initErrorHandling() {
    // Обработка необработанных ошибок
    window.addEventListener('error', (event) => {
        console.error('[GLOBAL ERROR]', event.error || event.message, event.filename, event.lineno);
        
        // Показываем пользователю только критичные ошибки
        if (event.error && event.error.critical) {
            showUserFriendlyError(event.error.message || 'Произошла ошибка');
        }
    });
    
    // Обработка необработанных промисов
    window.addEventListener('unhandledrejection', (event) => {
        console.error('[UNHANDLED PROMISE REJECTION]', event.reason);
        
        // Предотвращаем вывод в консоль по умолчанию
        event.preventDefault();
        
        // Показываем пользователю только важные ошибки
        if (event.reason && typeof event.reason === 'object') {
            const error = event.reason;
            if (error.critical || error.userFacing) {
                showUserFriendlyError(error.message || 'Произошла ошибка при выполнении операции');
            }
        }
    });
}

// Показ пользователю понятного сообщения об ошибке
function showUserFriendlyError(message) {
    // Используем существующую систему уведомлений, если доступна
    if (window.showNotification) {
        window.showNotification(`❌ ${message}`, 'error');
    } else {
        // Fallback: простой alert
        console.error('[USER ERROR]', message);
    }
}

// Обертка для безопасного выполнения функций
export function safeExecute(fn, errorMessage = 'Произошла ошибка') {
    return function(...args) {
        try {
            return fn.apply(this, args);
        } catch (error) {
            console.error('[SAFE EXECUTE]', error);
            showUserFriendlyError(errorMessage);
            return null;
        }
    };
}

// Обертка для безопасного выполнения асинхронных функций
export async function safeExecuteAsync(fn, errorMessage = 'Произошла ошибка') {
    try {
        return await fn();
    } catch (error) {
        console.error('[SAFE EXECUTE ASYNC]', error);
        showUserFriendlyError(errorMessage);
        return null;
    }
}

