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
        // Tours para Advogados/Escritórios
        this.tours.lawyer_dashboard = {
            steps: [
                {
                    element: '.navbar-brand',
                    intro: 'Bem-vindo ao Petitio! Sistema completo de gestão jurídica para advogados.',
                    position: 'bottom'
                },
                {
                    element: '[href*="dashboard"]',
                    intro: 'Dashboard com estatísticas das suas petições, clientes e uso de IA.',
                    position: 'bottom'
                },
                {
                    element: '[href*="peticionador"]',
                    intro: 'Crie petições automaticamente usando IA ou modelos pré-configurados.',
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
                    element: '[href*="procuracao"]',
                    intro: 'Gere procurações automaticamente para seus clientes.',
                    position: 'bottom'
                },
                {
                    element: '[href*="processes"]',
                    intro: 'Sistema completo de gerenciamento de processos judiciais com dashboard, relatórios e notificações.',
                    position: 'bottom'
                },
                {
                    element: '[href*="credits_dashboard"]',
                    intro: 'Monitore seus créditos de IA disponíveis para gerar petições.',
                    position: 'left'
                },
                {
                    element: '[href*="notifications"]',
                    intro: 'Fique por dentro das notificações importantes do sistema.',
                    position: 'left'
                }
            ]
        };

        // Tours para Administradores (Master)
        this.tours.admin_dashboard = {
            steps: [
                {
                    element: '.navbar-brand',
                    intro: 'Painel Administrativo do Petitio - Controle total do sistema.',
                    position: 'bottom'
                },
                {
                    element: '[href*="admin.dashboard"]',
                    intro: 'Dashboard administrativo com métricas globais do sistema.',
                    position: 'bottom'
                },
                {
                    element: '[href*="admin.users_list"]',
                    intro: 'Gerencie todos os usuários do sistema: advogados, escritórios e clientes.',
                    position: 'bottom'
                },
                {
                    element: '[href*="billing.plans"]',
                    intro: 'Configure planos de cobrança e preços do sistema.',
                    position: 'bottom'
                },
                {
                    element: '[href*="billing.users"]',
                    intro: 'Associe usuários aos planos e gerencie assinaturas.',
                    position: 'bottom'
                },
                {
                    element: '[href*="billing.petition_types"]',
                    intro: 'Configure tipos de petições disponíveis no sistema.',
                    position: 'bottom'
                },
                {
                    element: '[href*="main.admin_testimonials"]',
                    intro: 'Gerencie depoimentos exibidos no site.',
                    position: 'bottom'
                },
                {
                    element: '[href*="main.roadmap"]',
                    intro: 'Acompanhe o desenvolvimento e roadmap do sistema.',
                    position: 'left'
                }
            ]
        };

        // Tours para Clientes (Portal do Cliente)
        this.tours.client_portal = {
            steps: [
                {
                    element: '.navbar-brand',
                    intro: 'Portal do Cliente - Acompanhe seus processos jurídicos.',
                    position: 'bottom'
                },
                {
                    element: '[href*="portal"]',
                    intro: 'Dashboard com status dos seus processos e atualizações.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="processos"]',
                    intro: 'Visualize todos os seus processos em andamento.',
                    position: 'right'
                },
                {
                    element: '[data-tour="documentos"]',
                    intro: 'Acesse documentos e petições dos seus processos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="chat"]',
                    intro: 'Converse diretamente com seu advogado.',
                    position: 'right'
                },
                {
                    element: '[data-tour="pagamentos"]',
                    intro: 'Acompanhe pagamentos e faturas dos serviços jurídicos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="perfil"]',
                    intro: 'Atualize suas informações pessoais e de contato.',
                    position: 'left'
                }
            ]
        };

        // Tour do Peticionador (comum a advogados/escritórios)
        this.tours.peticionador = {
            steps: [
                {
                    element: '.page-header',
                    intro: 'Peticionador - Crie petições de forma inteligente e automatizada.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="tipo-peticao"]',
                    intro: 'Escolha o tipo de petição. Temos diversos modelos para diferentes áreas do direito.',
                    position: 'right'
                },
                {
                    element: '[data-tour="ia-generator"]',
                    intro: 'Use IA para gerar petições automaticamente a partir de uma descrição simples.',
                    position: 'right'
                },
                {
                    element: '[data-tour="modelos"]',
                    intro: 'Utilize templates pré-configurados e atualizados com a legislação vigente.',
                    position: 'right'
                }
            ]
        };

        // Tour do Dashboard do Cliente
        this.tours.client_dashboard = {
            steps: [
                {
                    element: '.page-header',
                    intro: 'Bem-vindo ao seu Portal do Cliente! Aqui você acompanha todos os seus processos.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="client-stats"]',
                    intro: 'Veja um resumo dos seus processos ativos, pendências e prazos importantes.',
                    position: 'right'
                },
                {
                    element: '[data-tour="recent-activity"]',
                    intro: 'Acompanhe as últimas atualizações dos seus casos e comunicações.',
                    position: 'right'
                },
                {
                    element: '[data-tour="client-menu"]',
                    intro: 'Use o menu lateral para navegar entre processos, documentos e mensagens.',
                    position: 'right'
                }
            ]
        };

        // Tour de Documentos do Cliente
        this.tours.client_documents = {
            steps: [
                {
                    element: '.documents-section',
                    intro: 'Aqui estão todos os documentos relacionados aos seus processos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="document-filter"]',
                    intro: 'Filtre documentos por tipo, data ou processo específico.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="document-download"]',
                    intro: 'Baixe petições, contratos e outros documentos importantes.',
                    position: 'left'
                }
            ]
        };

        // Tour de Comunicação do Cliente
        this.tours.client_communication = {
            steps: [
                {
                    element: '.messages-section',
                    intro: 'Comunique-se diretamente com seus advogados através desta seção.',
                    position: 'right'
                },
                {
                    element: '[data-tour="send-message"]',
                    intro: 'Envie mensagens para esclarecer dúvidas ou fornecer informações.',
                    position: 'top'
                },
                {
                    element: '[data-tour="message-history"]',
                    intro: 'Veja o histórico completo de todas as comunicações.',
                    position: 'left'
                }
            ]
        };

        // Tour do Dashboard Administrativo
        this.tours.admin_dashboard = {
            steps: [
                {
                    element: '.admin-stats',
                    intro: 'Visão geral do sistema: usuários ativos, uso de recursos e métricas importantes.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="system-health"]',
                    intro: 'Monitore a saúde do sistema e performance dos serviços.',
                    position: 'right'
                },
                {
                    element: '[data-tour="recent-activity"]',
                    intro: 'Acompanhe as atividades recentes de usuários e sistema.',
                    position: 'right'
                },
                {
                    element: '[data-tour="admin-menu"]',
                    intro: 'Acesse todas as ferramentas administrativas através do menu lateral.',
                    position: 'right'
                }
            ]
        };

        // Tour de Gerenciamento de Usuários
        this.tours.admin_users = {
            steps: [
                {
                    element: '.users-table',
                    intro: 'Gerencie todos os usuários do sistema: advogados, escritórios e clientes.',
                    position: 'right'
                },
                {
                    element: '[data-tour="user-filter"]',
                    intro: 'Filtre usuários por tipo, status ou plano de assinatura.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="user-actions"]',
                    intro: 'Edite permissões, altere planos ou suspenda contas quando necessário.',
                    position: 'left'
                },
                {
                    element: '[data-tour="bulk-actions"]',
                    intro: 'Execute ações em lote para gerenciar múltiplos usuários simultaneamente.',
                    position: 'top'
                }
            ]
        };

        // Tour do Sistema de Cobrança
        this.tours.admin_billing = {
            steps: [
                {
                    element: '.billing-overview',
                    intro: 'Visão geral de faturamento, pagamentos e inadimplências.',
                    position: 'right'
                },
                {
                    element: '[data-tour="plans-management"]',
                    intro: 'Configure e gerencie os diferentes planos de assinatura disponíveis.',
                    position: 'right'
                },
                {
                    element: '[data-tour="payment-gateway"]',
                    intro: 'Configure gateways de pagamento e métodos de cobrança.',
                    position: 'right'
                },
                {
                    element: '[data-tour="billing-reports"]',
                    intro: 'Gere relatórios detalhados de receita e uso do sistema.',
                    position: 'left'
                }
            ]
        };

        // Tour de Configurações do Sistema
        this.tours.admin_system = {
            steps: [
                {
                    element: '.system-settings',
                    intro: 'Configure aspectos globais do sistema e integrações.',
                    position: 'right'
                },
                {
                    element: '[data-tour="templates-config"]',
                    intro: 'Gerencie templates de petições e documentos padronizados.',
                    position: 'right'
                },
                {
                    element: '[data-tour="api-integrations"]',
                    intro: 'Configure integrações com tribunais, cartórios e outros sistemas.',
                    position: 'right'
                },
                {
                    element: '[data-tour="backup-settings"]',
                    intro: 'Configure backups automáticos e políticas de retenção de dados.',
                    position: 'left'
                }
            ]
        };

        // Tour de Gerenciamento de Clientes (para advogados/escritórios)
        this.tours.clients = {
            steps: [
                {
                    element: '.clients-list',
                    intro: 'Gerencie todos os seus clientes e seus respectivos casos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="client-search"]',
                    intro: 'Busque clientes por nome, CPF/CNPJ ou número do processo.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="client-details"]',
                    intro: 'Veja detalhes completos do cliente, processos ativos e histórico.',
                    position: 'right'
                },
                {
                    element: '[data-tour="add-client"]',
                    intro: 'Adicione novos clientes ao sistema com informações completas.',
                    position: 'left'
                }
            ]
        };

        // Tour do Sistema de Processos (Dashboard e Gerenciamento)
        this.tours.processes_dashboard = {
            steps: [
                {
                    element: '.breadcrumb-custom',
                    intro: 'Bem-vindo ao Sistema de Gerenciamento de Processos! Acompanhe todos os seus casos judiciais.',
                    position: 'bottom'
                },
                {
                    element: '.dashboard-card',
                    intro: 'Cards com estatísticas dos seus processos: total, aguardando distribuição, em andamento e petições sem número.',
                    position: 'right'
                },
                {
                    element: '[href*="processes"]',
                    intro: 'Acesse o dashboard completo de processos com métricas detalhadas.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="urgent-deadlines"]',
                    intro: 'Alertas de prazos urgentes - processos com vencimento em até 7 dias.',
                    position: 'right'
                },
                {
                    element: '[data-tour="notifications"]',
                    intro: 'Notificações importantes sobre mudanças nos seus processos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="quick-actions"]',
                    intro: 'Ações rápidas: ver todos os processos, petições pendentes, relatórios e novo processo.',
                    position: 'right'
                },
                {
                    element: '[data-tour="recent-processes"]',
                    intro: 'Processos criados recentemente com status e informações básicas.',
                    position: 'right'
                },
                {
                    element: '[data-tour="pending-petitions"]',
                    intro: 'Petições que foram criadas mas ainda não têm número de processo vinculado.',
                    position: 'right'
                },
                {
                    element: '[data-tour="status-distribution"]',
                    intro: 'Distribuição visual dos processos por status atual.',
                    position: 'left'
                }
            ]
        };

        // Tour da Página de Relatórios de Processos
        this.tours.processes_reports = {
            steps: [
                {
                    element: '.breadcrumb-custom',
                    intro: 'Página de Relatórios - Análises detalhadas dos seus processos judiciais.',
                    position: 'bottom'
                },
                {
                    element: '.dashboard-card',
                    intro: 'Clique em qualquer tipo de relatório para gerar análises específicas.',
                    position: 'right'
                },
                {
                    element: '[data-tour="status-distribution-report"]',
                    intro: 'Relatório de distribuição por status - veja como seus processos estão distribuídos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="monthly-creation-report"]',
                    intro: 'Acompanhe a evolução da criação de processos mês a mês.',
                    position: 'right'
                },
                {
                    element: '[data-tour="court-distribution-report"]',
                    intro: 'Análise de processos por tribunal e justiça - onde seus casos tramitam.',
                    position: 'right'
                },
                {
                    element: '[data-tour="deadline-analysis-report"]',
                    intro: 'Análise completa de prazos: próximos, vencidos e urgentes.',
                    position: 'right'
                },
                {
                    element: '[data-tour="petition-link-report"]',
                    intro: 'Relatório de vinculação entre petições e processos criados.',
                    position: 'right'
                },
                {
                    element: '[data-tour="date-filters"]',
                    intro: 'Configure período do relatório com datas inicial e final.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="report-results"]',
                    intro: 'Aqui serão exibidos os resultados dos relatórios gerados.',
                    position: 'right'
                },
                {
                    element: '[data-tour="export-report"]',
                    intro: 'Exporte relatórios em diferentes formatos para análise externa.',
                    position: 'left'
                }
            ]
        };

        // Tour da API de Processos
        this.tours.processes_api = {
            steps: [
                {
                    element: '[data-tour="api-endpoints"]',
                    intro: 'APIs RESTful completas para integração com outros sistemas.',
                    position: 'right'
                },
                {
                    element: '[data-tour="process-crud"]',
                    intro: 'Operações completas: criar, ler, atualizar e excluir processos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="notifications-api"]',
                    intro: 'APIs para gerenciar notificações e alertas de processos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="reports-api"]',
                    intro: 'Gere relatórios programaticamente através das APIs.',
                    position: 'right'
                }
            ]
        };

        // Tour de Autenticação de Dois Fatores (2FA)
        this.tours.two_factor_auth = {
            steps: [
                {
                    element: '.page-header, [data-tour="2fa-header"]',
                    intro: 'Autenticação de Dois Fatores - Proteção máxima da sua conta com verificação adicional.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="2fa-status"]',
                    intro: 'Status do 2FA: veja se a autenticação de dois fatores está ativada ou desativada.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-enable"]',
                    intro: 'Clique para ativar 2FA e aumentar a segurança da sua conta.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-qr-code"]',
                    intro: 'Escaneie este código QR com seu autenticador (Google Authenticator, Authy, Microsoft Authenticator, etc).',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-backup-codes"]',
                    intro: 'Seus códigos de backup - guarde-os em local seguro para recuperar acesso se perder seu autenticador.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-download-backup"]',
                    intro: 'Baixe os códigos de backup em PDF para guardar seguro. Cada código pode ser usado uma única vez.',
                    position: 'left'
                },
                {
                    element: '[data-tour="2fa-rate-limiting"]',
                    intro: 'Proteção contra força bruta: após 3 tentativas incorretas de 2FA, sua conta fica bloqueada por 15 minutos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-verification"]',
                    intro: 'Insira o código de 6 dígitos do seu autenticador para verificar.',
                    position: 'right'
                }
            ]
        };

        // Tour de Auditoria e Logs
        this.tours.audit_logs = {
            steps: [
                {
                    element: '.page-header, [data-tour="audit-header"]',
                    intro: 'Logs de Auditoria - Rastreie todas as ações no sistema para compliance e segurança.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-stats"]',
                    intro: 'Estatísticas: total de eventos registrados e eventos de hoje.',
                    position: 'right'
                },
                {
                    element: '[data-tour="audit-table"]',
                    intro: 'Tabela de eventos: data/hora, usuário, ação, entidade afetada e detalhes completos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="audit-entity-type"]',
                    intro: 'Filtro por tipo de entidade: User, Document, Process, Petition, 2FA, etc.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-entity-id"]',
                    intro: 'Filtro por ID específico: rastreie eventos de uma entidade em particular.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-action"]',
                    intro: 'Filtro por ação: CREATE, UPDATE, DELETE, LOGIN, 2FA_ENABLED, 2FA_DISABLED, etc.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-user"]',
                    intro: 'Filtro por usuário: veja todas as ações de um usuário específico.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-date-range"]',
                    intro: 'Filtro por período: selecione datas inicial e final para análise temporal.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-details"]',
                    intro: 'Clique em um evento para ver detalhes completos: valores antigos, novos, IP, user agent e mais.',
                    position: 'left'
                }
            ]
        };

        // Tour de Segurança Avançada
        this.tours.security_settings = {
            steps: [
                {
                    element: '.page-header, [data-tour="security-header"]',
                    intro: 'Configurações de Segurança - Proteja sua conta com as melhores práticas de segurança.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="password-security"]',
                    intro: 'Segurança de Senha: altere sua senha regularmente e use combinações fortes.',
                    position: 'right'
                },
                {
                    element: '[data-tour="two-factor"]',
                    intro: 'Autenticação de Dois Fatores (2FA): adicione uma camada extra de segurança.',
                    position: 'right'
                },
                {
                    element: '[data-tour="login-history"]',
                    intro: 'Histórico de Login: veja todos os acessos à sua conta com data, hora, IP e localização.',
                    position: 'right'
                },
                {
                    element: '[data-tour="active-sessions"]',
                    intro: 'Sessões Ativas: veja todos os dispositivos/navegadores conectados e encerre sesões suspeitas.',
                    position: 'right'
                },
                {
                    element: '[data-tour="api-keys"]',
                    intro: 'Chaves de API: crie e gerencie tokens para integrações seguras com outros sistemas.',
                    position: 'right'
                },
                {
                    element: '[data-tour="trusted-devices"]',
                    intro: 'Dispositivos Confiáveis: adicione dispositivos à lista branca para pular 2FA em locais seguros.',
                    position: 'right'
                },
                {
                    element: '[data-tour="security-notifications"]',
                    intro: 'Notificações de Segurança: receba alertas sobre login de novo dispositivo, mudança de senha, etc.',
                    position: 'left'
                }
            ]
        };

        // Tour de Gerenciamento de 2FA (para administradores)
        this.tours.admin_2fa_management = {
            steps: [
                {
                    element: '.page-header, [data-tour="admin-2fa-header"]',
                    intro: 'Gerenciamento de 2FA - Administre autenticação de dois fatores para os usuários.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="2fa-user-list"]',
                    intro: 'Lista de usuários: visualize status de 2FA (ativado/desativado) para cada usuário.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-user-reset"]',
                    intro: 'Reset de 2FA: reinicialize o 2FA de um usuário se ele perdeu acesso.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-enforcement"]',
                    intro: 'Forçar 2FA: exija que certos grupos de usuários usem 2FA obrigatoriamente.',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-audit-logs"]',
                    intro: 'Logs de 2FA: rastreie eventos de 2FA (ativação, desativação, tentativas de login).',
                    position: 'right'
                },
                {
                    element: '[data-tour="2fa-statistics"]',
                    intro: 'Estatísticas: percentual de usuários com 2FA ativado, tentativas bloqueadas, etc.',
                    position: 'right'
                }
            ]
        };

        // Tour de Gerenciamento de Auditoria (para administradores)
        this.tours.admin_audit_management = {
            steps: [
                {
                    element: '.page-header, [data-tour="admin-audit-header"]',
                    intro: 'Gerenciamento de Auditoria - Administre logs do sistema para compliance e investigação.',
                    position: 'bottom'
                },
                {
                    element: '[data-tour="audit-system-logs"]',
                    intro: 'Logs do Sistema: todos os eventos registrados com timestamp, usuário, ação e detalhes.',
                    position: 'right'
                },
                {
                    element: '[data-tour="audit-retention"]',
                    intro: 'Política de Retenção: defina por quanto tempo os logs são mantidos no sistema.',
                    position: 'right'
                },
                {
                    element: '[data-tour="audit-export"]',
                    intro: 'Exportar Logs: baixe relatórios de auditoria em CSV ou JSON para análise externa.',
                    position: 'right'
                },
                {
                    element: '[data-tour="audit-alerts"]',
                    intro: 'Alertas de Segurança: configure notificações para eventos suspeitos ou críticos.',
                    position: 'right'
                },
                {
                    element: '[data-tour="audit-compliance"]',
                    intro: 'Relatórios de Compliance: gere relatórios para LGPD, ISO 27001 e outras certificações.',
                    position: 'right'
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
        // Detectar tipo de usuário
        const userType = window.currentUser?.userType || 'guest';
        const isClient = window.currentUser?.isClient || false;

        let modalTitle = 'Tour Guiado do Sistema';
        let tourOptions = [];

        if (isClient) {
            // Tours para clientes
            modalTitle = 'Tour Guiado - Portal do Cliente';
            tourOptions = [
                {
                    id: 'client_dashboard',
                    icon: 'fas fa-tachometer-alt text-primary',
                    title: 'Dashboard do Cliente',
                    description: 'Conheça seu painel de acompanhamento de processos'
                },
                {
                    id: 'client_documents',
                    icon: 'fas fa-file-contract text-success',
                    title: 'Meus Documentos',
                    description: 'Acesse petições e documentos relacionados aos seus casos'
                },
                {
                    id: 'client_communication',
                    icon: 'fas fa-comments text-info',
                    title: 'Comunicação',
                    description: 'Veja mensagens e atualizações dos seus advogados'
                }
            ];
        } else if (userType === 'master') {
            // Tours para administradores
            modalTitle = 'Tour Guiado - Administração';
            tourOptions = [
                {
                    id: 'admin_dashboard',
                    icon: 'fas fa-tachometer-alt text-primary',
                    title: 'Dashboard Administrativo',
                    description: 'Visão geral do sistema e métricas de uso'
                },
                {
                    id: 'admin_users',
                    icon: 'fas fa-users text-success',
                    title: 'Gerenciamento de Usuários',
                    description: 'Gerencie advogados, escritórios e permissões'
                },
                {
                    id: 'admin_2fa_management',
                    icon: 'fas fa-shield-alt text-danger',
                    title: 'Gerenciamento de 2FA',
                    description: 'Administre autenticação de dois fatores dos usuários'
                },
                {
                    id: 'admin_audit_management',
                    icon: 'fas fa-list-alt text-warning',
                    title: 'Auditoria do Sistema',
                    description: 'Rastreie e gerencie logs para compliance'
                },
                {
                    id: 'admin_billing',
                    icon: 'fas fa-credit-card text-info',
                    title: 'Sistema de Cobrança',
                    description: 'Configure planos, faturamento e pagamentos'
                },
                {
                    id: 'admin_system',
                    icon: 'fas fa-cogs text-secondary',
                    title: 'Configurações do Sistema',
                    description: 'Gerencie templates, integrações e configurações globais'
                }
            ];
        } else {
            // Tours para advogados/escritórios
            tourOptions = [
                {
                    id: 'lawyer_dashboard',
                    icon: 'fas fa-tachometer-alt text-primary',
                    title: 'Dashboard',
                    description: 'Conheça a página inicial e navegação principal'
                },
                {
                    id: 'peticionador',
                    icon: 'fas fa-file-contract text-success',
                    title: 'Peticionador',
                    description: 'Aprenda a criar petições com IA e modelos'
                },
                {
                    id: 'processes_dashboard',
                    icon: 'fas fa-balance-scale text-info',
                    title: 'Processos',
                    description: 'Sistema completo de gerenciamento de processos judiciais'
                },
                {
                    id: 'processes_reports',
                    icon: 'fas fa-chart-bar text-warning',
                    title: 'Relatórios de Processos',
                    description: 'Análises e relatórios detalhados dos seus processos'
                },
                {
                    id: 'clients',
                    icon: 'fas fa-users text-secondary',
                    title: 'Clientes',
                    description: 'Gerencie seus clientes e seus casos'
                },
                {
                    id: 'two_factor_auth',
                    icon: 'fas fa-shield-alt text-danger',
                    title: 'Autenticação 2FA',
                    description: 'Proteja sua conta com autenticação de dois fatores'
                },
                {
                    id: 'security_settings',
                    icon: 'fas fa-lock text-danger',
                    title: 'Configurações de Segurança',
                    description: 'Gerencie senhas, sessões e chaves de API'
                },
                {
                    id: 'audit_logs',
                    icon: 'fas fa-list-alt text-muted',
                    title: 'Logs de Auditoria',
                    description: 'Rastreie ações no sistema e mudanças em suas contas'
                }
            ];
        }

        // Criar modal com opções de tour
        const modalHtml = `
            <div class="modal fade" id="tourModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-route text-primary me-2"></i>
                                ${modalTitle}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="text-muted mb-3">Escolha qual tour você gostaria de fazer:</p>
                            <div class="list-group">
                                ${tourOptions.map(option => `
                                    <button class="list-group-item list-group-item-action d-flex align-items-center"
                                            onclick="tourSystem.startTour('${option.id}')">
                                        <i class="${option.icon} me-3"></i>
                                        <div>
                                            <strong>${option.title}</strong>
                                            <br><small class="text-muted">${option.description}</small>
                                        </div>
                                    </button>
                                `).join('')}
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
        // Detectar tipo de usuário
        const userType = window.currentUser?.userType || 'guest';
        const isClient = window.currentUser?.isClient || false;

        // Chave específica para cada tipo de usuário
        const welcomeKey = isClient ? 'petitio_client_welcome_tour_shown' :
                          userType === 'master' ? 'petitio_admin_welcome_tour_shown' :
                          'petitio_lawyer_welcome_tour_shown';

        const hasSeenWelcome = localStorage.getItem(welcomeKey);
        if (!hasSeenWelcome && window.location.pathname.includes('dashboard')) {
            // Aguardar um pouco para garantir que a página carregou
            setTimeout(() => {
                this.showWelcomeDialog();
            }, 2000);
        }
    }

    showWelcomeDialog() {
        // Detectar tipo de usuário
        const userType = window.currentUser?.userType || 'guest';
        const isClient = window.currentUser?.isClient || false;

        let welcomeTitle = 'Bem-vindo ao Petitio!';
        let welcomeMessage = 'Seu sistema de gestão jurídica inteligente';
        let tourDescription = 'Criamos um tour rápido para te apresentar as principais funcionalidades.';
        let tourButtonText = 'Começar Tour';
        let suggestedTour = 'dashboard';

        if (isClient) {
            welcomeTitle = 'Bem-vindo ao Portal do Cliente!';
            welcomeMessage = 'Acompanhe seus processos e comunique-se com seus advogados';
            tourDescription = 'Vamos mostrar como usar todas as funcionalidades do seu portal.';
            suggestedTour = 'client_dashboard';
        } else if (userType === 'master') {
            welcomeTitle = 'Bem-vindo ao Painel Administrativo!';
            welcomeMessage = 'Gerencie usuários, sistema e configurações avançadas';
            tourDescription = 'Vamos apresentar as ferramentas administrativas disponíveis.';
            suggestedTour = 'admin_dashboard';
        } else {
            // Advogados/Escritórios
            welcomeTitle = 'Bem-vindo ao Petitio!';
            welcomeMessage = 'Seu sistema de gestão jurídica inteligente';
            tourDescription = 'Criamos um tour rápido para te apresentar as principais funcionalidades.';
            suggestedTour = 'dashboard';
        }

        const dialogHtml = `
            <div class="modal fade" id="welcomeModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-star text-warning me-2"></i>
                                ${welcomeTitle}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-4">
                                <i class="fas fa-rocket text-primary" style="font-size: 4rem;"></i>
                            </div>
                            <h4>${welcomeMessage}</h4>
                            <p class="text-muted mb-4">
                                ${tourDescription}
                                Vamos começar?
                            </p>
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <div class="card h-100 border-primary">
                                        <div class="card-body text-center">
                                            <i class="fas fa-route text-primary mb-2" style="font-size: 2rem;"></i>
                                            <h6>Fazer Tour Agora</h6>
                                            <p class="small text-muted">5 minutos para conhecer tudo</p>
                                            <button class="btn btn-primary btn-sm" onclick="tourSystem.startTour('${suggestedTour}'); document.getElementById('welcomeModal').querySelector('[data-bs-dismiss=modal]').click();">
                                                ${tourButtonText}
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

        // Marcar como visto quando fechar (usando chave específica por tipo de usuário)
        const welcomeKey = isClient ? 'petitio_client_welcome_tour_shown' :
                          userType === 'master' ? 'petitio_admin_welcome_tour_shown' :
                          'petitio_lawyer_welcome_tour_shown';

        document.getElementById('welcomeModal').addEventListener('hidden.bs.modal', () => {
            localStorage.setItem(welcomeKey, 'true');
            document.getElementById('welcomeModal').remove();
        });
    }

    showTourCompletedToast(tourName) {
        // Detectar tipo de usuário para personalizar mensagens
        const userType = window.currentUser?.userType || 'guest';
        const isClient = window.currentUser?.isClient || false;

        const tourNames = {
            // Tours comuns
            dashboard: 'Dashboard',
            peticionador: 'Peticionador',
            dynamic_form: 'Formulários',
            clients: 'Clientes',
            processes_dashboard: 'Processos',
            processes_reports: 'Relatórios de Processos',

            // Tours de Segurança
            two_factor_auth: 'Autenticação de Dois Fatores',
            security_settings: 'Configurações de Segurança',
            audit_logs: 'Logs de Auditoria',

            // Tours para clientes
            client_dashboard: 'Dashboard do Cliente',
            client_documents: 'Documentos',
            client_communication: 'Comunicação',

            // Tours para administradores
            admin_dashboard: 'Dashboard Administrativo',
            admin_users: 'Gerenciamento de Usuários',
            admin_2fa_management: 'Gerenciamento de 2FA',
            admin_audit_management: 'Auditoria do Sistema',
            admin_billing: 'Sistema de Cobrança',
            admin_system: 'Configurações do Sistema'
        };

        const tourNameDisplay = tourNames[tourName] || tourName;

        // Usar o sistema de toast existente
        if (window.showToast) {
            showToast(`Tour de ${tourNameDisplay} concluído! 🎉`, 'success');
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
        // Detectar tipo de usuário
        const userType = window.currentUser?.userType || 'guest';
        const isClient = window.currentUser?.isClient || false;

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
            },
            // Ajuda específica para clientes
            client_dashboard: {
                'client-stats': {
                    title: 'Seus Processos',
                    content: 'Veja quantos processos ativos você tem, prazos importantes e status dos seus casos.'
                },
                'recent-activity': {
                    title: 'Atividades Recentes',
                    content: 'Acompanhe as últimas atualizações dos seus advogados e movimentações processuais.'
                },
                'client-menu': {
                    title: 'Navegação',
                    content: 'Use este menu para acessar processos, documentos, mensagens e seu perfil.'
                }
            },
            client_documents: {
                'document-filter': {
                    title: 'Filtrar Documentos',
                    content: 'Use os filtros para encontrar rapidamente petições, contratos ou outros documentos.'
                },
                'document-download': {
                    title: 'Download de Documentos',
                    content: 'Clique para baixar qualquer documento relacionado aos seus processos.'
                }
            },
            client_communication: {
                'send-message': {
                    title: 'Enviar Mensagens',
                    content: 'Comunique-se diretamente com seus advogados para tirar dúvidas ou fornecer informações.'
                },
                'message-history': {
                    title: 'Histórico de Mensagens',
                    content: 'Veja todas as conversas anteriores organizadas por data.'
                }
            },
            // Ajuda específica para administradores
            admin_dashboard: {
                'system-health': {
                    title: 'Saúde do Sistema',
                    content: 'Monitore o status dos serviços, uso de recursos e possíveis problemas.'
                },
                'admin-menu': {
                    title: 'Menu Administrativo',
                    content: 'Acesse ferramentas para gerenciar usuários, cobrança, sistema e configurações.'
                }
            },
            admin_users: {
                'user-filter': {
                    title: 'Filtrar Usuários',
                    content: 'Filtre usuários por tipo (advogado, escritório, cliente), status ou plano.'
                },
                'user-actions': {
                    title: 'Ações do Usuário',
                    content: 'Edite permissões, altere planos de assinatura ou suspenda contas quando necessário.'
                },
                'bulk-actions': {
                    title: 'Ações em Lote',
                    content: 'Selecione múltiplos usuários para executar ações como alterar planos ou enviar notificações.'
                }
            },
            admin_billing: {
                'plans-management': {
                    title: 'Gerenciar Planos',
                    content: 'Configure preços, limites e recursos disponíveis em cada plano de assinatura.'
                },
                'payment-gateway': {
                    title: 'Gateways de Pagamento',
                    content: 'Configure integrações com diferentes provedores de pagamento e métodos de cobrança.'
                },
                'billing-reports': {
                    title: 'Relatórios de Cobrança',
                    content: 'Gere relatórios detalhados de receita, inadimplência e uso do sistema.'
                }
            },
            admin_system: {
                'templates-config': {
                    title: 'Templates do Sistema',
                    content: 'Gerencie templates padrão de petições e documentos jurídicos.'
                },
                'api-integrations': {
                    title: 'Integrações',
                    content: 'Configure conexões com tribunais, cartórios e outros sistemas externos.'
                },
                'backup-settings': {
                    title: 'Configurações de Backup',
                    content: 'Defina frequência de backups e políticas de retenção de dados.'
                }
            },
            // Ajuda para advogados/escritórios
            clients: {
                'client-search': {
                    title: 'Buscar Clientes',
                    content: 'Encontre clientes rapidamente por nome, CPF/CNPJ ou número do processo.'
                },
                'client-details': {
                    title: 'Detalhes do Cliente',
                    content: 'Veja informações completas, processos ativos e histórico do cliente.'
                },
                'add-client': {
                    title: 'Adicionar Cliente',
                    content: 'Cadastre novos clientes com todas as informações necessárias para seus processos.'
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