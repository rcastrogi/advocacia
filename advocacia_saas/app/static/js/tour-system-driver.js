/**
 * Sistema de Tours Guiados - Petitio
 * Implementa tours interativos usando Driver.js (visual melhorado)
 */

class TourSystem {
    constructor() {
        this.currentDriver = null;
        this.tours = {};
        this.driverAttempts = 0;
        this.maxDriverAttempts = 10; // Máximo 10 tentativas (5 segundos)
        this.init();
    }

    init() {
        // Registrar tours disponíveis
        this.registerTours();

        // Verificar se Driver.js foi carregado
        this.checkDriverAvailability();

        // Adicionar botão de tour ao menu do usuário se estiver logado
        this.addTourButtonToMenu();

        // Verificar se deve mostrar tour de boas-vindas para novos usuários
        this.checkFirstTimeUser();
    }

    checkDriverAvailability() {
        // Verificar se Driver.js está disponível (API: window.driver.js.driver)
        const isAvailable = window.driver && window.driver.js && typeof window.driver.js.driver === 'function';
        if (!isAvailable) {
            console.warn('⚠️ Driver.js não foi detectado. Aguardando carregamento...');
            // Esperar um tempo maior para o Driver.js carregar
            setTimeout(() => {
                const loaded = window.driver && window.driver.js && typeof window.driver.js.driver === 'function';
                if (loaded) {
                    console.log('✅ Driver.js carregado com sucesso!');
                } else {
                    console.error('❌ Falha ao carregar Driver.js. Tours não estarão disponíveis.');
                }
            }, 3000);
        } else {
            console.log('✅ Driver.js detectado!');
        }
    }

    registerTours() {
        // Tours para Advogados/Escritórios - Dashboard Principal
        this.tours.lawyer_dashboard = {
            steps: [
                {
                    element: '[data-tour="main-header"]',
                    popover: {
                        title: '👋 Bem-vindo ao Petitio!',
                        description: 'Sistema completo de gestão jurídica inteligente. Aqui você gerencia clientes, petições e prazos em um único lugar.',
                        side: 'bottom',
                        align: 'start'
                    }
                },
                {
                    element: '[data-tour="quick-actions"]',
                    popover: {
                        title: '⚡ Ações Rápidas',
                        description: 'Acesse os recursos mais usados: criar petição com IA, adicionar novo cliente, visualizar processos e muito mais.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="stats-petitions"]',
                    popover: {
                        title: '📄 Petições IA',
                        description: 'Visualize quantas petições você criou este mês. Ilimitadas ou com limite conforme seu plano de assinatura.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="stats-clients"]',
                    popover: {
                        title: '👥 Seus Clientes',
                        description: 'Total de clientes cadastrados no sistema. Clique para gerenciar, editar dados e consultar histórico.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="stats-ai-credits"]',
                    popover: {
                        title: '🤖 Créditos de IA',
                        description: 'Acompanhe seu saldo de créditos de inteligência artificial para geração automática de petições.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="recent-petitions"]',
                    popover: {
                        title: '📋 Petições Recentes',
                        description: 'Acesse rapidamente suas petições mais recentes. Clique para editar, visualizar ou converter em documento.',
                        side: 'left'
                    }
                },
                {
                    element: '[data-tour="your-plan"]',
                    popover: {
                        title: '💳 Seu Plano',
                        description: 'Visualize seu plano atual, benefícios inclusos, limite de petições e data de renovação da assinatura.',
                        side: 'left'
                    }
                }
            ]
        };

        // Tours para Administradores (Master)
        this.tours.admin_dashboard = {
            steps: [
                {
                    element: '.navbar-brand',
                    popover: {
                        title: '🛡️ Painel Administrativo',
                        description: 'Você está no painel de administração do sistema Petitio. Aqui você gerencia toda a plataforma.',
                        side: 'bottom',
                        align: 'start'
                    }
                },
                {
                    element: '[href*="admin/usuarios"]',
                    popover: {
                        title: '👨‍💼 Gerenciar Usuários',
                        description: 'Visualize, edite, ative/desative e gerencie todos os usuários do sistema. Altere permissões e planos.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="admin/petitions"]',
                    popover: {
                        title: '⚙️ Tipos e Modelos',
                        description: 'Configure os tipos de petições, edite modelos, adicione seções customizadas e gerencie templates.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="admin/roadmap"]',
                    popover: {
                        title: '🗺️ Roadmap & Feedback',
                        description: 'Gerencie o roadmap de features, analise feedback dos usuários e priorize desenvolvimentos.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="billing"]',
                    popover: {
                        title: '💰 Planos de Cobrança',
                        description: 'Configure os planos de assinatura, limites, preços e gerencie faturamento da plataforma.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="admin/logs"]',
                    popover: {
                        title: '📊 Logs do Sistema',
                        description: 'Monitore atividades, erros e eventos do sistema em tempo real para debugging e análise.',
                        side: 'bottom'
                    }
                }
            ]
        };

        // Tours para Processos
        this.tours.processes_dashboard = {
            steps: [
                {
                    element: '[data-tour="urgent-deadlines"]',
                    popover: {
                        title: '⚠️ Prazos Urgentes',
                        description: 'Processos com prazos próximos de vencer aparecem aqui. Monitore cuidadosamente para não perder prazos.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="notifications"]',
                    popover: {
                        title: '🔔 Notificações',
                        description: 'Receba alertas automáticos sobre movimentações processuais e prazos importantes do seu calendário.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="quick-actions"]',
                    popover: {
                        title: '⚡ Ações Rápidas',
                        description: 'Acesse rapidamente as funcionalidades mais usadas: criar processo, adicionar prazo, enviar petição.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="recent-processes"]',
                    popover: {
                        title: '📁 Processos Recentes',
                        description: 'Seus últimos processos acessados aparecem aqui. Clique para retomar o trabalho rapidamente.',
                        side: 'left'
                    }
                },
                {
                    element: '[data-tour="pending-petitions"]',
                    popover: {
                        title: '📋 Petições Pendentes',
                        description: 'Petições já criadas mas que ainda não foram vinculadas a nenhum processo. Complete a vinculação aqui.',
                        side: 'left'
                    }
                },
                {
                    element: '[data-tour="status-distribution"]',
                    popover: {
                        title: '📊 Distribuição de Status',
                        description: 'Visualize a distribuição dos seus processos por status (ativo, encerrado, suspenso, etc).',
                        side: 'left'
                    }
                }
            ]
        };

        // Tours para Clientes
        this.tours.clients_list = {
            steps: [
                {
                    element: '[data-tour="clients-header"]',
                    popover: {
                        title: 'Meus Clientes',
                        description: 'Aqui você gerencia todos os seus clientes cadastrados.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="add-client-btn"]',
                    popover: {
                        title: 'Adicionar Cliente',
                        description: 'Clique aqui para cadastrar um novo cliente no sistema.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="clients-search"]',
                    popover: {
                        title: 'Buscar Clientes',
                        description: 'Use a busca para encontrar rapidamente um cliente.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="clients-table"]',
                    popover: {
                        title: 'Lista de Clientes',
                        description: 'Visualize todos os seus clientes com CPF, email e telefone.',
                        side: 'top'
                    }
                }
            ]
        };

        // Tours para Petições
        this.tours.petitions_form = {
            steps: [
                {
                    element: '[data-tour="petition-type"]',
                    popover: {
                        title: 'Tipo de Petição',
                        description: 'Escolha o tipo de petição que deseja criar.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="petition-client"]',
                    popover: {
                        title: 'Selecione o Cliente',
                        description: 'Escolha para qual cliente esta petição será criada.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="petition-ai-button"]',
                    popover: {
                        title: 'Gerar com IA',
                        description: 'Use IA para gerar automaticamente o conteúdo da petição.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="petition-editor"]',
                    popover: {
                        title: 'Editor de Petição',
                        description: 'Edite o conteúdo da sua petição aqui. Use as ferramentas de formatação acima.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="petition-save"]',
                    popover: {
                        title: 'Salvar Petição',
                        description: 'Clique para salvar sua petição. Você pode continuar editando depois.',
                        side: 'bottom'
                    }
                }
            ]
        };

        // Tours para Billing
        this.tours.billing_portal = {
            steps: [
                {
                    element: '[data-tour="current-plan"]',
                    popover: {
                        title: 'Seu Plano Atual',
                        description: 'Visualize detalhes do seu plano de assinatura.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="plan-features"]',
                    popover: {
                        title: 'Benefícios do Plano',
                        description: 'Veja quais benefícios estão inclusos em seu plano.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="upgrade-button"]',
                    popover: {
                        title: 'Upgrade de Plano',
                        description: 'Clique aqui para fazer upgrade para um plano melhor.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="payment-history"]',
                    popover: {
                        title: 'Histórico de Pagamentos',
                        description: 'Visualize todos os seus pagamentos anteriores.',
                        side: 'top'
                    }
                }
            ]
        };

        // Tours para Reports
        this.tours.reports = {
            steps: [
                {
                    element: '[data-tour="date-filters"]',
                    popover: {
                        title: 'Filtros de Data',
                        description: 'Selecione o período que deseja analisar nos seus relatórios.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="status-distribution-report"]',
                    popover: {
                        title: 'Distribuição de Status',
                        description: 'Visualize quantos processos você tem em cada status.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="monthly-creation-report"]',
                    popover: {
                        title: 'Criações Mensais',
                        description: 'Veja quantos processos foram criados por mês.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="court-distribution-report"]',
                    popover: {
                        title: 'Distribuição por Tribunal',
                        description: 'Veja como seus processos estão distribuídos por tribunal.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="report-results"]',
                    popover: {
                        title: 'Resultado dos Relatórios',
                        description: 'Os gráficos e dados dos seus relatórios aparecerão aqui.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="export-report"]',
                    popover: {
                        title: 'Exportar Relatório',
                        description: 'Clique para baixar o relatório em PDF ou Excel.',
                        side: 'bottom'
                    }
                }
            ]
        };
    }

    addTourButtonToMenu() {
        // Adicionar botão de "Iniciar Tour" ao menu do usuário
        const userMenu = document.querySelector('[data-bs-toggle="dropdown"]');
        if (!userMenu) return;

        // Criar botão de tour
        const tourBtn = document.createElement('a');
        tourBtn.href = '#';
        tourBtn.className = 'dropdown-item';
        tourBtn.innerHTML = '<i class="fas fa-graduation-cap me-2"></i>Ver Tour';
        tourBtn.onclick = (e) => {
            e.preventDefault();
            this.startTourForCurrentPage();
        };

        // Inserir após o primeiro dropdown-item
        const firstItem = userMenu.nextElementSibling?.querySelector('.dropdown-item');
        if (firstItem) {
            firstItem.parentElement.insertBefore(tourBtn, firstItem.nextElementSibling);
        }
    }

    startTourForCurrentPage() {
        // Detectar qual página estamos e iniciar tour apropriado
        const url = window.location.href.toLowerCase();
        let tourName = null;

        if (url.includes('/admin')) {
            tourName = 'admin_dashboard';
        } else if (url.includes('/processes')) {
            tourName = 'processes_dashboard';
        } else if (url.includes('/dashboard')) {
            tourName = 'lawyer_dashboard';
        }

        if (tourName && this.tours[tourName]) {
            this.startTour(tourName);
        } else {
            console.log('Nenhum tour disponível para esta página');
        }
    }

    startTour(tourName) {
        if (!this.tours[tourName]) {
            console.error(`Tour "${tourName}" não encontrado`);
            return;
        }

        // Verificar se Driver.js está disponível (API: window.driver.js.driver)
        const isDriverAvailable = window.driver && window.driver.js && typeof window.driver.js.driver === 'function';
        if (!isDriverAvailable) {
            // Limitar tentativas para evitar loop infinito
            if (this.driverAttempts >= this.maxDriverAttempts) {
                console.error('❌ Driver.js não conseguiu carregar após várias tentativas. Tours desabilitados.');
                return;
            }
            
            this.driverAttempts++;
            console.warn(`⏳ Driver.js não foi carregado (tentativa ${this.driverAttempts}/${this.maxDriverAttempts}). Tentando novamente em 500ms...`);
            setTimeout(() => this.startTour(tourName), 500);
            return;
        }

        // Reset contador se conseguiu carregar
        this.driverAttempts = 0;

        const steps = this.tours[tourName].steps;

        this.currentDriver = window.driver.js.driver({
            steps: steps,
            popoverClass: 'driver-popover',
            nextBtnText: 'Próximo →',
            prevBtnText: '← Anterior',
            doneBtnText: 'Concluído',
            progressText: 'Passo %current% de %total%',
            showProgress: true,
            showButtons: true,
            allowClose: true,
            stageBackground: 'rgba(0, 0, 0, 0.5)',
            onHighlighted: (element) => {
                // Scroll do elemento para o viewport se necessário
                element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });

        this.currentDriver.drive();
    }

    checkFirstTimeUser() {
        // Verificar se é o primeiro acesso
        const hasSeenTour = localStorage.getItem('petitio_tour_seen');
        if (!hasSeenTour && document.querySelector('[href*="dashboard"]')) {
            // Aguardar Driver.js estar disponível antes de mostrar tour
            let attempts = 0;
            const maxAttempts = 20; // 2 segundos (20 * 100ms)
            
            const waitForDriver = () => {
                const isReady = window.driver && window.driver.js && typeof window.driver.js.driver === 'function';
                if (isReady) {
                    // Mostrar tour de boas-vindas após 2 segundos
                    setTimeout(() => {
                        this.startTourForCurrentPage();
                    }, 2000);
                    localStorage.setItem('petitio_tour_seen', 'true');
                } else if (attempts < maxAttempts) {
                    attempts++;
                    // Tentar novamente em 100ms
                    setTimeout(waitForDriver, 100);
                } else {
                    console.warn('⚠️ Driver.js não foi carregado. Tour de boas-vindas cancelado.');
                    localStorage.setItem('petitio_tour_seen', 'true'); // Evitar tentar novamente
                }
            };
            waitForDriver();
        }
    }

    // Métodos públicos para iniciar tours específicos
    startLawyerTour() {
        this.startTour('lawyer_dashboard');
    }

    startAdminTour() {
        this.startTour('admin_dashboard');
    }

    startProcessesTour() {
        this.startTour('processes_dashboard');
    }

    stopTour() {
        if (this.currentDriver) {
            this.currentDriver.destroy();
            this.currentDriver = null;
        }
    }
}

// Inicializar tour system quando o documento carregar
document.addEventListener('DOMContentLoaded', () => {
    window.petitioTourSystem = new TourSystem();
    // Alias para compatibilidade
    window.tourSystem = window.petitioTourSystem;
    
    // Funções globais para fácil acesso
    window.startTour = (tourName) => {
        if (window.petitioTourSystem) {
            window.petitioTourSystem.startTour(tourName);
        }
    };
    
    window.startTourForCurrentPage = () => {
        if (window.petitioTourSystem) {
            window.petitioTourSystem.startTourForCurrentPage();
        }
    };
    
    window.stopTour = () => {
        if (window.petitioTourSystem) {
            window.petitioTourSystem.stopTour();
        }
    };
});
