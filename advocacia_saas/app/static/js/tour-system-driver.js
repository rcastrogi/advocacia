/**
 * Sistema de Tours Guiados - Petitio
 * Implementa tours interativos usando Driver.js (visual melhorado)
 */

class TourSystem {
    constructor() {
        this.currentDriver = null;
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
        // Tours para Advogados/Escritórios - Dashboard Principal
        this.tours.lawyer_dashboard = {
            steps: [
                {
                    element: '[data-tour="main-header"]',
                    popover: {
                        title: 'Bem-vindo ao Petitio!',
                        description: 'Sistema completo de gestão jurídica para advogados.',
                        side: 'bottom',
                        align: 'start'
                    }
                },
                {
                    element: '[data-tour="quick-actions"]',
                    popover: {
                        title: 'Ações Rápidas',
                        description: 'Acesse rapidamente as ações mais usadas: criar petição, adicionar cliente, etc.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="stats-petitions"]',
                    popover: {
                        title: 'Estatísticas de Petições',
                        description: 'Visualize quantas petições você criou, usou IA e quanto economizou.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="stats-clients"]',
                    popover: {
                        title: 'Clientes Ativos',
                        description: 'Veja quantos clientes estão cadastrados em seu sistema.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="stats-ai-credits"]',
                    popover: {
                        title: 'Créditos de IA',
                        description: 'Acompanhe seu uso de IA e quanto ainda pode gerar com seu plano.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="recent-petitions"]',
                    popover: {
                        title: 'Petições Recentes',
                        description: 'Acesse rapidamente suas petições mais recentes.',
                        side: 'left'
                    }
                },
                {
                    element: '[data-tour="your-plan"]',
                    popover: {
                        title: 'Seu Plano',
                        description: 'Visualize seu plano atual e benefícios inclusos.',
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
                        title: 'Painel Administrativo',
                        description: 'Você está no painel de administração do sistema Petitio.',
                        side: 'bottom',
                        align: 'start'
                    }
                },
                {
                    element: '[href*="admin/usuarios"]',
                    popover: {
                        title: 'Gerenciar Usuários',
                        description: 'Visualize, edite e gerencie todos os usuários do sistema.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="admin/petitions"]',
                    popover: {
                        title: 'Tipos e Modelos de Petições',
                        description: 'Configure os tipos de petições, modelos e seções disponíveis.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="admin/roadmap"]',
                    popover: {
                        title: 'Roadmap & Feedback',
                        description: 'Gerencie o roadmap de features e feedback dos usuários.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="billing"]',
                    popover: {
                        title: 'Planos de Cobrança',
                        description: 'Configure os planos de assinatura e limites do sistema.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[href*="admin/logs"]',
                    popover: {
                        title: 'Logs do Sistema',
                        description: 'Monitore atividades e erros do sistema em tempo real.',
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
                        title: 'Prazos Urgentes',
                        description: 'Veja aqui os processos com prazos próximos de vencer.',
                        side: 'bottom'
                    }
                },
                {
                    element: '[data-tour="notifications"]',
                    popover: {
                        title: 'Notificações',
                        description: 'Receba alertas sobre movimentações e prazos importantes.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="quick-actions"]',
                    popover: {
                        title: 'Ações Rápidas',
                        description: 'Acesse rapidamente as funcionalidades mais usadas.',
                        side: 'top'
                    }
                },
                {
                    element: '[data-tour="recent-processes"]',
                    popover: {
                        title: 'Processos Recentes',
                        description: 'Seus últimos processos acessados aparecem aqui.',
                        side: 'left'
                    }
                },
                {
                    element: '[data-tour="pending-petitions"]',
                    popover: {
                        title: 'Petições Pendentes',
                        description: 'Petições que ainda não foram envolvidas com processos.',
                        side: 'left'
                    }
                },
                {
                    element: '[data-tour="status-distribution"]',
                    popover: {
                        title: 'Distribuição de Status',
                        description: 'Visualize a distribuição dos seus processos por status.',
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

        // Verificar se Driver.js está disponível
        if (typeof window.driver !== 'function') {
            console.error('Driver.js não foi carregado. Tentando novamente em 500ms...');
            setTimeout(() => this.startTour(tourName), 500);
            return;
        }

        const steps = this.tours[tourName].steps;

        this.currentDriver = window.driver({
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
            const waitForDriver = () => {
                if (typeof window.driver === 'function') {
                    // Mostrar tour de boas-vindas após 2 segundos
                    setTimeout(() => {
                        this.startTourForCurrentPage();
                    }, 2000);
                    localStorage.setItem('petitio_tour_seen', 'true');
                } else {
                    // Tentar novamente em 100ms
                    setTimeout(waitForDriver, 100);
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
