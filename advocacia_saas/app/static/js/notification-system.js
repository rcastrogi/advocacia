/**
 * Sistema Unificado de Notificações - Petitio
 * Substitui todos os sistemas de notificação existentes por um único sistema
 */

// Classe principal do sistema de notificações
class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = [];
        // Defer initialization to avoid blocking DOMContentLoaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.init();
            });
        } else {
            this.init();
        }
    }

    init() {
        // Use requestAnimationFrame for better performance
        requestAnimationFrame(() => {
            this.createContainer();
            this.handleServerMessages();

            // API global para uso em JavaScript
            window.showNotification = (message, type = 'info', duration = 5000) => {
                this.show(message, type, duration);
            };

            // Compatibilidade com código existente
            window.showToast = window.showNotification;
            window.showAlert = (message, type = 'info') => {
                this.show(message, type, 0); // 0 = não auto-fechar
            };
        });
    }

    createContainer() {
        // Remover containers antigos se existirem
        const oldContainers = document.querySelectorAll('.notification-container, .toast-container');
        oldContainers.forEach(container => container.remove());

        this.container = document.createElement('div');
        this.container.className = 'notification-container';
        this.container.setAttribute('role', 'region');
        this.container.setAttribute('aria-label', 'Notificações do sistema');
        this.container.setAttribute('aria-live', 'polite');

        // Estilos inline para garantir funcionamento
        Object.assign(this.container.style, {
            position: 'fixed',
            top: '80px',
            right: '20px',
            zIndex: '9999',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            maxWidth: '400px',
            pointerEvents: 'none'
        });

        document.body.appendChild(this.container);
    }

    handleServerMessages() {
        // Buscar flash messages diretamente da API
        this.fetchFlashMessages();
    }

    async fetchFlashMessages() {
        try {
            const response = await fetch('/api/flash-messages', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'
            });

            if (response.ok) {
                const messages = await response.json();
                messages.forEach(msg => {
                    // Erros não fecham automaticamente, apenas sucesso/info/warning
                    const duration = msg.type === 'error' ? 0 : 5000;
                    this.show(msg.message, msg.type, duration);
                });
            }
        } catch (error) {
        }
    }

    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type, duration);
        this.notifications.push(notification);
        this.container.appendChild(notification.element);

        // Auto-remover após duração
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification.id);
            }, duration);
        }

        return notification.id;
    }

    // Método para mostrar mensagem persistente (não fecha automaticamente)
    showPersistent(message, type = 'info') {
        return this.show(message, type, 0);
    }

    createNotification(message, type, duration) {
        const id = Date.now() + Math.random();
        const element = document.createElement('div');

        // Classes e estilos baseados no tipo
        const typeClasses = {
            success: 'notification-success',
            error: 'notification-error',
            warning: 'notification-warning',
            info: 'notification-info'
        };

        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };

        element.className = `notification ${typeClasses[type] || typeClasses.info}`;
        element.setAttribute('role', 'alert');
        element.setAttribute('aria-live', 'assertive');

        Object.assign(element.style, {
            padding: '16px 20px',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            cursor: 'pointer',
            pointerEvents: 'auto',
            animation: 'notificationSlideIn 0.3s ease-out',
            position: 'relative'
        });

        // Gradientes por tipo
        const gradients = {
            success: 'linear-gradient(135deg, #28a745, #20c997)',
            error: 'linear-gradient(135deg, #dc3545, #e74c3c)',
            warning: 'linear-gradient(135deg, #ffc107, #fd7e14)',
            info: 'linear-gradient(135deg, #007bff, #6610f2)'
        };

        element.style.background = gradients[type] || gradients.info;
        element.style.color = type === 'warning' ? '#000' : 'white';

        element.innerHTML = `
            <i class="fas fa-${icons[type] || icons.info}" aria-hidden="true"></i>
            <span class="notification-message">${this.escapeHtml(message)}</span>
            <button class="notification-close" aria-label="Fechar notificação" style="
                background: none;
                border: none;
                color: inherit;
                cursor: pointer;
                font-size: 18px;
                margin-left: auto;
                opacity: 0.8;
            ">×</button>
        `;

        // Event listeners
        // Apenas fechar ao clicar no botão X (não em toda a notificação)
        element.querySelector('.notification-close').addEventListener('click', (e) => {
            e.stopPropagation();
            this.remove(id);
        });
        
        // Para mensagens de sucesso/info, fechar ao clicar na notificação
        if (type !== 'error' && type !== 'warning') {
            element.addEventListener('click', () => this.remove(id));
        }

        return { id, element, type, message, duration };
    }

    remove(id) {
        const index = this.notifications.findIndex(n => n.id === id);
        if (index === -1) return;

        const notification = this.notifications[index];
        notification.element.style.animation = 'notificationSlideOut 0.3s ease-in forwards';

        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
            this.notifications.splice(index, 1);
        }, 300);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Método para limpar todas as notificações
    clear() {
        this.notifications.forEach(notification => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
        });
        this.notifications = [];
    }
}

// CSS para animações
const notificationStyles = `
<style>
@keyframes notificationSlideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes notificationSlideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(100%); opacity: 0; }
}

.notification-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.4;
}

.notification-message {
    flex: 1;
    word-wrap: break-word;
}

.notification-close:hover {
    opacity: 1 !important;
}
</style>
`;

// Inicializar sistema quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Injetar estilos apenas uma vez
    if (!document.getElementById('notification-system-styles')) {
        document.head.insertAdjacentHTML('beforeend', notificationStyles);
    }

    // Inicializar sistema apenas se não existir
    if (!window.notificationSystem) {
        window.notificationSystem = new NotificationSystem();
    }
});

// Fallback para navegadores antigos ou scripts carregados tardiamente
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    // Usar setTimeout para garantir que outros scripts tenham carregado
    setTimeout(function() {
        if (!document.getElementById('notification-system-styles')) {
            document.head.insertAdjacentHTML('beforeend', notificationStyles);
        }
        if (!window.notificationSystem) {
            window.notificationSystem = new NotificationSystem();
        }
    }, 100);
}