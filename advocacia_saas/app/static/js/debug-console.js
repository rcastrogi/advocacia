/**
 * Enhanced Debug Console - Para identificar exatamente qual erro está ocorrendo
 * Coloque este script ANTES de todos os outros scripts
 */

// 1. Capturar TODOS os console.log, warn, error
const originalLog = console.log;
const originalWarn = console.warn;
const originalError = console.error;

window.DEBUG_LOGS = [];

console.log = function(...args) {
    window.DEBUG_LOGS.push({ type: 'LOG', time: new Date().toISOString(), args });
    originalLog.apply(console, args);
};

console.warn = function(...args) {
    window.DEBUG_LOGS.push({ type: 'WARN', time: new Date().toISOString(), args });
    originalWarn.apply(console, args);
};

console.error = function(...args) {
    window.DEBUG_LOGS.push({ type: 'ERROR', time: new Date().toISOString(), args });
    originalError.apply(console, args);
};

// 2. Capturar TODOS os fetch/XMLHttpRequest
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const [url, options] = args;
    const requestId = Math.random().toString(36).substr(2, 9);
    const method = options?.method || 'GET';
    
    console.log(`[FETCH-${requestId}] ${method} ${url}`);
    
    return originalFetch.apply(this, args)
        .then(response => {
            console.log(`[FETCH-${requestId}] Response ${response.status} ${url}`);
            
            // Clone para ler o body
            return response.clone().text().then(text => {
                if (response.status >= 400) {
                    console.error(`[FETCH-${requestId}] Error body:`, text.substring(0, 500));
                }
                // Retornar response original
                return new Response(text, {
                    status: response.status,
                    statusText: response.statusText,
                    headers: response.headers
                });
            });
        })
        .catch(error => {
            console.error(`[FETCH-${requestId}] Network error:`, error.message);
            throw error;
        });
};

// 3. Capturar XMLHttpRequest também
const originalOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    console.log(`[XHR] ${method} ${url}`);
    
    const originalOnreadystatechange = this.onreadystatechange;
    this.onreadystatechange = function() {
        if (this.readyState === 4) {
            console.log(`[XHR] Response ${this.status} ${url}`);
        }
        if (originalOnreadystatechange) {
            originalOnreadystatechange.apply(this, arguments);
        }
    };
    
    return originalOpen.apply(this, [method, url, ...rest]);
};

// 4. Capturar unhandledrejection com detalhes
window.addEventListener('unhandledrejection', event => {
    console.error('[UNHANDLED-REJECTION]', {
        reason: event.reason,
        message: event.reason?.message,
        stack: event.reason?.stack
    });
});

// 5. Criar função para visualizar todos os logs
window.showAllLogs = function() {
    console.group('=== ALL DEBUG LOGS ===');
    window.DEBUG_LOGS.forEach(log => {
        console.log(`[${log.time}] ${log.type}:`, ...log.args);
    });
    console.groupEnd();
};

// 6. Log de inicialização
console.log('[DEBUG-CONSOLE] Enhanced debug console initialized');
console.log('[DEBUG-CONSOLE] Call window.showAllLogs() to see all logs');
