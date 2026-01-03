/**
 * Sistema de tratamento de erros - DELEGADO PARA SISTEMA UNIFICADO
 * Todas as notificações agora passam pelo NotificationSystem
 */

// Interceptador global de fetch para tratamento de erros
if (typeof fetch !== 'undefined') {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const [url, options] = args;
        console.log(`[FETCH] ${options?.method || 'GET'} ${url}`);
        
        return originalFetch.apply(this, args)
            .then(response => {
                console.log(`[FETCH-RESPONSE] ${response.status} ${url}`);
                
                // Se a resposta não for ok, mostrar erro
                if (!response.ok && response.status >= 400) {
                    response.clone().text().then(text => {
                        console.error(`[FETCH-ERROR] Status ${response.status}:`, text.substring(0, 200));
                        try {
                            const errorData = JSON.parse(text);
                            if (errorData.message) {
                                console.error('[FETCH-ERROR-MSG]:', errorData.message);
                                window.showNotification(errorData.message, 'error');
                            } else if (errorData.error) {
                                console.error('[FETCH-ERROR-MSG]:', errorData.error);
                                window.showNotification(errorData.error, 'error');
                            }
                        } catch (e) {
                            // Se não for JSON, mostrar mensagem genérica
                            const errorMsg = `Erro ${response.status}: ${response.statusText}`;
                            console.error('[FETCH-ERROR-GENERIC]:', errorMsg);
                            window.showNotification(errorMsg, 'error');
                        }
                    }).catch(err => {
                        console.error('[FETCH-ERROR-PARSE]:', err);
                        window.showNotification(`Erro ${response.status}: ${response.statusText}`, 'error');
                    });
                }
                return response;
            })
            .catch(error => {
                // Erro de rede
                console.error('[FETCH-NETWORK-ERROR]:', error.message || error);
                window.showNotification('Erro de conexão. Verifique sua internet.', 'error');
                throw error;
            });
    };
}

// Funções de compatibilidade - delegam para o sistema unificado
function showErrorToast(message, title = 'Erro') {
    if (window.showNotification) {
        window.showNotification(message, 'error');
    }
}

function showSuccessToast(message, title = 'Sucesso') {
    if (window.showNotification) {
        window.showNotification(message, 'success');
    }
}

// Exportar para uso global
window.showErrorToast = showErrorToast;
window.showSuccessToast = showSuccessToast;

// Função para exibir toast de sucesso - DESABILITADA
function showSuccessToast(message, title = 'Sucesso', duration = 3000) {
    // SISTEMA DESABILITADO PARA EVITAR DUPLICAÇÃO COM FLASH MESSAGES
    return;
    
    // Código original comentado
    /*
    const toastId = 'success-toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast success-toast" role="alert" aria-live="polite" aria-atomic="true" data-bs-delay="${duration}">
            <div class="toast-header bg-success text-white">
                <i class="fas fa-check-circle me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    let container = document.querySelector('.toast-container-errors');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container-errors position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    container.insertAdjacentHTML('beforeend', toastHTML);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
    */
}

// Interceptar fetch global APENAS para erros de rede críticos - DESABILITADO
// Não interceptar erros HTTP que devem ser tratados pela aplicação
// const originalFetch = window.fetch;
// window.fetch = function(...args) {
//     return originalFetch.apply(this, args)
//         .catch(error => {
//             // APENAS erros de rede graves (Failed to fetch, timeout, etc)
//             if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
//                 showErrorToast(
//                     'Não foi possível conectar ao servidor. Verifique sua conexão com a internet.',
//                     'Erro de Conexão'
//                 );
//             }
//             // Re-throw para permitir que a aplicação trate o erro
//             throw error;
//         });
// };

// Interceptor jQuery Ajax DESABILITADO por padrão para evitar toasts duplicados
// Se necessário, use showErrorToast() manualmente no error handler da requisição
// 
// if (typeof jQuery !== 'undefined') {
//     jQuery(document).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
//         // Código desabilitado
//     });
// }

// Listener para erros JavaScript não capturados
window.addEventListener('error', function(event) {
    const errorInfo = {
        message: event.message || 'Erro desconhecido',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
    };
    
    console.error('[ERROR-HANDLER] Erro não capturado:', errorInfo);
    if (event.error && event.error.stack) {
        console.error('[ERROR-HANDLER] Stack:', event.error.stack);
    }
    
    // Não mostrar toast para erros de script externos (ads, analytics, etc)
    if (event.filename && !event.filename.includes(window.location.hostname)) {
        return;
    }
    
    // Em produção, mostrar mensagem genérica
    if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
        showErrorToast(
            'Ocorreu um erro inesperado. Por favor, recarregue a página.',
            'Erro',
            7000
        );
    }
});

// Listener para promessas rejeitadas não tratadas
window.addEventListener('unhandledrejection', function(event) {
    console.error('[UNHANDLED-REJECTION] Promise rejeitada:', {
        reason: event.reason,
        promise: event.promise
    });
    
    // Log detalhado
    if (event.reason) {
        if (event.reason.message) {
            console.error('[UNHANDLED-REJECTION] Message:', event.reason.message);
        }
        if (event.reason.stack) {
            console.error('[UNHANDLED-REJECTION] Stack:', event.reason.stack);
        }
    }
    
    // Em produção, mostrar mensagem genérica
    if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
        showErrorToast(
            'Ocorreu um erro inesperado. Por favor, tente novamente.',
            'Erro'
        );
    }
});

// Exportar funções para uso global
window.showErrorToast = showErrorToast;
window.showSuccessToast = showSuccessToast;

// Não mostra toasts automaticamente para evitar spam ao usuário