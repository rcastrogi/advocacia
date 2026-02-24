/**
 * Petitio Assinador — Cliente JavaScript
 * 
 * Detecta se o agente desktop está rodando em localhost:7777
 * e oferece assinatura A3 (smart card) SOMENTE quando disponível.
 * 
 * Se o agente não estiver instalado/rodando:
 *   - Nenhum badge aparece
 *   - Nenhum seletor A3 aparece
 *   - Nenhum erro é gerado
 *   - O fluxo A1 funciona normalmente como sempre
 */

class PetitioAgent {
    constructor(port = 7777) {
        this.baseUrl = `http://127.0.0.1:${port}`;
        this.online = false;
        this.version = null;
        this.smartcard = null;
    }

    /** Verifica silenciosamente se o agente está rodando. */
    async checkStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/status`, {
                method: 'GET',
                signal: AbortSignal.timeout(1500),
            });
            if (!response.ok) throw new Error('not ok');
            const data = await response.json();
            this.online = data.online === true;
            this.version = data.version;
            this.smartcard = data.smartcard || {};
            return data;
        } catch (e) {
            this.online = false;
            this.version = null;
            this.smartcard = null;
            return { online: false };
        }
    }

    /** Lista certificados no smart card. */
    async listarCertificados() {
        if (!this.online) return [];
        try {
            const resp = await fetch(`${this.baseUrl}/certificados`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000),
            });
            const data = await resp.json();
            return data.success ? data.certificados : [];
        } catch (e) {
            return [];
        }
    }

    /** Assina PDF com certificado A3 no smart card. */
    async assinarPDF(pdfData, pin, options = {}) {
        let b64;
        if (pdfData instanceof Blob) {
            b64 = this._arrayBufferToBase64(await pdfData.arrayBuffer());
        } else if (pdfData instanceof ArrayBuffer) {
            b64 = this._arrayBufferToBase64(pdfData);
        } else if (typeof pdfData === 'string') {
            b64 = pdfData;
        } else {
            throw new Error('Formato de PDF não suportado');
        }

        const resp = await fetch(`${this.baseUrl}/assinar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                documento_b64: b64,
                pin: pin,
                slot_id: options.slot_id || 0,
                cert_id_hex: options.cert_id_hex || null,
                reason: options.reason || 'Peticionamento Eletrônico',
            }),
            signal: AbortSignal.timeout(30000),
        });
        return await resp.json();
    }

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
 * Inicializa o agente SILENCIOSAMENTE.
 * Só cria UI se o agente estiver de fato online.
 * Se não estiver, não faz absolutamente nada.
 */
async function initPetitioAgent() {
    const agent = new PetitioAgent();
    const status = await agent.checkStatus();

    if (!status.online) {
        // Agente não rodando — silêncio total, zero erros
        window.petitioAgent = null;
        return;
    }

    // Agente online — ativar
    window.petitioAgent = agent;
    _showAgentBadge(agent, status);
    _enableA3InPage(status);

    // Monitorar a cada 10s
    setInterval(async () => {
        const s = await agent.checkStatus();
        if (!s.online) {
            const badge = document.getElementById('agentStatusBadge');
            if (badge) badge.remove();
            _disableA3InPage();
            window.petitioAgent = null;
        } else {
            _updateA3Status(s);
        }
    }, 10000);
}


// ============================================================
// UI: Badge de status (só aparece se agente online)
// ============================================================

function _showAgentBadge(agent, status) {
    if (document.getElementById('agentStatusBadge')) return;

    // Injetar CSS uma vez
    if (!document.getElementById('agentBadgeStyle')) {
        const style = document.createElement('style');
        style.id = 'agentBadgeStyle';
        style.textContent = `
            #agentStatusBadge {
                position: fixed; bottom: 20px; right: 20px; z-index: 1050;
                display: flex; align-items: center; gap: 8px;
                padding: 8px 14px; background: white;
                border: 1px solid #dee2e6; border-radius: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                font-size: 0.85rem; cursor: pointer;
                transition: all 0.3s ease;
            }
            #agentStatusBadge:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
            #agentStatusBadge .dot {
                width: 10px; height: 10px; border-radius: 50%;
                display: inline-block; transition: background 0.3s;
            }
            @keyframes a3pulse {
                0% { box-shadow: 0 0 0 0 rgba(0,123,255,0.4); }
                70% { box-shadow: 0 0 0 6px rgba(0,123,255,0); }
                100% { box-shadow: 0 0 0 0 rgba(0,123,255,0); }
            }
        `;
        document.head.appendChild(style);
    }

    const sc = status.smartcard || {};
    const card = sc.card_detected || false;
    const readers = (sc.readers || []).length > 0;

    const dotColor = card ? '#007bff' : (readers ? '#ffc107' : '#28a745');
    const label = card ? 'A3 pronto' : (readers ? 'Insira o cartão' : 'Agente ativo');
    const tooltip = card
        ? 'Smart card detectado! Pronto para assinar.'
        : (readers ? 'Leitor detectado, insira o cartão.' : 'Agente rodando, conecte o leitor.');

    const el = document.createElement('div');
    el.id = 'agentStatusBadge';
    el.title = tooltip;
    el.innerHTML = `
        <i class="fas fa-id-card" style="color:#007bff"></i>
        <span class="dot" style="background:${dotColor}${card ? ';animation:a3pulse 2s infinite' : ''}"></span>
        <span class="label">${label}</span>
    `;
    el.addEventListener('click', () => _showAgentModal(agent));
    document.body.appendChild(el);
}


// ============================================================
// UI: Habilitar/desabilitar opção A3 em saved_view
// ============================================================

function _enableA3InPage(status) {
    const wrapper = document.getElementById('metodoAssinatura');
    const radio = document.getElementById('metodoA3');
    if (!wrapper || !radio) return;

    wrapper.classList.remove('d-none');
    radio.disabled = false;
    _updateA3Status(status);

    // Se não tem A1 mas tem agente A3, habilitar botão de protocolar
    if (window._hasA1Certificate === false) {
        const btn = document.getElementById('btnProtocolar');
        const noCertWarn = document.getElementById('noCertWarning');
        if (btn && !btn.getAttribute('data-no-process')) btn.disabled = false;
        // Ajustar aviso: tem A3 disponível
        if (noCertWarn) {
            noCertWarn.className = 'alert alert-info py-2 mb-2';
            noCertWarn.innerHTML = '<i class="fas fa-info-circle me-1"></i>' +
                '<small>Certificado A1 não configurado, mas você pode usar o <strong>Smart Card (A3)</strong>. ' +
                'Selecione o método A3 acima.</small>';
        }
    }
}

function _disableA3InPage() {
    const radio = document.getElementById('metodoA3');
    const radioA1 = document.getElementById('metodoA1');
    const statusDiv = document.getElementById('a3Status');

    if (radio) {
        radio.disabled = true;
        if (radio.checked && radioA1) {
            radioA1.checked = true;
            radioA1.dispatchEvent(new Event('change'));
        }
    }
    if (statusDiv) statusDiv.classList.add('d-none');
}

function _updateA3Status(status) {
    const dot = document.getElementById('a3StatusDot');
    const text = document.getElementById('a3StatusText');
    const div = document.getElementById('a3Status');
    if (!dot || !text || !div) return;

    const sc = status.smartcard || {};
    const card = sc.card_detected || false;
    const readers = (sc.readers || []).length > 0;

    div.classList.remove('d-none');
    if (card) {
        dot.className = 'fas fa-circle text-success';
        text.textContent = 'Smart card pronto!';
    } else if (readers) {
        dot.className = 'fas fa-circle text-warning';
        text.textContent = 'Insira o smart card';
    } else {
        dot.className = 'fas fa-circle text-info';
        text.textContent = 'Agente ativo (sem leitor)';
    }

    // Atualizar badge global
    const badgeDot = document.querySelector('#agentStatusBadge .dot');
    const badgeLabel = document.querySelector('#agentStatusBadge .label');
    if (badgeDot) {
        badgeDot.style.background = card ? '#007bff' : (readers ? '#ffc107' : '#28a745');
        badgeDot.style.animation = card ? 'a3pulse 2s infinite' : 'none';
    }
    if (badgeLabel) {
        badgeLabel.textContent = card ? 'A3 pronto' : (readers ? 'Insira o cartão' : 'Agente ativo');
    }
}


// ============================================================
// Modal de detalhes do agente
// ============================================================

async function _showAgentModal(agent) {
    const existing = document.getElementById('agentModal');
    if (existing) existing.remove();

    const status = await agent.checkStatus();
    const sc = status.smartcard || {};
    const certs = await agent.listarCertificados();

    const certsHtml = certs.length > 0
        ? certs.map(c => `
            <div class="card mb-2"><div class="card-body py-2">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>${c.nome_titular || c.common_name || 'Certificado'}</strong>
                        ${c.cpf ? `<br><small class="text-muted">CPF: ${c.cpf}</small>` : ''}
                        ${c.oab ? `<br><small class="text-muted">OAB: ${c.oab}</small>` : ''}
                    </div>
                    <span class="badge ${c.valido ? 'bg-success' : 'bg-danger'}">${c.valido ? 'Válido' : 'Expirado'}</span>
                </div>
                <small class="text-muted">Validade: ${c.validade_inicio || '?'} a ${c.validade_fim || '?'}</small>
            </div></div>
        `).join('')
        : '<p class="text-muted">Nenhum certificado encontrado. Insira o smart card.</p>';

    const icon = sc.card_detected ? '🟢' : (sc.readers?.length ? '🟡' : '🔵');

    const html = `
        <div class="modal fade" id="agentModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title"><i class="fas fa-id-card me-2"></i>Petitio Assinador</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="d-flex align-items-center gap-2 mb-3">
                            <span style="font-size:1.2rem">${icon}</span>
                            <strong>Agente Conectado</strong>
                            <small class="text-muted">v${status.version || '?'}</small>
                        </div>
                        <h6><i class="fas fa-usb me-1"></i> Leitores</h6>
                        <div class="mb-3">
                            ${sc.readers?.length
                                ? sc.readers.map(r => `<span class="badge bg-secondary me-1">${r}</span>`).join('')
                                : '<span class="text-muted">Nenhum leitor detectado</span>'}
                        </div>
                        <h6><i class="fas fa-certificate me-1"></i> Certificados</h6>
                        ${certsHtml}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Fechar</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
    new bootstrap.Modal(document.getElementById('agentModal')).show();
}


// ============================================================
// Dialog de PIN para assinar com A3
// ============================================================

function requestPIN() {
    return new Promise((resolve) => {
        const existing = document.getElementById('pinModal');
        if (existing) existing.remove();

        const html = `
            <div class="modal fade" id="pinModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-header bg-warning">
                            <h6 class="modal-title"><i class="fas fa-key me-1"></i> PIN do Smart Card</h6>
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

        document.getElementById('pinConfirm').addEventListener('click', () => {
            const pin = input.value.trim();
            if (!pin) {
                document.getElementById('pinError').textContent = 'PIN obrigatório';
                document.getElementById('pinError').classList.remove('d-none');
                return;
            }
            modal.hide();
            resolve(pin);
        });

        document.getElementById('pinCancel').addEventListener('click', () => {
            modal.hide();
            resolve(null);
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('pinConfirm').click();
        });

        modal.show();
        setTimeout(() => input.focus(), 500);

        document.getElementById('pinModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('pinModal').remove();
        });
    });
}


// ============================================================
// Inicialização — UMA verificação silenciosa, sem erros
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    if (path.includes('/petitions/') || path.includes('/processes/')) {
        initPetitioAgent(); // Silencioso — se offline, nada acontece
    }
});
