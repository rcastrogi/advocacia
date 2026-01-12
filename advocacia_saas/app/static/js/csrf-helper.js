/**
 * CSRF Token Helper - Proteção automática contra CSRF em requisições AJAX
 * Este script deve ser carregado após debug-console.js e antes de outros scripts
 * 
 * Funcionalidades:
 * 1. getCsrfToken() - Obtém o token CSRF da página
 * 2. Adiciona automaticamente X-CSRFToken em todas as requisições não-GET
 * 3. Configura jQuery AJAX (se presente) com CSRF token
 */

(function() {
    'use strict';

    // =========================================================================
    // FUNÇÃO GLOBAL PARA OBTER CSRF TOKEN
    // =========================================================================
    window.getCsrfToken = function() {
        // Primeiro tenta obter da meta tag (mais seguro e padronizado)
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        // Fallback: busca em input hidden (formulários Flask-WTF)
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            return csrfInput.value;
        }

        // Último fallback: cookie (se estiver configurado)
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return decodeURIComponent(value);
            }
        }

        console.warn('[CSRF] Token não encontrado na página');
        return '';
    };

    // =========================================================================
    // INTERCEPTOR DE FETCH - ADICIONA CSRF TOKEN AUTOMATICAMENTE
    // =========================================================================
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options = {}) {
        // Inicializa options se não existir
        options = options || {};
        options.headers = options.headers || {};

        // Converte Headers object para plain object se necessário
        if (options.headers instanceof Headers) {
            const headerObj = {};
            options.headers.forEach((value, key) => {
                headerObj[key] = value;
            });
            options.headers = headerObj;
        }

        // Métodos que precisam de CSRF token
        const methodsRequiringCSRF = ['POST', 'PUT', 'PATCH', 'DELETE'];
        const method = (options.method || 'GET').toUpperCase();

        // Adiciona CSRF token apenas para métodos que modificam dados
        if (methodsRequiringCSRF.includes(method)) {
            // Não sobrescreve se já foi definido manualmente
            if (!options.headers['X-CSRFToken'] && !options.headers['X-CSRF-Token']) {
                const csrfToken = window.getCsrfToken();
                if (csrfToken) {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
            }
        }

        return originalFetch.call(this, url, options);
    };

    // =========================================================================
    // CONFIGURAÇÃO DO JQUERY AJAX (SE DISPONÍVEL)
    // =========================================================================
    function setupJQueryCSRF() {
        if (typeof jQuery !== 'undefined' || typeof $ !== 'undefined') {
            const jq = jQuery || $;
            
            // Configura header padrão para todas as requisições AJAX do jQuery
            jq.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    // Métodos que não precisam de CSRF
                    const safeMethodsRegex = /^(GET|HEAD|OPTIONS|TRACE)$/i;
                    
                    if (!safeMethodsRegex.test(settings.type) && !this.crossDomain) {
                        const csrfToken = window.getCsrfToken();
                        if (csrfToken) {
                            xhr.setRequestHeader('X-CSRFToken', csrfToken);
                        }
                    }
                }
            });

            console.log('[CSRF] jQuery AJAX configurado com proteção CSRF');
        }
    }

    // =========================================================================
    // CONFIGURAÇÃO DO HTMX (SE DISPONÍVEL)
    // =========================================================================
    function setupHtmxCSRF() {
        // HTMX é configurado via evento ou atributo no HTML
        // Verifica se existe e adiciona o header
        document.addEventListener('htmx:configRequest', function(event) {
            const csrfToken = window.getCsrfToken();
            if (csrfToken) {
                event.detail.headers['X-CSRFToken'] = csrfToken;
            }
        });
    }

    // =========================================================================
    // INICIALIZAÇÃO
    // =========================================================================
    function init() {
        // Setup jQuery quando estiver disponível
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                setupJQueryCSRF();
                setupHtmxCSRF();
            });
        } else {
            setupJQueryCSRF();
            setupHtmxCSRF();
        }

        console.log('[CSRF] Helper inicializado - Todas as requisições POST/PUT/DELETE terão proteção CSRF automática');
    }

    init();
})();
