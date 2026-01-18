/**
 * Global Search - Petitio
 * Modal de busca global com atalho Ctrl+K
 * Busca em clientes, processos, petições e documentos
 */

(function() {
    'use strict';

    // Estado do componente
    let isOpen = false;
    let selectedIndex = -1;
    let results = [];
    let quickActions = [];
    let searchTimeout = null;
    let modal = null;
    let input = null;
    let resultsContainer = null;

    // Configurações
    const DEBOUNCE_DELAY = 300;
    const MIN_CHARS = 2;

    /**
     * Inicializa o componente de busca global
     */
    function init() {
        createModal();
        bindKeyboardShortcuts();
        loadQuickActions();
    }

    /**
     * Cria o modal de busca no DOM
     */
    function createModal() {
        const modalHtml = `
            <div id="globalSearchModal" class="global-search-modal" role="dialog" aria-modal="true" aria-label="Busca global">
                <div class="global-search-backdrop"></div>
                <div class="global-search-container">
                    <div class="global-search-header">
                        <div class="global-search-input-wrapper">
                            <i class="fas fa-search global-search-icon"></i>
                            <input 
                                type="text" 
                                id="globalSearchInput" 
                                class="global-search-input" 
                                placeholder="Buscar clientes, processos, petições..."
                                autocomplete="off"
                                spellcheck="false"
                            >
                            <kbd class="global-search-kbd">ESC</kbd>
                        </div>
                    </div>
                    <div id="globalSearchResults" class="global-search-results">
                        <!-- Resultados serão inseridos aqui -->
                    </div>
                    <div class="global-search-footer">
                        <div class="global-search-hints">
                            <span><kbd>↑</kbd><kbd>↓</kbd> navegar</span>
                            <span><kbd>Enter</kbd> selecionar</span>
                            <span><kbd>ESC</kbd> fechar</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        modal = document.getElementById('globalSearchModal');
        input = document.getElementById('globalSearchInput');
        resultsContainer = document.getElementById('globalSearchResults');

        // Event listeners
        modal.querySelector('.global-search-backdrop').addEventListener('click', close);
        input.addEventListener('input', handleInput);
        input.addEventListener('keydown', handleKeydown);
    }

    /**
     * Registra atalhos de teclado globais
     */
    function bindKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl+K ou Cmd+K para abrir
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                toggle();
                return;
            }

            // ESC para fechar
            if (e.key === 'Escape' && isOpen) {
                e.preventDefault();
                close();
                return;
            }
        });
    }

    /**
     * Carrega ações rápidas do servidor
     */
    async function loadQuickActions() {
        try {
            const response = await fetch('/api/search/quick-actions', {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            const data = await response.json();
            if (data.success) {
                quickActions = data.actions;
            }
        } catch (error) {
            console.error('Erro ao carregar ações rápidas:', error);
        }
    }

    /**
     * Abre o modal de busca
     */
    function open() {
        if (isOpen) return;
        
        isOpen = true;
        selectedIndex = -1;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Limpar e focar input
        input.value = '';
        input.focus();
        
        // Mostrar ações rápidas
        renderQuickActions();
    }

    /**
     * Fecha o modal de busca
     */
    function close() {
        if (!isOpen) return;
        
        isOpen = false;
        modal.classList.remove('active');
        document.body.style.overflow = '';
        
        // Limpar estado
        input.value = '';
        results = [];
        selectedIndex = -1;
        resultsContainer.innerHTML = '';
    }

    /**
     * Alterna abertura/fechamento
     */
    function toggle() {
        if (isOpen) {
            close();
        } else {
            open();
        }
    }

    /**
     * Handler do input de busca
     */
    function handleInput(e) {
        const query = e.target.value.trim();
        
        // Limpar timeout anterior
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Se vazio, mostrar ações rápidas
        if (!query) {
            renderQuickActions();
            return;
        }

        // Se muito curto, mostrar hint
        if (query.length < MIN_CHARS) {
            resultsContainer.innerHTML = `
                <div class="global-search-hint">
                    <i class="fas fa-keyboard"></i>
                    Digite pelo menos ${MIN_CHARS} caracteres para buscar
                </div>
            `;
            return;
        }

        // Mostrar loading
        resultsContainer.innerHTML = `
            <div class="global-search-loading">
                <i class="fas fa-spinner fa-spin"></i>
                Buscando...
            </div>
        `;

        // Debounce da busca
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, DEBOUNCE_DELAY);
    }

    /**
     * Executa busca no servidor
     */
    async function performSearch(query) {
        try {
            const response = await fetch(`/api/search/global?q=${encodeURIComponent(query)}`, {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                results = data.results;
                selectedIndex = -1;
                renderResults(data.results, query);
            }
        } catch (error) {
            console.error('Erro na busca:', error);
            resultsContainer.innerHTML = `
                <div class="global-search-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    Erro ao buscar. Tente novamente.
                </div>
            `;
        }
    }

    /**
     * Renderiza resultados da busca
     */
    function renderResults(items, query) {
        if (!items.length) {
            resultsContainer.innerHTML = `
                <div class="global-search-empty">
                    <i class="fas fa-search"></i>
                    <p>Nenhum resultado para "<strong>${escapeHtml(query)}</strong>"</p>
                    <small>Tente buscar por nome, número, e-mail ou CPF/CNPJ</small>
                </div>
            `;
            return;
        }

        // Agrupar por tipo
        const grouped = {};
        items.forEach(item => {
            if (!grouped[item.type]) {
                grouped[item.type] = [];
            }
            grouped[item.type].push(item);
        });

        let html = '';
        let globalIndex = 0;

        // Ordem de exibição
        const typeOrder = ['client', 'process', 'petition', 'document'];
        const typeLabels = {
            client: 'Clientes',
            process: 'Processos',
            petition: 'Petições',
            document: 'Documentos'
        };

        typeOrder.forEach(type => {
            if (!grouped[type]) return;

            html += `<div class="global-search-group">
                <div class="global-search-group-title">${typeLabels[type]}</div>`;

            grouped[type].forEach(item => {
                html += createResultItem(item, globalIndex, query);
                globalIndex++;
            });

            html += '</div>';
        });

        resultsContainer.innerHTML = html;

        // Adicionar listeners de click
        resultsContainer.querySelectorAll('.global-search-item').forEach((el, idx) => {
            el.addEventListener('click', () => selectItem(idx));
            el.addEventListener('mouseenter', () => {
                selectedIndex = idx;
                updateSelection();
            });
        });
    }

    /**
     * Renderiza ações rápidas
     */
    function renderQuickActions() {
        if (!quickActions.length) {
            resultsContainer.innerHTML = `
                <div class="global-search-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    Carregando...
                </div>
            `;
            return;
        }

        results = quickActions;
        
        let html = `<div class="global-search-group">
            <div class="global-search-group-title">Ações Rápidas</div>`;

        quickActions.forEach((action, index) => {
            html += `
                <div class="global-search-item ${index === selectedIndex ? 'selected' : ''}" 
                     data-index="${index}" 
                     data-url="${action.url}"
                     ${action.action ? `data-action="${action.action}"` : ''}>
                    <div class="global-search-item-icon action-icon">
                        <i class="fas ${action.icon}"></i>
                    </div>
                    <div class="global-search-item-content">
                        <div class="global-search-item-title">${escapeHtml(action.title)}</div>
                        <div class="global-search-item-subtitle">${escapeHtml(action.subtitle)}</div>
                    </div>
                    ${action.shortcut ? `<kbd class="global-search-item-shortcut">${action.shortcut}</kbd>` : ''}
                </div>
            `;
        });

        html += '</div>';
        resultsContainer.innerHTML = html;

        // Adicionar listeners
        resultsContainer.querySelectorAll('.global-search-item').forEach((el, idx) => {
            el.addEventListener('click', () => selectItem(idx));
            el.addEventListener('mouseenter', () => {
                selectedIndex = idx;
                updateSelection();
            });
        });
    }

    /**
     * Cria HTML de um item de resultado
     */
    function createResultItem(item, index, query) {
        const title = highlightMatch(item.title, query);
        const subtitle = item.subtitle ? highlightMatch(item.subtitle, query) : '';

        return `
            <div class="global-search-item ${index === selectedIndex ? 'selected' : ''}" 
                 data-index="${index}" 
                 data-url="${item.url}">
                <div class="global-search-item-icon type-${item.type}">
                    <i class="fas ${item.icon}"></i>
                </div>
                <div class="global-search-item-content">
                    <div class="global-search-item-title">${title}</div>
                    ${subtitle ? `<div class="global-search-item-subtitle">${subtitle}</div>` : ''}
                </div>
                <span class="global-search-item-badge">${item.type_label}</span>
            </div>
        `;
    }

    /**
     * Destaca o termo buscado no texto
     */
    function highlightMatch(text, query) {
        if (!text || !query) return escapeHtml(text || '');
        
        const escaped = escapeHtml(text);
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return escaped.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Escapa caracteres especiais para regex
     */
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Handler de teclas no input
     */
    function handleKeydown(e) {
        const maxIndex = results.length - 1;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (selectedIndex < maxIndex) {
                    selectedIndex++;
                    updateSelection();
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (selectedIndex > 0) {
                    selectedIndex--;
                    updateSelection();
                }
                break;

            case 'Enter':
                e.preventDefault();
                if (selectedIndex >= 0 && selectedIndex < results.length) {
                    selectItem(selectedIndex);
                }
                break;

            case 'Tab':
                e.preventDefault();
                if (e.shiftKey) {
                    if (selectedIndex > 0) selectedIndex--;
                } else {
                    if (selectedIndex < maxIndex) selectedIndex++;
                }
                updateSelection();
                break;
        }
    }

    /**
     * Atualiza visual da seleção
     */
    function updateSelection() {
        const items = resultsContainer.querySelectorAll('.global-search-item');
        items.forEach((item, idx) => {
            item.classList.toggle('selected', idx === selectedIndex);
        });

        // Scroll into view
        const selected = resultsContainer.querySelector('.global-search-item.selected');
        if (selected) {
            selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }

    /**
     * Seleciona um item e navega
     */
    function selectItem(index) {
        const item = results[index];
        if (!item) return;

        // Verificar se é uma ação especial
        if (item.action) {
            executeAction(item.action);
            close();
            return;
        }

        // Navegar para URL
        if (item.url && item.url !== '#') {
            close();
            window.location.href = item.url;
        }
    }

    /**
     * Executa ação especial
     */
    function executeAction(action) {
        switch (action) {
            case 'openCalculator':
                // Usar função global se existir
                if (typeof window.abrirModal === 'function') {
                    window.abrirModal();
                }
                break;
            default:
                console.warn('Ação desconhecida:', action);
        }
    }

    /**
     * Escapa HTML para prevenir XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Obtém o token CSRF
     */
    function getCsrfToken() {
        // Tentar função global primeiro
        if (typeof window.getCsrfToken === 'function') {
            return window.getCsrfToken();
        }
        // Fallback para meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // API pública
    window.GlobalSearch = {
        open: open,
        close: close,
        toggle: toggle
    };

    // Inicializar quando DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
