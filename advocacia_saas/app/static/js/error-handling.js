/**
 * Sistema global de tratamento de erros para requisições Ajax/Fetch
 * Exibe toasts amigáveis ao invés de erros técnicos
 */

// Função para exibir toast de erro
function showErrorToast(message, title = 'Erro', duration = 5000) {
    // Criar elemento de toast
    const toastId = 'error-toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast error-toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${duration}">
            <div class="toast-header bg-danger text-white">
                <i class="fas fa-exclamation-circle me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Adicionar ao container de toasts
    let container = document.querySelector('.toast-container-errors');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container-errors position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    container.insertAdjacentHTML('beforeend', toastHTML);
    
    // Inicializar e mostrar toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remover do DOM após esconder
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Função para exibir toast de sucesso
function showSuccessToast(message, title = 'Sucesso', duration = 3000) {
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
}

// Interceptar fetch global para tratar erros
const originalFetch = window.fetch;
window.fetch = function(...args) {
    return originalFetch.apply(this, args)
        .then(response => {
            // Se resposta não for OK e for JSON, tentar pegar mensagem de erro
            if (!response.ok && response.headers.get('content-type')?.includes('application/json')) {
                return response.json().then(data => {
                    const errorMessage = data.error || data.message || 'Ocorreu um erro na requisição';
                    showErrorToast(errorMessage);
                    throw new Error(errorMessage);
                });
            }
            return response;
        })
        .catch(error => {
            // Erros de rede
            if (error.message === 'Failed to fetch') {
                showErrorToast(
                    'Não foi possível conectar ao servidor. Verifique sua conexão com a internet.',
                    'Erro de Conexão'
                );
            } else if (!error.message.includes('requisição')) {
                // Só mostrar se não for erro já tratado
                showErrorToast(error.message || 'Erro desconhecido');
            }
            throw error;
        });
};

// Interceptar jQuery Ajax se estiver disponível
if (typeof jQuery !== 'undefined') {
    jQuery(document).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
        let errorMessage = 'Ocorreu um erro na requisição';
        
        // Tentar pegar mensagem do JSON de resposta
        try {
            const response = JSON.parse(jqXHR.responseText);
            errorMessage = response.error || response.message || errorMessage;
        } catch (e) {
            // Se não for JSON, usar mensagem padrão por código de status
            switch (jqXHR.status) {
                case 400:
                    errorMessage = 'Requisição inválida. Verifique os dados enviados.';
                    break;
                case 401:
                    errorMessage = 'Sua sessão expirou. Por favor, faça login novamente.';
                    setTimeout(() => window.location.href = '/auth/login', 2000);
                    break;
                case 403:
                    errorMessage = 'Você não tem permissão para realizar esta ação.';
                    break;
                case 404:
                    errorMessage = 'Recurso não encontrado.';
                    break;
                case 429:
                    errorMessage = 'Muitas tentativas. Por favor, aguarde alguns minutos.';
                    break;
                case 500:
                    errorMessage = 'Erro interno do servidor. Nossa equipe foi notificada.';
                    break;
                case 503:
                    errorMessage = 'Serviço temporariamente indisponível. Tente novamente em breve.';
                    break;
                default:
                    if (jqXHR.status === 0) {
                        errorMessage = 'Não foi possível conectar ao servidor. Verifique sua conexão.';
                    }
            }
        }
        
        showErrorToast(errorMessage);
    });
}

// Listener para erros JavaScript não capturados
window.addEventListener('error', function(event) {
    console.error('Erro não capturado:', event.error);
    
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

console.log('✅ Sistema de tratamento de erros inicializado');
