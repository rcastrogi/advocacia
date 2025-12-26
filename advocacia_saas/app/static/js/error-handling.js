/**
 * Sistema de tratamento de erros - DELEGADO PARA SISTEMA UNIFICADO
 * Todas as notificações agora passam pelo NotificationSystem
 */

// Interceptador global de fetch para tratamento de erros
if (typeof fetch !== 'undefined') {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args)
            .then(response => {
                // Se a resposta não for ok, mostrar erro
                if (!response.ok && response.status >= 400) {
                    response.clone().text().then(text => {
                        try {
                            const errorData = JSON.parse(text);
                            if (errorData.message) {
                                window.showNotification(errorData.message, 'error');
                            }
                        } catch (e) {
                            // Se não for JSON, mostrar mensagem genérica
                            window.showNotification(`Erro ${response.status}: ${response.statusText}`, 'error');
                        }
                    }).catch(() => {
                        window.showNotification(`Erro ${response.status}: ${response.statusText}`, 'error');
                    });
                }
                return response;
            })
            .catch(error => {
                // Erro de rede
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
    console.log('Toast de sucesso desabilitado:', message);
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
    console.error('Erro não capturado:', event.error || event.message || 'Erro desconhecido');
    
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
    console.error('Promise rejeitada não tratada:', event.reason);
    
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

console.log('✅ Sistema de tratamento de erros iniciado - APENAS LOGGING');
// Não mostra toasts automaticamente para evitar spam ao usuário