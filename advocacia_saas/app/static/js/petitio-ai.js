/**
 * Módulo de geração de conteúdo com IA para Petitio
 * Adiciona botões de geração IA nos campos do editor de petições
 */

const PetitioAI = {
    // Estado
    userCredits: 0,
    isUnlimited: false,  // true para usuários master
    isLoading: false,
    creditCosts: {
        section: 1,
        improve: 1,
        full_petition: 5,
        fundamentos: 3,
        analyze: 3
    },

    // Inicialização
    async init() {
        await this.fetchCreditsBalance();
        this.injectAIButtons();
        this.setupEventListeners();
    },

    // Busca saldo de créditos
    async fetchCreditsBalance() {
        try {
            const response = await fetch('/ai/api/credits/balance');
            const data = await response.json();
            if (data.success) {
                this.isUnlimited = data.is_unlimited || false;
                this.userCredits = data.is_unlimited ? Infinity : data.balance;
                this.updateCreditsDisplay();
            }
        } catch (error) {
            console.error('Erro ao buscar saldo:', error);
        }
    },

    // Atualiza exibição de créditos
    updateCreditsDisplay() {
        const badge = document.getElementById('ai-credits-badge');
        if (badge) {
            if (this.isUnlimited) {
                badge.textContent = '∞ créditos';
                badge.className = 'badge bg-success';
            } else {
                badge.textContent = `${this.userCredits} créditos`;
                badge.className = `badge ${this.userCredits > 0 ? 'bg-success' : 'bg-warning text-dark'}`;
            }
        }
        
        // Atualiza também o badge da navbar
        const navbarBadge = document.getElementById('navbar-credits-badge');
        if (navbarBadge) {
            navbarBadge.textContent = this.isUnlimited ? '∞' : this.userCredits;
        }
    },

    // Injeta botões de IA nos campos do editor
    injectAIButtons() {
        // Verifica se estamos em um formulário dinâmico (que já tem toolbars Alpine.js)
        const isDynamicForm = document.querySelector('[x-data*="dynamicPetitionForm"]') ||
                             document.querySelector('[x-data*="modelPetitionForm"]');

        if (isDynamicForm) {
            console.log('PetitioAI: Formulário dinâmico detectado, pulando injeção automática');
            return;
        }

        // Verifica se já existem toolbars de IA do sistema Alpine.js
        const existingToolbars = document.querySelectorAll('.ai-toolbar[x-show]');
        if (existingToolbars.length > 0) {
            console.log('PetitioAI: Toolbars Alpine.js já existem, pulando injeção automática');
            return;
        }

        const editorFields = document.querySelectorAll('.quill-wrapper');

        editorFields.forEach(wrapper => {
            const editorId = wrapper.querySelector('.quill-editor')?.id;
            if (!editorId) return;

            const fieldName = editorId.replace('quill_', '');
            const sectionType = this.detectSectionType(fieldName);

            if (sectionType) {
                this.createAIToolbar(wrapper, fieldName, sectionType);
            }
        });

        // Adiciona badge de créditos no topo (somente se não for ilimitado)
        if (!this.isUnlimited) {
            this.createCreditsIndicator();
        }
    },

    // Detecta o tipo de seção pelo nome do campo
    detectSectionType(fieldName) {
        const lowerName = fieldName.toLowerCase();
        
        if (lowerName.includes('fato') || lowerName.includes('fact')) {
            return 'fatos';
        }
        if (lowerName.includes('direito') || lowerName.includes('fundament') || lowerName.includes('argument')) {
            return 'direito';
        }
        if (lowerName.includes('pedido') || lowerName.includes('request') || lowerName.includes('requerimento')) {
            return 'pedidos';
        }
        if (lowerName.includes('conclus')) {
            return 'conclusao';
        }
        
        // Campos genéricos também podem usar IA
        return 'generico';
    },

    // Cria barra de ferramentas IA para um campo
    createAIToolbar(wrapper, fieldName, sectionType) {
        const toolbar = document.createElement('div');
        toolbar.className = 'ai-toolbar d-flex gap-2 mb-2 flex-wrap';
        toolbar.innerHTML = `
            <button type="button" 
                    class="btn btn-sm btn-outline-primary ai-btn" 
                    data-action="generate"
                    data-field="${fieldName}"
                    data-section="${sectionType}"
                    title="Gerar conteúdo com IA (1 crédito)">
                <i class="bi bi-stars me-1"></i>Gerar com IA
            </button>
            <button type="button" 
                    class="btn btn-sm btn-outline-secondary ai-btn"
                    data-action="improve"
                    data-field="${fieldName}"
                    data-section="${sectionType}"
                    title="Melhorar texto existente (1 crédito)">
                <i class="bi bi-magic me-1"></i>Melhorar
            </button>
            <span class="text-muted small d-flex align-items-center ms-auto">
                <i class="bi bi-info-circle me-1"></i>
                ${this.getSectionDescription(sectionType)}
            </span>
        `;
        
        // Insere antes do wrapper do editor
        wrapper.parentNode.insertBefore(toolbar, wrapper);
    },

    // Cria indicador de créditos no formulário
    createCreditsIndicator() {
        const formHeader = document.querySelector('.card-header') || document.querySelector('h1');
        if (!formHeader) return;

        const indicator = document.createElement('div');
        indicator.className = 'ai-credits-indicator mb-3';
        indicator.innerHTML = `
            <div class="alert alert-light border d-flex align-items-center justify-content-between py-2">
                <div>
                    <i class="bi bi-robot text-primary me-2"></i>
                    <strong>Geração com IA</strong>
                    <span class="text-muted ms-2">Use inteligência artificial para criar e melhorar suas petições</span>
                </div>
                <div>
                    <span id="ai-credits-badge" class="badge ${this.userCredits > 0 ? 'bg-success' : 'bg-warning text-dark'}">
                        ${this.userCredits} créditos
                    </span>
                    <a href="/ai/credits" class="btn btn-sm btn-outline-success ms-2">
                        <i class="bi bi-plus-circle me-1"></i>Comprar
                    </a>
                </div>
            </div>
        `;

        // Insere após o header do card ou após o h1
        const targetParent = formHeader.closest('.card-body') || formHeader.parentNode;
        if (targetParent) {
            targetParent.insertBefore(indicator, targetParent.firstChild);
        }
    },

    // Descrição por tipo de seção
    getSectionDescription(sectionType) {
        const descriptions = {
            'fatos': 'Narração dos fatos relevantes',
            'direito': 'Fundamentação jurídica',
            'pedidos': 'Pedidos e requerimentos',
            'conclusao': 'Conclusão da petição',
            'generico': 'Conteúdo jurídico'
        };
        return descriptions[sectionType] || '';
    },

    // Event listeners
    setupEventListeners() {
        document.addEventListener('click', async (e) => {
            const btn = e.target.closest('.ai-btn');
            if (!btn) return;

            const action = btn.dataset.action;
            const fieldName = btn.dataset.field;
            const sectionType = btn.dataset.section;

            if (action === 'generate') {
                await this.generateContent(fieldName, sectionType, btn);
            } else if (action === 'improve') {
                await this.improveContent(fieldName, btn);
            }
        });
    },

    // Obtém contexto do formulário
    getFormContext() {
        const context = {};
        
        // Coleta dados dos campos de texto
        document.querySelectorAll('input[type="text"], select, textarea').forEach(field => {
            if (field.name && field.value) {
                context[field.name] = field.value;
            }
        });

        // Coleta dados dos editores Quill (se Alpine disponível)
        if (window.Alpine) {
            const alpineData = Alpine.$data(document.querySelector('[x-data]'));
            if (alpineData && alpineData.formData) {
                Object.assign(context, alpineData.formData);
            }
        }

        return context;
    },

    // Obtém conteúdo de um campo Quill
    getFieldContent(fieldName) {
        const editorId = `quill_${fieldName}`;
        const editorEl = document.getElementById(editorId);
        
        if (editorEl && editorEl.__quill) {
            return editorEl.__quill.root.innerHTML;
        }
        
        // Fallback: tentar via Alpine
        if (window.Alpine) {
            const alpineData = Alpine.$data(document.querySelector('[x-data]'));
            if (alpineData && alpineData.formData) {
                return alpineData.formData[fieldName] || '';
            }
        }
        
        return '';
    },

    // Define conteúdo em um campo Quill
    setFieldContent(fieldName, content) {
        const editorId = `quill_${fieldName}`;
        const editorEl = document.getElementById(editorId);
        
        if (editorEl && editorEl.__quill) {
            editorEl.__quill.root.innerHTML = content;
            // Dispara evento de mudança
            editorEl.__quill.root.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        // Atualiza também via Alpine se disponível
        if (window.Alpine) {
            const alpineEl = document.querySelector('[x-data]');
            if (alpineEl) {
                const alpineData = Alpine.$data(alpineEl);
                if (alpineData && alpineData.formData) {
                    alpineData.formData[fieldName] = content;
                }
            }
        }
    },

    // Gera conteúdo para uma seção
    async generateContent(fieldName, sectionType, btn) {
        if (this.isLoading) return;
        
        // Verifica créditos (usuários ilimitados sempre têm)
        if (!this.isUnlimited && this.userCredits < this.creditCosts.section) {
            this.showInsufficientCredits();
            return;
        }

        const existingContent = this.getFieldContent(fieldName);
        
        // Confirmação se já tem conteúdo
        if (existingContent && existingContent.length > 50) {
            if (!confirm('Este campo já tem conteúdo. Deseja substituir pelo conteúdo gerado?')) {
                return;
            }
        }

        this.isLoading = true;
        this.setButtonLoading(btn, true);

        try {
            const context = this.getFormContext();
            const petitionType = document.querySelector('[name="tipo_peticao"]')?.value || 
                                window.location.pathname.split('/').pop() || '';

            const response = await fetch('/ai/api/generate/section', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    section_type: sectionType,
                    petition_type: petitionType,
                    context: context,
                    existing_content: existingContent,
                    premium: false
                })
            });

            const data = await response.json();

            if (data.success) {
                this.setFieldContent(fieldName, data.content);
                // Atualiza créditos (pode ser string '∞' ou número)
                if (data.credits_remaining !== '∞') {
                    this.userCredits = data.credits_remaining;
                }
                this.updateCreditsDisplay();
                const creditMsg = this.isUnlimited ? '' : ` (${data.credits_used} crédito usado)`;
                this.showSuccess(`Conteúdo gerado!${creditMsg}`);
            } else {
                if (response.status === 402) {
                    this.showInsufficientCredits();
                } else {
                    this.showError(data.error || 'Erro ao gerar conteúdo');
                }
            }
        } catch (error) {
            console.error('Erro:', error);
            this.showError('Erro de conexão. Tente novamente.');
        } finally {
            this.isLoading = false;
            this.setButtonLoading(btn, false);
        }
    },

    // Melhora conteúdo existente
    async improveContent(fieldName, btn) {
        if (this.isLoading) return;

        const existingContent = this.getFieldContent(fieldName);
        
        if (!existingContent || existingContent.length < 20) {
            this.showWarning('Digite algum conteúdo primeiro para poder melhorar.');
            return;
        }

        // Verifica créditos (usuários ilimitados sempre têm)
        if (!this.isUnlimited && this.userCredits < this.creditCosts.improve) {
            this.showInsufficientCredits();
            return;
        }

        this.isLoading = true;
        this.setButtonLoading(btn, true);

        try {
            const context = this.getFormContext();
            
            const response = await fetch('/ai/api/generate/improve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: existingContent,
                    context: JSON.stringify(context),
                    premium: false
                })
            });

            const data = await response.json();

            if (data.success) {
                this.setFieldContent(fieldName, data.content);
                // Atualiza créditos (pode ser string '∞' ou número)
                if (data.credits_remaining !== '∞') {
                    this.userCredits = data.credits_remaining;
                }
                this.updateCreditsDisplay();
                const creditMsg = this.isUnlimited ? '' : ` (${data.credits_used} crédito usado)`;
                this.showSuccess(`Texto melhorado!${creditMsg}`);
            } else {
                if (response.status === 402) {
                    this.showInsufficientCredits();
                } else {
                    this.showError(data.error || 'Erro ao melhorar texto');
                }
            }
        } catch (error) {
            console.error('Erro:', error);
            this.showError('Erro de conexão. Tente novamente.');
        } finally {
            this.isLoading = false;
            this.setButtonLoading(btn, false);
        }
    },

    // UI Helpers
    setButtonLoading(btn, loading) {
        if (loading) {
            btn.disabled = true;
            btn.dataset.originalHtml = btn.innerHTML;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Gerando...';
        } else {
            btn.disabled = false;
            btn.innerHTML = btn.dataset.originalHtml;
        }
    },

    showSuccess(message) {
        this.showToast(message, 'success');
    },

    showError(message) {
        this.showToast(message, 'danger');
    },

    showWarning(message) {
        this.showToast(message, 'warning');
    },

    showInsufficientCredits() {
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div class="modal fade" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header border-0">
                            <h5 class="modal-title">
                                <i class="bi bi-coin text-warning me-2"></i>Créditos Insuficientes
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center py-4">
                            <div class="display-1 text-warning mb-3">
                                <i class="bi bi-wallet2"></i>
                            </div>
                            <p class="mb-1">Você tem apenas <strong>${this.userCredits}</strong> créditos.</p>
                            <p class="text-muted">Adquira mais créditos para continuar usando a IA.</p>
                        </div>
                        <div class="modal-footer border-0 justify-content-center">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                            <a href="/ai/credits" class="btn btn-success">
                                <i class="bi bi-cart-plus me-2"></i>Comprar Créditos
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal.querySelector('.modal'));
        bsModal.show();
        
        modal.querySelector('.modal').addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    },

    showToast(message, type = 'info') {
        // DELEGADO PARA SISTEMA UNIFICADO DE NOTIFICAÇÕES
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
        }
    }
};

// Inicializa quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    // Aguarda um pouco para garantir que Quill foi inicializado
    setTimeout(() => {
        PetitioAI.init();
    }, 500);
});
