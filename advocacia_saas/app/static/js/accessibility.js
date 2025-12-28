/**
 * Acessibilidade - Recursos para deficientes visuais
 * WCAG 2.1 Level AA compliance
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== 1. CONTROLE DE TAMANHO DE FONTE =====
    const fontSizes = {
        small: 0.875,
        normal: 1,
        large: 1.25,
        xlarge: 1.5
    };
    
    let currentFontSize = localStorage.getItem('fontSize') || 'normal';
    applyFontSize(currentFontSize);
    
    function applyFontSize(size) {
        document.documentElement.style.fontSize = (fontSizes[size] * 16) + 'px';
        currentFontSize = size;
        localStorage.setItem('fontSize', size);
        
        // Atualizar botões ativos
        document.querySelectorAll('[data-font-size]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.fontSize === size);
        });
    }
    
    // Event listeners para botões de fonte
    document.querySelectorAll('[data-font-size]').forEach(btn => {
        btn.addEventListener('click', function() {
            applyFontSize(this.dataset.fontSize);
            announceToScreenReader('Tamanho da fonte alterado para ' + this.dataset.fontSize);
        });
    });
    
    
    // ===== 2. MODO DE ALTO CONTRASTE =====
    let highContrast = localStorage.getItem('highContrast') === 'true';
    applyHighContrast(highContrast);
    
    function applyHighContrast(enabled) {
        highContrast = enabled;
        document.body.classList.toggle('high-contrast', enabled);
        localStorage.setItem('highContrast', enabled);
        
        const btn = document.getElementById('toggleContrast');
        if (btn) {
            btn.setAttribute('aria-pressed', enabled);
            btn.innerHTML = enabled ? 
                '<i class="fas fa-adjust"></i> Contraste Normal' : 
                '<i class="fas fa-adjust"></i> Alto Contraste';
        }
        
        announceToScreenReader(enabled ? 'Alto contraste ativado' : 'Alto contraste desativado');
    }
    
    const contrastBtn = document.getElementById('toggleContrast');
    if (contrastBtn) {
        contrastBtn.addEventListener('click', function() {
            applyHighContrast(!highContrast);
        });
    }
    
    
    // ===== 3. SKIP LINK - PULAR PARA CONTEÚDO =====
    const skipLink = document.getElementById('skip-to-content');
    if (skipLink) {
        skipLink.addEventListener('click', function(e) {
            e.preventDefault();
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.tabIndex = -1;
                mainContent.focus();
                mainContent.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    
    // ===== 4. NAVEGAÇÃO POR TECLADO MELHORADA =====
    
    // ESC para fechar modais
    document.addEventListener('keydown', function(e) {
        if (!e.key || typeof e.key !== 'string' || e.key.length === 0) return;
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
    
    // Trap focus em modais
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const focusableElements = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            if (firstElement) {
                firstElement.focus();
            }
            
            modal.addEventListener('keydown', function(e) {
                if (!e.key || typeof e.key !== 'string' || e.key.length === 0) return;
                if (e.key === 'Tab') {
                    if (e.shiftKey && document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    } else if (!e.shiftKey && document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                }
            });
        });
    });
    
    
    // ===== 5. INDICADORES DE FOCO VISÍVEIS =====
    
    // Adicionar classe quando navegando por teclado
    let isUsingKeyboard = false;
    
    document.addEventListener('keydown', function(e) {
        if (!e.key || typeof e.key !== 'string' || e.key.length === 0) return;
        if (e.key === 'Tab') {
            isUsingKeyboard = true;
            document.body.classList.add('keyboard-navigation');
        }
    });
    
    document.addEventListener('mousedown', function() {
        isUsingKeyboard = false;
        document.body.classList.remove('keyboard-navigation');
    });
    
    
    // ===== 6. ANÚNCIOS PARA SCREEN READERS =====
    
    function announceToScreenReader(message) {
        const announcement = document.getElementById('screen-reader-announcements');
        if (announcement) {
            announcement.textContent = message;
            
            // Limpar após 3 segundos
            setTimeout(() => {
                announcement.textContent = '';
            }, 3000);
        }
    }
    
    // Anunciar mensagens de sucesso/erro
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        const message = alert.textContent.trim();
        if (message) {
            announceToScreenReader(message);
        }
    });
    
    
    // ===== 7. MELHORAR LABELS DE FORMULÁRIOS =====
    
    // Adicionar aria-required em campos obrigatórios
    document.querySelectorAll('input[required], select[required], textarea[required]').forEach(field => {
        field.setAttribute('aria-required', 'true');
    });
    
    // Adicionar aria-invalid em campos com erro
    document.querySelectorAll('.is-invalid').forEach(field => {
        field.setAttribute('aria-invalid', 'true');
        
        const errorMsg = field.nextElementSibling;
        if (errorMsg && errorMsg.classList.contains('invalid-feedback') && field.id) {
            const errorId = 'error-' + field.id;
            errorMsg.id = errorId;
            field.setAttribute('aria-describedby', errorId);
        }
    });
    
    
    // ===== 8. ATALHOS DE TECLADO =====
    
    const shortcuts = {
        'Alt+1': () => window.location.href = '/',
        'Alt+2': () => {
            const dashboardLink = document.querySelector('a[href*="dashboard"]');
            if (dashboardLink) dashboardLink.click();
        },
        'Alt+3': () => {
            const clientsLink = document.querySelector('a[href*="clients"]');
            if (clientsLink) clientsLink.click();
        },
        'Alt+H': () => showShortcutsHelp()
    };
    
    document.addEventListener('keydown', function(e) {
        if (!e.key || typeof e.key !== 'string' || e.key.length === 0) return; // Prevent error if key is undefined, not a string, or empty
        
        const key = (e.altKey ? 'Alt+' : '') + e.key.toUpperCase();
        
        if (shortcuts[key]) {
            e.preventDefault();
            shortcuts[key]();
        }
    });
    
    function showShortcutsHelp() {
        const helpText = `
            Atalhos de Teclado:
            Alt+1 - Ir para página inicial
            Alt+2 - Ir para dashboard
            Alt+3 - Ir para clientes
            Alt+H - Mostrar esta ajuda
        `;
        announceToScreenReader(helpText);
        alert(helpText);
    }
    
    
    // ===== 9. MELHORAR TABELAS =====
    
    document.querySelectorAll('table').forEach(table => {
        // Adicionar role se não tiver
        if (!table.getAttribute('role')) {
            table.setAttribute('role', 'table');
        }
        
        // Adicionar caption se não tiver
        if (!table.querySelector('caption') && table.querySelector('thead')) {
            const caption = document.createElement('caption');
            caption.className = 'visually-hidden';
            caption.textContent = 'Tabela de dados';
            table.insertBefore(caption, table.firstChild);
        }
        
        // Adicionar scope nos headers
        table.querySelectorAll('th').forEach(th => {
            if (!th.getAttribute('scope')) {
                th.setAttribute('scope', 'col');
            }
        });
    });
    
    
    // ===== 10. LOADING STATES ACESSÍVEIS =====
    
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        announceToScreenReader('Carregando...');
        
        return originalFetch.apply(this, args).then(response => {
            if (response.ok) {
                announceToScreenReader('Carregamento concluído');
            } else {
                announceToScreenReader('Erro no carregamento');
            }
            return response;
        });
    };
    
    
});
