/**
 * Petitio Assinador — Cliente JavaScript
 * 
 * Detecta se o agente desktop está rodando em localhost:7777
 * e oferece assinatura A3 (smart card) quando disponível.
 * 
 * Uso:
 *   const agent = new PetitioAgent();
 *   const status = await agent.checkStatus();
 *   if (status.online) { ... }
 */

class PetitioAgent {
    constructor(port = 7777) {
        this.baseUrl = `http://127.0.0.1:${port}`;
        this.online = false;
        this.version = null;
        this.smartcard = null;
        this._checkInterval = null;
    }

    /**
     * Verifica se o agente está rodando.
     * @returns {Promise<{online: boolean, version: string, smartcard: object}>}
     */
    async checkStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/status`, {
                method: 'GET',
                signal: AbortSignal.timeout(2000),
            });
            
            if (!response.ok) throw new Error('Agent not responding');
            
            const data = await response.json();
            this.online = data.online === true;
            this.version = data.version;
            this.smartcard = data.smartcard || {};
            return data;
        } catch (e) {
            this.online = false;
            this.version = null;
            this.smartcard = null;
            return { online: false, error: e.message };
        }
    }

    /**
     * Lista certificados no smart card.
     * @returns {Promise<Array>}
     */
    async listarCertificados() {
        try {
            const response = await fetch(`${this.baseUrl}/certificados`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000),
            });
            const data = await response.json();
            return data.success ? data.certificados : [];
        } catch (e) {
            console.warn('Erro ao listar certificados:', e);
            return [];
        }
    }

    /**
     * Assina um documento PDF com o certificado A3.
     * @param {Blob|ArrayBuffer} pdfData - PDF para assinar
     * @param {string} pin - PIN do cartão
     * @param {object} options - Opções extras
     * @returns {Promise<{success: boolean, assinatura_b64: string, message: string}>}
     */
    async assinarPDF(pdfData, pin, options = {}) {
        // Converter para base64
        let b64;
        if (pdfData instanceof Blob) {
            const buffer = await pdfData.arrayBuffer();
            b64 = this._arrayBufferToBase64(buffer);
        } else if (pdfData instanceof ArrayBuffer) {
            b64 = this._arrayBufferToBase64(pdfData);
        } else if (typeof pdfData === 'string') {
            b64 = pdfData; // Já em base64
        } else {
            throw new Error('Formato de PDF não suportado');
        }

        const response = await fetch(`${this.baseUrl}/assinar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                documento_b64: b64,
                pin: pin,
                slot_id: options.slot_id || 0,
                cert_id_hex: options.cert_id_hex || null,
                reason: options.reason || 'Peticionamento Eletrônico',
            }),
            signal: AbortSignal.timeout(30000), // 30s para assinatura
        });

        return await response.json();
    }

    /**
     * Monitora status do agente periodicamente.
     * @param {function} callback - Chamada quando status muda
     * @param {number} interval - Intervalo em ms (padrão: 5000)
     */
    startMonitoring(callback, interval = 5000) {
        this.stopMonitoring();
        
        let lastOnline = null;
        let lastCard = null;

        const check = async () => {
            const status = await this.checkStatus();
            const cardDetected = status.smartcard?.card_detected || false;

            // Notificar apenas se mudou
            if (lastOnline !== this.online || lastCard !== cardDetected) {
                lastOnline = this.online;
                lastCard = cardDetected;
                callback({
                    online: this.online,
                    cardDetected: cardDetected,
                    version: this.version,
                    readers: status.smartcard?.readers || [],
                });
            }
        };

        check(); // Primeira verificação imediata
        this._checkInterval = setInterval(check, interval);
    }

    /**
     * Para o monitoramento.
     */
    stopMonitoring() {
        if (this._checkInterval) {
            clearInterval(this._checkInterval);
            this._checkInterval = null;
        }
    }

    /**
     * Converte ArrayBuffer para base64.
     */
    _arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
}


/**
 * UI Helper - Cria o indicador de status do agente na barra lateral.
 */
function createAgentStatusIndicator() {
    const agent = new PetitioAgent();

    // Criar elemento indicador
    const indicator = document.createElement('div');
    indicator.id = 'agentStatus';
    indicator.className = 'agent-status-indicator';
    indicator.innerHTML = `
        <div class="agent-badge" title="Petitio Assinador">
            <i class="fas fa-id-card"></i>
            <span class="status-dot"></span>
            <span class="status-text">Verificando agente...</span>
        </div>
    `;

    // Estilos
    const style = document.createElement('style');
    style.textContent = `
        .agent-status-indicator {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1050;
        }
        .agent-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .agent-badge:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .agent-badge .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #adb5bd;
            transition: background 0.3s;
        }
        .agent-badge .status-dot.online { background: #28a745; }
        .agent-badge .status-dot.card-ready { background: #007bff; animation: pulse 2s infinite; }
        .agent-badge .status-dot.offline { background: #dc3545; }
        .agent-badge .status-dot.no-card { background: #ffc107; }
        .agent-badge .fa-id-card { color: #6c757d; }
        .agent-badge.online .fa-id-card { color: #007bff; }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(0,123,255,0.4); }
            70% { box-shadow: 0 0 0 6px rgba(0,123,255,0); }
            100% { box-shadow: 0 0 0 0 rgba(0,123,255,0); }
        }
    `;
    document.head.appendChild(style);

    // Monitorar status
    agent.startMonitoring((status) => {
        const dot = indicator.querySelector('.status-dot');
        const text = indicator.querySelector('.status-text');
        const badge = indicator.querySelector('.agent-badge');

        if (!status.online) {
            dot.className = 'status-dot offline';
            text.textContent = 'Agente offline';
            badge.classList.remove('online');
            badge.title = 'Petitio Assinador não está rodando. Baixe em petitio.onrender.com/agent';
        } else if (status.cardDetected) {
            dot.className = 'status-dot card-ready';
            text.textContent = 'A3 pronto';
            badge.classList.add('online');
            badge.title = 'Smart card detectado! Pronto para assinar com certificado A3.';
        } else if (status.readers && status.readers.length > 0) {
            dot.className = 'status-dot no-card';
            text.textContent = 'Insira o cartão';
            badge.classList.add('online');
            badge.title = 'Leitor detectado, mas nenhum cartão inserido.';
        } else {
            dot.className = 'status-dot online';
            text.textContent = 'Agente ativo';
            badge.classList.add('online');
            badge.title = 'Agente rodando, mas nenhum leitor de smart card encontrado.';
        }
    }, 5000);

    // Click handler — mostrar modal de detalhes
    indicator.addEventListener('click', () => {
        showAgentModal(agent);
    });

    document.body.appendChild(indicator);
    return agent;
}


/**
 * Modal com detalhes do agente e certificados.
 */
async function showAgentModal(agent) {
    // Remover modal anterior
    const existing = document.getElementById('agentModal');
    if (existing) existing.remove();

    const status = await agent.checkStatus();
    let certsHtml = '';

    if (status.online) {
        const certs = await agent.listarCertificados();
        if (certs.length > 0) {
            certsHtml = certs.map(c => `
                <div class="card mb-2">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong>${c.nome_titular || c.common_name || 'Certificado'}</strong>
                                ${c.cpf ? `<br><small class="text-muted">CPF: ${c.cpf}</small>` : ''}
                                ${c.oab ? `<br><small class="text-muted">OAB: ${c.oab}</small>` : ''}
                            </div>
                            <span class="badge ${c.valido ? 'bg-success' : 'bg-danger'}">${c.valido ? 'Válido' : 'Expirado'}</span>
                        </div>
                        <small class="text-muted">
                            Validade: ${c.validade_inicio || '?'} a ${c.validade_fim || '?'}
                        </small>
                    </div>
                </div>
            `).join('');
        } else {
            certsHtml = '<p class="text-muted">Nenhum certificado encontrado. Insira o smart card.</p>';
        }
    }

    const smartcard = status.smartcard || {};
    const statusIcon = status.online
        ? (smartcard.card_detected ? '🟢' : smartcard.readers?.length ? '🟡' : '🔵')
        : '🔴';

    const modalHtml = `
        <div class="modal fade" id="agentModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-id-card me-2"></i>Petitio Assinador
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <div class="d-flex align-items-center gap-2 mb-2">
                                <span style="font-size:1.2rem">${statusIcon}</span>
                                <strong>${status.online ? 'Agente Conectado' : 'Agente Offline'}</strong>
                                ${status.version ? `<small class="text-muted">v${status.version}</small>` : ''}
                            </div>
                            ${!status.online ? `
                                <div class="alert alert-warning py-2">
                                    <small>
                                        O Petitio Assinador não está rodando.<br>
                                        Para usar certificado A3 (smart card), inicie o aplicativo.
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                        
                        ${status.online ? `
                        <div class="mb-3">
                            <h6><i class="fas fa-usb me-1"></i> Leitores</h6>
                            ${smartcard.readers?.length
                                ? smartcard.readers.map(r => `<span class="badge bg-secondary me-1">${r}</span>`).join('')
                                : '<span class="text-muted">Nenhum leitor detectado</span>'
                            }
                        </div>
                        
                        <div>
                            <h6><i class="fas fa-certificate me-1"></i> Certificados</h6>
                            ${certsHtml}
                        </div>
                        ` : `
                        <div class="text-center py-3">
                            <i class="fas fa-download fa-2x text-muted mb-2"></i>
                            <p class="mb-1">Baixe o Petitio Assinador para assinar com A3.</p>
                            <a href="/agent/download" class="btn btn-primary btn-sm">
                                <i class="fas fa-download me-1"></i>Baixar para Windows
                            </a>
                        </div>
                        `}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Fechar</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('agentModal'));
    modal.show();
}


/**
 * Dialog de PIN para assinar com A3.
 * @returns {Promise<string|null>} PIN ou null se cancelou
 */
function requestPIN() {
    return new Promise((resolve) => {
        const existing = document.getElementById('pinModal');
        if (existing) existing.remove();

        const html = `
            <div class="modal fade" id="pinModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-header bg-warning">
                            <h6 class="modal-title">
                                <i class="fas fa-key me-1"></i> PIN do Smart Card
                            </h6>
                        </div>
                        <div class="modal-body">
                            <p class="small mb-2">Digite o PIN do seu certificado A3:</p>
                            <input type="password" class="form-control" id="pinInput" 
                                   placeholder="PIN" maxlength="12" autocomplete="off">
                            <div id="pinError" class="text-danger small mt-1 d-none"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary btn-sm" id="pinCancel">Cancelar</button>
                            <button type="button" class="btn btn-primary btn-sm" id="pinConfirm">
                                <i class="fas fa-check me-1"></i>Confirmar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        const modal = new bootstrap.Modal(document.getElementById('pinModal'));

        const input = document.getElementById('pinInput');
        const btnConfirm = document.getElementById('pinConfirm');
        const btnCancel = document.getElementById('pinCancel');

        btnConfirm.addEventListener('click', () => {
            const pin = input.value.trim();
            if (!pin) {
                document.getElementById('pinError').textContent = 'PIN obrigatório';
                document.getElementById('pinError').classList.remove('d-none');
                return;
            }
            modal.hide();
            resolve(pin);
        });

        btnCancel.addEventListener('click', () => {
            modal.hide();
            resolve(null);
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') btnConfirm.click();
        });

        modal.show();
        setTimeout(() => input.focus(), 500);

        // Cleanup
        document.getElementById('pinModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('pinModal').remove();
        });
    });
}


// Auto-inicializar quando o DOM carregar (apenas em páginas com petições/processos)
document.addEventListener('DOMContentLoaded', () => {
    // Verificar se estamos em página relevante
    const isRelevantPage =
        window.location.pathname.includes('/petitions/') ||
        window.location.pathname.includes('/processes/');

    if (isRelevantPage) {
        window.petitioAgent = createAgentStatusIndicator();
    }
});
