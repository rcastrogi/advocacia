/**
 * Sistema de Tutoriais Contextuais - Petitio
 * Fornece ajuda contextual em diferentes páginas e elementos
 */

class ContextualHelpSystem {
    constructor() {
        this.helpDatabase = {};
        this.init();
    }

    init() {
        this.loadHelpDatabase();
        this.addHelpButtons();
        this.setupKeyboardShortcuts();
    }

    loadHelpDatabase() {
        this.helpDatabase = {
            dashboard: {
                'stats-cards': {
                    title: '📊 Estatísticas Gerais',
                    content: `
                        <p>Aqui você encontra um resumo completo das suas atividades no sistema:</p>
                        <ul>
                            <li><strong>Total de Petições:</strong> Número de petições criadas</li>
                            <li><strong>Clientes Ativos:</strong> Clientes com petições ativas</li>
                            <li><strong>Créditos IA:</strong> Saldo disponível para usar a IA</li>
                            <li><strong>Receita Mensal:</strong> Faturamento do período</li>
                        </ul>
                        <p><em>Clique em qualquer card para ver detalhes específicos.</em></p>
                    `,
                    category: 'overview'
                },
                'recent-petitions': {
                    title: '📄 Petições Recentes',
                    content: `
                        <p>Suas últimas petições criadas ou editadas:</p>
                        <ul>
                            <li><strong>Status:</strong> Rascunho, Finalizada, Cancelada</li>
                            <li><strong>Data:</strong> Quando foi criada/modificada</li>
                            <li><strong>Ações:</strong> Visualizar, editar ou excluir</li>
                        </ul>
                        <p><em>Use os filtros para encontrar petições específicas.</em></p>
                    `,
                    category: 'petitions'
                },
                'quick-actions': {
                    title: '⚡ Ações Rápidas',
                    content: `
                        <p>Atalhos para as tarefas mais comuns:</p>
                        <ul>
                            <li><strong>Nova Petição:</strong> Criar petição do zero</li>
                            <li><strong>Usar IA:</strong> Gerar petição com inteligência artificial</li>
                            <li><strong>Modelos:</strong> Usar templates pré-configurados</li>
                        </ul>
                        <p><em>Esses botões levam você diretamente para o peticionador.</em></p>
                    `,
                    category: 'actions'
                }
            },
            peticionador: {
                'tipo-peticao': {
                    title: '📋 Tipos de Petição',
                    content: `
                        <p>Escolha o tipo de petição que deseja criar:</p>
                        <ul>
                            <li><strong>Dinâmicas:</strong> Formulários adaptáveis baseados em seções</li>
                            <li><strong>Modelos:</strong> Templates completos e pré-configurados</li>
                            <li><strong>IA:</strong> Geração automática a partir de descrição</li>
                        </ul>
                        <p><em>Cada tipo oferece uma experiência diferente de criação.</em></p>
                    `,
                    category: 'creation'
                },
                'ia-generator': {
                    title: '🤖 Gerador com IA',
                    content: `
                        <p>Crie petições automaticamente descrevendo o que precisa:</p>
                        <ul>
                            <li><strong>Descrição simples:</strong> "Quero uma ação de divórcio consensual"</li>
                            <li><strong>Detalhes específicos:</strong> Adicione informações do caso</li>
                            <li><strong>Revisão final:</strong> Edite o resultado antes de usar</li>
                        </ul>
                        <p><em>A IA entende linguagem natural e gera petições completas.</em></p>
                    `,
                    category: 'ai'
                },
                'modelos': {
                    title: '📄 Modelos Pré-configurados',
                    content: `
                        <p>Use templates profissionais já estruturados:</p>
                        <ul>
                            <li><strong>Categorias:</strong> Família, Civil, Trabalhista, etc.</li>
                            <li><strong>Atualizados:</strong> Sempre com a legislação mais recente</li>
                            <li><strong>Customizáveis:</strong> Adapte conforme sua necessidade</li>
                        </ul>
                        <p><em>Modelos economizam tempo e garantem qualidade jurídica.</em></p>
                    `,
                    category: 'templates'
                }
            },
            dynamic_form: {
                'sections': {
                    title: '📑 Seções do Formulário',
                    content: `
                        <p>Os formulários são organizados em seções lógicas:</p>
                        <ul>
                            <li><strong>Cabeçalho:</strong> Informações básicas da petição</li>
                            <li><strong>Partes:</strong> Autor, réu e qualificações</li>
                            <li><strong>Fatos:</strong> Descrição do caso</li>
                            <li><strong>Direito:</strong> Fundamentação jurídica</li>
                            <li><strong>Pedidos:</strong> O que está sendo requerido</li>
                        </ul>
                        <p><em>Clique nos títulos para expandir/recolher seções.</em></p>
                    `,
                    category: 'structure'
                },
                'auto-save': {
                    title: '💾 Salvamento Automático',
                    content: `
                        <p>Seus dados são salvos automaticamente:</p>
                        <ul>
                            <li><strong>Tempo real:</strong> A cada mudança significativa</li>
                            <li><strong>Rascunhos:</strong> Acesse depois de qualquer dispositivo</li>
                            <li><strong>Recuperação:</strong> Nunca perca seu trabalho</li>
                        </ul>
                        <p><em>Continue de onde parou a qualquer momento.</em></p>
                    `,
                    category: 'features'
                },
                'validation': {
                    title: '✅ Validação de Campos',
                    content: `
                        <p>O sistema valida seus dados em tempo real:</p>
                        <ul>
                            <li><strong>Obrigatórios:</strong> Campos marcados com * são necessários</li>
                            <li><strong>Formatos:</strong> CPF, CNPJ, datas são validados</li>
                            <li><strong>Consistência:</strong> Verificação lógica dos dados</li>
                        </ul>
                        <p><em>Correções são sugeridas automaticamente.</em></p>
                    `,
                    category: 'validation'
                }
            },
            clients: {
                'client-list': {
                    title: '👥 Lista de Clientes',
                    content: `
                        <p>Gerencie todos os seus clientes:</p>
                        <ul>
                            <li><strong>Busca:</strong> Encontre clientes rapidamente</li>
                            <li><strong>Filtros:</strong> Por status, data de cadastro, etc.</li>
                            <li><strong>Ações:</strong> Editar, ver petições, excluir</li>
                        </ul>
                        <p><em>Mantenha suas informações sempre atualizadas.</em></p>
                    `,
                    category: 'management'
                },
                'add-client': {
                    title: '➕ Adicionar Cliente',
                    content: `
                        <p>Como cadastrar um novo cliente:</p>
                        <ul>
                            <li><strong>Dados básicos:</strong> Nome, documento, contato</li>
                            <li><strong>Endereço:</strong> Completo para petições</li>
                            <li><strong>Observações:</strong> Informações adicionais importantes</li>
                        </ul>
                        <p><em>Dados completos facilitam a criação de petições.</em></p>
                    `,
                    category: 'creation'
                }
            }
        };
    }

    addHelpButtons() {
        // Adicionar botão de ajuda flutuante
        this.createFloatingHelpButton();

        // Adicionar botões de ajuda contextuais em elementos específicos
        this.addContextualHelpButtons();
    }

    createFloatingHelpButton() {
        const helpButton = document.createElement('div');
        helpButton.id = 'floating-help-button';
        helpButton.innerHTML = `
            <button class="btn btn-primary rounded-circle shadow-lg"
                    style="width: 56px; height: 56px; position: fixed; bottom: 24px; right: 24px; z-index: 1050;"
                    onclick="contextualHelp.showHelpMenu()"
                    title="Ajuda e Tutoriais">
                <i class="fas fa-question"></i>
            </button>
        `;

        document.body.appendChild(helpButton);

        // Adicionar estilos
        const style = document.createElement('style');
        style.textContent = `
            #floating-help-button .btn:hover {
                transform: scale(1.1);
                box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important;
            }
            #floating-help-button .btn {
                transition: all 0.3s ease;
            }
        `;
        document.head.appendChild(style);
    }

    addContextualHelpButtons() {
        // Adicionar botões de ajuda em elementos específicos baseado na página atual
        const currentPage = this.getCurrentPage();

        if (this.helpDatabase[currentPage]) {
            Object.keys(this.helpDatabase[currentPage]).forEach(elementKey => {
                const element = document.querySelector(`[data-help="${elementKey}"]`);
                if (element) {
                    this.addHelpIconToElement(element, elementKey);
                }
            });
        }
    }

    addHelpIconToElement(element, helpKey) {
        const helpIcon = document.createElement('span');
        helpIcon.className = 'help-icon ms-2';
        helpIcon.innerHTML = '<i class="fas fa-info-circle text-info" style="cursor: help; font-size: 0.9em;"></i>';
        helpIcon.onclick = (e) => {
            e.stopPropagation();
            this.showHelpTooltip(helpKey);
        };

        element.appendChild(helpIcon);
    }

    showHelpMenu() {
        const currentPage = this.getCurrentPage();
        const pageHelp = this.helpDatabase[currentPage];

        if (!pageHelp) {
            this.showToast('Nenhuma ajuda disponível para esta página', 'info');
            return;
        }

        const helpItems = Object.entries(pageHelp).map(([key, help]) => `
            <button class="list-group-item list-group-item-action d-flex align-items-start"
                    onclick="contextualHelp.showHelpTooltip('${key}')">
                <div class="me-3 mt-1">
                    <i class="fas fa-${this.getCategoryIcon(help.category)} text-primary"></i>
                </div>
                <div class="flex-grow-1">
                    <strong>${help.title}</strong>
                    <p class="mb-0 small text-muted">${this.stripHtml(help.content).substring(0, 100)}...</p>
                </div>
            </button>
        `).join('');

        const modalHtml = `
            <div class="modal fade" id="helpModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-question-circle text-primary me-2"></i>
                                Central de Ajuda
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="text-muted mb-3">Tutoriais e dicas para esta página:</p>
                            <div class="list-group">
                                ${helpItems}
                            </div>
                            <hr>
                            <div class="text-center">
                                <p class="mb-2"><strong>Precisa de mais ajuda?</strong></p>
                                <button class="btn btn-outline-primary me-2" onclick="if(window.petitioTourSystem)window.petitioTourSystem.startTourForCurrentPage()">
                                    <i class="fas fa-route me-1"></i> Fazer Tour Guiado
                                </button>
                                <a href="/roadmap" class="btn btn-outline-info">
                                    <i class="fas fa-road me-1"></i> Ver Roadmap
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('helpModal'));
        modal.show();

        document.getElementById('helpModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('helpModal').remove();
        });
    }

    showHelpTooltip(helpKey) {
        const currentPage = this.getCurrentPage();
        const helpData = this.helpDatabase[currentPage]?.[helpKey];

        if (!helpData) {
            this.showToast('Ajuda não encontrada', 'warning');
            return;
        }

        // Fechar modal de ajuda se estiver aberto
        const helpModal = document.getElementById('helpModal');
        if (helpModal) {
            bootstrap.Modal.getInstance(helpModal)?.hide();
        }

        const modalHtml = `
            <div class="modal fade" id="helpTooltipModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${helpData.title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${helpData.content}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                            <button type="button" class="btn btn-primary" onclick="if(window.petitioTourSystem)window.petitioTourSystem.startTourForCurrentPage()">
                                <i class="fas fa-route me-1"></i> Fazer Tour Completo
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('helpTooltipModal'));
        modal.show();

        document.getElementById('helpTooltipModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('helpTooltipModal').remove();
        });
    }

    getCurrentPage() {
        const path = window.location.pathname;

        if (path.includes('/dashboard')) return 'dashboard';
        if (path.includes('/peticionador')) return 'peticionador';
        if (path.includes('/dynamic-form') || path.includes('/model-form')) return 'dynamic_form';
        if (path.includes('/clients')) return 'clients';

        return 'dashboard'; // fallback
    }

    getCategoryIcon(category) {
        const icons = {
            overview: 'chart-bar',
            petitions: 'file-contract',
            actions: 'bolt',
            creation: 'plus',
            ai: 'robot',
            templates: 'file-alt',
            structure: 'sitemap',
            features: 'star',
            validation: 'check-circle',
            management: 'users'
        };
        return icons[category] || 'info-circle';
    }

    stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }

    showToast(message, type = 'info') {
        if (window.showToast) {
            showToast(message, type);
        } else {
            console.log(`Toast: ${message} (${type})`);
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // F1 para ajuda
            if (e.key === 'F1') {
                e.preventDefault();
                this.showHelpMenu();
            }

            // Ctrl+Shift+T para tour
            if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                if (window.petitioTourSystem) {
                    window.petitioTourSystem.startTourForCurrentPage();
                }
            }
        });
    }
}

// Inicializar sistema de ajuda contextual
document.addEventListener('DOMContentLoaded', () => {
    window.contextualHelp = new ContextualHelpSystem();
});

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextualHelpSystem;
}