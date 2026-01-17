/**
 * Sistema de Notificações no Navbar
 * Gerencia dropdown, badge e polling de notificações
 */

class NotificationSystem {
    constructor() {
        this.dropdown = null;
        this.badge = null;
        this.button = null;
        this.pollInterval = null;
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        // Aguardar DOM carregar
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        this.button = document.getElementById('notificationsDropdownBtn');
        this.dropdown = document.getElementById('notificationsDropdown');
        this.badge = document.getElementById('notificationsBadge');
        
        if (!this.button || !this.dropdown) {
            console.log('Notification elements not found, user may not be logged in');
            return;
        }
        
        // Eventos
        this.button.addEventListener('click', (e) => this.toggle(e));
        document.addEventListener('click', (e) => this.handleOutsideClick(e));
        
        // Carregar notificações iniciais
        this.loadNotifications();
        
        // Polling a cada 30 segundos
        this.startPolling();
    }
    
    toggle(e) {
        e.preventDefault();
        e.stopPropagation();
        
        this.isOpen = !this.isOpen;
        this.dropdown.classList.toggle('show', this.isOpen);
        
        if (this.isOpen) {
            this.loadNotifications();
        }
    }
    
    handleOutsideClick(e) {
        if (!this.button.contains(e.target) && !this.dropdown.contains(e.target)) {
            this.close();
        }
    }
    
    close() {
        this.isOpen = false;
        this.dropdown.classList.remove('show');
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/recent', {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (!response.ok) throw new Error('Failed to load');
            
            const data = await response.json();
            
            if (data.success) {
                this.render(data.notifications);
                this.updateBadge(data.unread_count);
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
            this.renderError();
        }
    }
    
    render(notifications) {
        const container = this.dropdown.querySelector('.notifications-list');
        
        if (!notifications || notifications.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fas fa-bell-slash fa-2x mb-2"></i>
                    <p class="mb-0 small">Nenhuma notificação</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = notifications.map(notif => `
            <div class="notification-item ${notif.read ? 'read' : 'unread'}" 
                 data-notification-id="${notif.id}"
                 ${notif.url ? `onclick="notificationSystem.handleClick(${notif.id}, '${notif.url}')"` : ''}>
                <div class="notification-icon bg-${notif.color}">
                    <i class="fas ${notif.icon}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${this.escapeHtml(notif.title)}</div>
                    <div class="notification-message">${this.escapeHtml(notif.message)}</div>
                    <div class="notification-time">${this.formatTime(notif.created_at)}</div>
                </div>
                ${!notif.read ? '<div class="notification-badge"></div>' : ''}
            </div>
        `).join('');
    }
    
    renderError() {
        const container = this.dropdown.querySelector('.notifications-list');
        container.innerHTML = `
            <div class="text-center py-4 text-danger">
                <i class="fas fa-exclamation-circle fa-2x mb-2"></i>
                <p class="mb-0 small">Erro ao carregar</p>
            </div>
        `;
    }
    
    updateBadge(count) {
        if (!this.badge) return;
        
        count = parseInt(count) || 0;
        
        if (count > 0) {
            this.badge.textContent = count > 99 ? '99+' : count;
            this.badge.style.display = 'inline-block';
        } else {
            this.badge.style.display = 'none';
        }
    }
    
    async handleClick(notificationId, url) {
        // Marcar como lida
        await this.markAsRead(notificationId);
        
        // Redirecionar se tiver URL
        if (url) {
            window.location.href = url;
        }
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/mark-read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateBadge(data.unread_count);
                    // Recarregar lista
                    this.loadNotifications();
                }
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/api/notifications/mark-all-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateBadge(0);
                    this.loadNotifications();
                    showToast('success', data.message);
                }
            }
        } catch (error) {
            console.error('Error marking all as read:', error);
            showToast('danger', 'Erro ao marcar todas como lidas');
        }
    }
    
    startPolling() {
        // Atualizar badge a cada 30 segundos
        this.pollInterval = setInterval(() => {
            this.updateUnreadCount();
        }, 30000);
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    async updateUnreadCount() {
        try {
            const response = await fetch('/api/notifications/unread-count', {
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateBadge(data.count);
                }
            }
        } catch (error) {
            // Silently fail
        }
    }
    
    formatTime(isoString) {
        if (!isoString) return '';
        
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'agora';
        if (diffMins < 60) return `${diffMins}min atrás`;
        if (diffHours < 24) return `${diffHours}h atrás`;
        if (diffDays < 7) return `${diffDays}d atrás`;
        
        return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Instância global
let notificationSystem = null;

// Inicializar quando DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    notificationSystem = new NotificationSystem();
});

// Cleanup ao descarregar
window.addEventListener('beforeunload', () => {
    if (notificationSystem) {
        notificationSystem.stopPolling();
    }
});
