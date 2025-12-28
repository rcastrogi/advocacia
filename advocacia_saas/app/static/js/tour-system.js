/**
 * Sistema de Tours Guiados - Petitio
 * Implementa tours interativos usando Intro.js
 */

class TourSystem {
    constructor() {
        this.currentTour = null;
        this.tours = {};
        this.init();
    }

    init() {
        // Registrar tours disponíveis
        this.registerTours();

        // Adicionar botão de tour ao menu do usuário se estiver logado
        this.addTourButtonToMenu();

        // Verificar se deve mostrar tour de boas-vindas para novos usuários
        this.checkFirstTimeUser();
    }

    registerTours() {
        // Tour do Dashboard
        this.tours.dashboard = {
            steps: [
                {
                    element: '.navbar-brand',
                    intro: 'Bem-vindo ao Petitio! Este é o seu sistema de gestão jurídica completo.',
                    position: 'bottom'
                },
                {
                    element: '[href*="dashboard"]',
                    intro: 'O Dashboard mostra um resumo das suas atividades e estatísticas importantes.',
                    position: 'bottom'
                },
                {
                    element: '[href*="peticionador"]',
                    intro: 'Aqui você pode criar novas petições usando IA ou modelos pré-configurados.',
                    position: 'bottom'
                },
                {
                    element: '[href*="saved_list"]',
                    intro: 'Acesse todas as suas petições salvas e continue editando quando precisar.',
                    position: 'bottom'
                },
                {
                    element: '[href*="clients"]',
                    intro: 'Gerencie seus clientes e mantenha todas as informações organizadas.',
                    position: 'bottom'
                },
                {
                    element: '[href*="notifications"]',
                    intro: 'Fique por dentro das notificações importantes do sistema.',
                    position: 'left'
                },
                {
                    element: '[href*="credits_dashboard"]',
                    intro: 'Monitore seus créditos de IA disponíveis para gerar petições.',
                    position: 'left'
                }
            ]
        };

        // Tour do Peticionador
        this.tours.peticionador = {
            steps: [
                {
                    element: '.page-header',
                    intro: 'Página do Peticionador - Aqui você cria suas petições de forma inteligente.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="tipo-peticao"]',
                    intro: 'Escolha o tipo de petição que deseja criar. Temos diversos modelos disponíveis.',
                    position: 'right'
                },
                {
                    element: '[data-tour="ia-generator"]',
                    intro: 'Use nossa IA para gerar petições automaticamente a partir de uma descrição simples.',
                    position: 'right'
                },
                {
                    element: '[data-tour="modelos"]',
                    intro: 'Ou utilize nossos modelos pré-configurados para agilizar o processo.',
                    position: 'right'
                }
            ]
        };

        // Tour de Formulário Dinâmico
        this.tours.dynamic_form = {
            steps: [
                {
                    element: '.section-card:first-child',
                    intro: 'Os formulários são organizados em seções para facilitar o preenchimento.',
                    position: 'right'
                },
                {
                    element: '.section-header',
                    intro: 'Clique nos cabeçalhos para expandir ou recolher as seções.',
                    position: 'right'
                },
                {
                    element: 'button[type="submit"]',
                    intro: 'Após preencher todos os campos obrigatórios, clique aqui para gerar sua petição.',
                    position: 'top'
                },
                {
                    element: '.auto-save-indicator',
                    intro: 'Seus dados são salvos automaticamente, então não precisa se preocupar em perder o progresso.',
                    position: 'left'
                }
            ]
        };
    }

    startTour(tourName) {
        if (!this.tours[tourName]) {
            console.warn(`Tour "${tourName}" não encontrado`);
            return;
        }

        // Fechar tour anterior se existir
        if (this.currentTour) {
            this.currentTour.exit();
        }

        const tourConfig = this.tours[tourName];

        this.currentTour = introJs()
            .setOptions({
                steps: tourConfig.steps,
                showProgress: true,
                showBullets: true,
                exitOnOverlayClick: true,
                exitOnEsc: true,
                nextLabel: 'Próximo',
                prevLabel: 'Anterior',
                skipLabel: 'Pular',
                doneLabel: 'Concluir',
                hidePrev: false,
                hideNext: false,
                tooltipClass: 'custom-intro-tooltip',
                highlightClass: 'custom-intro-highlight',
                showStepNumbers: true,
                keyboardNavigation: true,
                scrollToElement: true,
                overlayOpacity: 0.7,
                disableInteraction: false
            })
            .oncomplete(() => {
                this.showTourCompletedToast(tourName);
                this.markTourAsCompleted(tourName);
            })
            .onexit(() => {
                this.currentTour = null;
            })
            .start();
    }

    addTourButtonToMenu() {
        // Aguardar o DOM estar pronto
        document.addEventListener('DOMContentLoaded', () => {
            const dropdownMenu = document.querySelector('#navbarDropdown + .dropdown-menu');
            if (dropdownMenu) {
                // Adicionar item de tour antes do separador
                const tourItem = document.createElement('li');
                tourItem.innerHTML = `
                    <a class="dropdown-item" href="#" onclick="tourSystem.showTourMenu(); return false;">
                        <i class="fas fa-route"></i> Tour Guiado
                    </a>
                `;

                // Inserir antes do primeiro <li><hr> encontrado
                const hrElements = dropdownMenu.querySelectorAll('li:has(hr)');
                if (hrElements.length > 0) {
                    dropdownMenu.insertBefore(tourItem, hrElements[0]);
                } else {
                    // Fallback: adicionar no final
                    dropdownMenu.appendChild(tourItem);
                }
            }
        });
    }

    showTourMenu() {
        // Criar modal com opções de tour
        const modalHtml = `
            <div class="modal fade" id="tourModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-route text-primary me-2"></i>
                                Tour Guiado do Sistema
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="text-muted mb-3">Escolha qual tour você gostaria de fazer:</p>
                            <div class="list-group">
                                <button class="list-group-item list-group-item-action d-flex align-items-center"
                                        onclick="tourSystem.startTour('dashboard')">
                                    <i class="fas fa-tachometer-alt text-primary me-3"></i>
                                    <div>
                                        <strong>Dashboard</strong>
                                        <br><small class="text-muted">Conheça a página inicial e navegação principal</small>
                                    </div>
                                </button>
                                <button class="list-group-item list-group-item-action d-flex align-items-center"
                                        onclick="tourSystem.startTour('peticionador')">
                                    <i class="fas fa-file-contract text-success me-3"></i>
                                    <div>
                                        <strong>Peticionador</strong>
                                        <br><small class="text-muted">Aprenda a criar petições com IA e modelos</small>
                                    </div>
                                </button>
                                <button class="list-group-item list-group-item-action d-flex align-items-center"
                                        onclick="tourSystem.startTour('dynamic_form')">
                                    <i class="fas fa-edit text-info me-3"></i>
                                    <div>
                                        <strong>Formulários</strong>
                                        <br><small class="text-muted">Entenda como preencher os formulários dinâmicos</small>
                                    </div>
                                </button>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Adicionar modal ao body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('tourModal'));
        modal.show();

        // Remover modal do DOM quando fechada
        document.getElementById('tourModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('tourModal').remove();
        });
    }

    checkFirstTimeUser() {
        // Verificar se é a primeira vez do usuário (localStorage)
        const hasSeenWelcome = localStorage.getItem('petitio_welcome_tour_shown');
        if (!hasSeenWelcome && window.location.pathname.includes('dashboard')) {
            // Aguardar um pouco para garantir que a página carregou
            setTimeout(() => {
                this.showWelcomeDialog();
            }, 2000);
        }
    }

    showWelcomeDialog() {
        const dialogHtml = `
            <div class="modal fade" id="welcomeModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-star text-warning me-2"></i>
                                Bem-vindo ao Petitio!
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-4">
                                <i class="fas fa-rocket text-primary" style="font-size: 4rem;"></i>
                            </div>
                            <h4>Seu sistema de gestão jurídica inteligente</h4>
                            <p class="text-muted mb-4">
                                Criamos um tour rápido para te apresentar as principais funcionalidades.
                                Vamos começar?
                            </p>
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <div class="card h-100 border-primary">
                                        <div class="card-body text-center">
                                            <i class="fas fa-route text-primary mb-2" style="font-size: 2rem;"></i>
                                            <h6>Fazer Tour Agora</h6>
                                            <p class="small text-muted">5 minutos para conhecer tudo</p>
                                            <button class="btn btn-primary btn-sm" onclick="tourSystem.startTour('dashboard'); document.getElementById('welcomeModal').querySelector('[data-bs-dismiss=modal]').click();">
                                                Começar Tour
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="card h-100 border-secondary">
                                        <div class="card-body text-center">
                                            <i class="fas fa-play text-secondary mb-2" style="font-size: 2rem;"></i>
                                            <h6>Explorar Sozinho</h6>
                                            <p class="small text-muted">Descobrir por conta própria</p>
                                            <button class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">
                                                Explorar Agora
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <small class="text-muted">
                                Você pode refazer este tour a qualquer momento através do menu do usuário.
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        const modal = new bootstrap.Modal(document.getElementById('welcomeModal'));
        modal.show();

        // Marcar como visto quando fechar
        document.getElementById('welcomeModal').addEventListener('hidden.bs.modal', () => {
            localStorage.setItem('petitio_welcome_tour_shown', 'true');
            document.getElementById('welcomeModal').remove();
        });
    }

    showTourCompletedToast(tourName) {
        // Usar o sistema de toast existente
        if (window.showToast) {
            const tourNames = {
                dashboard: 'Dashboard',
                peticionador: 'Peticionador',
                dynamic_form: 'Formulários'
            };

            showToast(`Tour de ${tourNames[tourName] || tourName} concluído! 🎉`, 'success');
        }
    }

    markTourAsCompleted(tourName) {
        const completedTours = JSON.parse(localStorage.getItem('petitio_completed_tours') || '[]');
        if (!completedTours.includes(tourName)) {
            completedTours.push(tourName);
            localStorage.setItem('petitio_completed_tours', JSON.stringify(completedTours));
        }
    }

    // Método para mostrar tutoriais contextuais em páginas específicas
    showContextualHelp(page, element) {
        const helpContent = this.getContextualHelp(page, element);
        if (helpContent) {
            this.showTooltipHelp(element, helpContent);
        }
    }

    getContextualHelp(page, element) {
        const helpDatabase = {
            dashboard: {
                'stats-cards': {
                    title: 'Estatísticas Gerais',
                    content: 'Aqui você vê um resumo das suas atividades: petições criadas, clientes ativos e uso de IA.'
                },
                'recent-petitions': {
                    title: 'Petições Recentes',
                    content: 'Suas últimas petições criadas. Clique em uma para visualizar ou continuar editando.'
                }
            },
            peticionador: {
                'tipo-peticao': {
                    title: 'Tipos de Petição',
                    content: 'Escolha o tipo de petição que deseja criar. Cada tipo tem seu próprio conjunto de campos.'
                },
                'ia-generator': {
                    title: 'Gerador com IA',
                    content: 'Descreva o que precisa em linguagem natural e nossa IA criará uma petição completa para você.'
                }
            }
        };

        return helpDatabase[page]?.[element];
    }

    showTooltipHelp(element, helpData) {
        // Criar tooltip personalizado
        const tooltipHtml = `
            <div class="help-tooltip">
                <div class="help-tooltip-header">
                    <strong>${helpData.title}</strong>
                    <button class="btn-close btn-close-white btn-sm" onclick="this.closest('.help-tooltip').remove()"></button>
                </div>
                <div class="help-tooltip-body">
                    ${helpData.content}
                </div>
            </div>
        `;

        const targetElement = document.querySelector(element);
        if (targetElement) {
            targetElement.style.position = 'relative';
            targetElement.insertAdjacentHTML('beforeend', tooltipHtml);
        }
    }
}

// Inicializar sistema de tours quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.tourSystem = new TourSystem();
});

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TourSystem;
}