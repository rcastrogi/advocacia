/**
 * Integração de Onboarding com Petitio
 * Comunica com API de onboarding para rastrear progress
 */

class OnboardingManager {
    constructor() {
        this.userOnboarding = null;
        this.init();
    }
    
    async init() {
        await this.loadOnboardingStatus();
        this.setupAutoTracking();
    }
    
    /**
     * Carregar status de onboarding do usuário
     */
    async loadOnboardingStatus() {
        try {
            const response = await fetch('/api/onboarding/status', {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.userOnboarding = data.data;
                console.log('✅ Onboarding status carregado:', this.userOnboarding);
            }
        } catch (error) {
            console.warn('⚠️ Erro ao carregar onboarding:', error);
        }
    }
    
    /**
     * Verificar se deve mostrar tour para novo usuário
     */
    async shouldShowTour() {
        try {
            const response = await fetch('/api/onboarding/should-show-tour', {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.should_show_tour;
            }
        } catch (error) {
            console.warn('⚠️ Erro ao verificar tour:', error);
        }
        return false;
    }
    
    /**
     * Marcar tour como completado
     */
    async markTourCompleted(tourName) {
        try {
            const response = await fetch(`/api/onboarding/tour/${tourName}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log(`✅ Tour "${tourName}" marcado como completado`);
                this.userOnboarding = data.data;
                return true;
            }
        } catch (error) {
            console.error('❌ Erro ao marcar tour:', error);
        }
        return false;
    }
    
    /**
     * Atualizar preferências de onboarding
     */
    async updatePreferences(preferences) {
        try {
            const response = await fetch('/api/onboarding/preferences', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(preferences)
            });
            
            if (response.ok) {
                const data = await response.json();
                this.userOnboarding = data.data;
                return true;
            }
        } catch (error) {
            console.error('❌ Erro ao atualizar preferências:', error);
        }
        return false;
    }
    
    /**
     * Configurar rastreamento automático de tours
     */
    setupAutoTracking() {
        // Integrar com TourSystem quando estiver disponível
        if (window.petitioTourSystem) {
            // Hook para quando um tour completar
            const originalStartTour = window.petitioTourSystem.startTour.bind(window.petitioTourSystem);
            
            window.petitioTourSystem.startTour = function(tourName) {
                originalStartTour(tourName);
                
                // Quando o tour terminar, marcar como completado
                // Isso é tratado pelo Driver.js onNext e onClose callbacks
            };
        }
    }
    
    /**
     * Mapear página atual para nome do tour
     */
    getTourNameFromPage() {
        const path = window.location.pathname.toLowerCase();
        
        if (path.includes('/admin')) return 'admin_dashboard';
        if (path.includes('/processes') || path.includes('/processos')) return 'processes_tour';
        if (path.includes('/clients') || path.includes('/clientes')) return 'clients_tour';
        if (path.includes('/petitions') || path.includes('/peticoes')) return 'petitions_tour';
        if (path.includes('/billing') || path.includes('/assinatura')) return 'billing_tour';
        if (path.includes('/profile') || path.includes('/perfil')) return 'profile_tour';
        if (path.includes('/roadmap')) return 'roadmap_tour';
        
        // Dashboard é o default para advogados
        return 'lawyer_dashboard';
    }
    
    /**
     * Obter taxa de conclusão de tours
     */
    getCompletionRate() {
        return this.userOnboarding?.tour_completion_rate || 0;
    }
    
    /**
     * Tours completados
     */
    getCompletedTours() {
        if (!this.userOnboarding) return [];
        
        return Object.keys(this.userOnboarding.tours_completed || {})
            .filter(key => this.userOnboarding.tours_completed[key]);
    }
    
    /**
     * Tours pendentes
     */
    getPendingTours() {
        if (!this.userOnboarding) return [];
        
        return Object.keys(this.userOnboarding.tours_completed || {})
            .filter(key => !this.userOnboarding.tours_completed[key]);
    }
}

// Instância global
let onboardingManager = null;

// Inicializar quando DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    onboardingManager = new OnboardingManager();
});

// Exportar para uso global
window.OnboardingManager = OnboardingManager;
