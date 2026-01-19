/**
 * Sistema de Notificações Push - Portal do Cliente
 */

class PushNotificationManager {
    constructor() {
        this.registration = null;
        this.vapidPublicKey = null;
        this.isSubscribed = false;
        this.init();
    }

    async init() {
        // Verificar se o navegador suporta notificações push
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            console.log('Push notifications not supported');
            this.hidePushUI();
            return;
        }

        try {
            // Registrar service worker
            this.registration = await navigator.serviceWorker.register('/static/js/sw.js');
            console.log('Service Worker registered successfully');

            // Verificar status da inscrição
            await this.checkSubscriptionStatus();

            // Configurar UI
            this.setupUI();

        } catch (error) {
            console.error('Service Worker registration failed:', error);
            this.hidePushUI();
        }
    }

    async checkSubscriptionStatus() {
        try {
            const subscription = await this.registration.pushManager.getSubscription();
            this.isSubscribed = !!subscription;

            if (this.isSubscribed) {
                console.log('User is already subscribed to push notifications');
                this.updateUI(true);
            } else {
                console.log('User is not subscribed to push notifications');
                this.updateUI(false);
            }
        } catch (error) {
            console.error('Error checking subscription status:', error);
        }
    }

    async subscribe() {
        try {
            // Solicitar permissão
            const permission = await Notification.requestPermission();

            if (permission !== 'granted') {
                throw new Error('Notification permission denied');
            }

            // Obter chave VAPID do servidor
            const response = await fetch('/portal/api/push/vapid-key');
            const data = await response.json();
            this.vapidPublicKey = data.publicKey;

            // Criar inscrição
            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });

            // Enviar inscrição para o servidor
            const result = await fetch('/portal/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    subscription: subscription.toJSON()
                })
            });

            if (result.ok) {
                this.isSubscribed = true;
                this.updateUI(true);
                this.showNotification('Notificações ativadas!', 'success');
            } else {
                throw new Error('Failed to subscribe on server');
            }

        } catch (error) {
            console.error('Error subscribing to push notifications:', error);
            this.showNotification('Erro ao ativar notificações', 'error');
        }
    }

    async unsubscribe() {
        try {
            const subscription = await this.registration.pushManager.getSubscription();

            if (subscription) {
                await subscription.unsubscribe();

                // Remover do servidor
                await fetch('/portal/api/push/unsubscribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        endpoint: subscription.endpoint
                    })
                });

                this.isSubscribed = false;
                this.updateUI(false);
                this.showNotification('Notificações desativadas', 'info');
            }
        } catch (error) {
            console.error('Error unsubscribing from push notifications:', error);
        }
    }

    setupUI() {
        // Adicionar botão de toggle nas configurações
        const settingsBtn = document.createElement('button');
        settingsBtn.id = 'pushNotificationToggle';
        settingsBtn.className = 'btn btn-outline-primary me-2';
        settingsBtn.innerHTML = '<i class="fas fa-bell me-2"></i>Ativar Notificações';

        // Adicionar ao header ou a uma área de configurações
        const header = document.querySelector('.navbar, .card-header');
        if (header) {
            header.appendChild(settingsBtn);
        }

        // Event listener
        settingsBtn.addEventListener('click', () => {
            if (this.isSubscribed) {
                this.unsubscribe();
            } else {
                this.subscribe();
            }
        });
    }

    updateUI(subscribed) {
        const btn = document.getElementById('pushNotificationToggle');
        if (btn) {
            // Preservar classes de layout, apenas mudar cor e conteúdo
            const layoutClasses = 'w-100 h-100 py-4 d-flex flex-column align-items-center justify-content-center';
            if (subscribed) {
                btn.className = `btn btn-success ${layoutClasses}`;
                btn.innerHTML = '<i class="fas fa-bell-slash fa-2x mb-2"></i><span class="small">Desativar Notificações</span>';
            } else {
                btn.className = `btn btn-outline-danger ${layoutClasses}`;
                btn.innerHTML = '<i class="fas fa-bell fa-2x mb-2"></i><span class="small">Notificações</span>';
            }
        }
    }

    hidePushUI() {
        const btn = document.getElementById('pushNotificationToggle');
        if (btn) {
            btn.style.display = 'none';
        }
    }

    showNotification(message, type = 'info') {
        if (window.showNotification) {
            window.showNotification(message, type);
        }
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // Método para enviar notificação de teste
    async sendTestNotification() {
        try {
            const response = await fetch('/portal/api/push/test', {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Notificação de teste enviada!', 'success');
            } else {
                throw new Error('Failed to send test notification');
            }
        } catch (error) {
            console.error('Error sending test notification:', error);
            this.showNotification('Erro ao enviar notificação de teste', 'error');
        }
    }
}

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.pushManager = new PushNotificationManager();
});