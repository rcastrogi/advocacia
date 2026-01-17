/**
 * Calculadora Jurídica - Petitio
 * JavaScript para cálculos de correção monetária, juros e honorários
 * 
 * Estratégia: Pré-carrega índices do BCB ao abrir a página,
 * cálculos são feitos localmente sem nova chamada à API.
 */

// Cache global dos índices do BCB
let indicesBCB = null;
let indicesCarregando = false;
let indicesErro = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('[CALCULATOR] Inicializando calculadora...');
    
    // Inicializar
    initMoneyInputs();
    initDateDefaults();
    initFormHandlers();
    initDynamicFields();
    
    // Pré-carregar índices do BCB em background
    preCarregarIndices();
    
    console.log('[CALCULATOR] Calculadora inicializada com sucesso!');
});

// ============================================
// PRÉ-CARREGAMENTO DE ÍNDICES (BACKGROUND)
// ============================================

async function preCarregarIndices() {
    if (indicesCarregando) return;
    
    indicesCarregando = true;
    console.log('[CALCULATOR] Pré-carregando índices do BCB...');
    
    try {
        const response = await fetch('/calculadora/api/indices', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                indicesBCB = data.indices;
                console.log('[CALCULATOR] ✅ Índices carregados:', Object.keys(indicesBCB));
                atualizarIndicadorStatus(true);
            } else {
                throw new Error(data.message || 'Erro ao carregar índices');
            }
        } else {
            throw new Error('Resposta não OK: ' + response.status);
        }
    } catch (error) {
        console.warn('[CALCULATOR] ⚠️ Erro ao carregar índices:', error.message);
        indicesErro = error.message;
        atualizarIndicadorStatus(false);
        // Usar fallback local
        indicesBCB = getIndicesFallback();
    } finally {
        indicesCarregando = false;
    }
}

function getIndicesFallback() {
    // Taxas médias aproximadas quando API não responde
    return {
        "IPCA": { nome: "IPCA", taxa_mensal: 0.40, fonte: "Estimativa" },
        "INPC": { nome: "INPC", taxa_mensal: 0.45, fonte: "Estimativa" },
        "IGPM": { nome: "IGP-M", taxa_mensal: 0.50, fonte: "Estimativa" },
        "TR": { nome: "TR", taxa_mensal: 0.10, fonte: "Estimativa" },
        "SELIC": { nome: "SELIC", taxa_mensal: 0.85, fonte: "Estimativa" }
    };
}

function atualizarIndicadorStatus(sucesso) {
    // Atualizar badge visual se existir
    const badge = document.querySelector('.badge.bg-success, .badge.bg-warning');
    if (badge) {
        if (sucesso) {
            badge.className = 'badge bg-success ms-2';
            badge.textContent = 'API BCB ✓';
        } else {
            badge.className = 'badge bg-warning text-dark ms-2';
            badge.textContent = 'Estimativa';
        }
    }
}

// ============================================
// FORMATAÇÃO DE VALORES MONETÁRIOS
// ============================================

function initMoneyInputs() {
    document.querySelectorAll('.money-input').forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            value = (parseInt(value) / 100).toFixed(2);
            if (!isNaN(value)) {
                e.target.value = formatMoney(value);
            }
        });
        
        input.addEventListener('blur', function(e) {
            if (e.target.value === '') {
                e.target.value = '0,00';
            }
        });
    });
}

function formatMoney(value) {
    const num = parseFloat(value);
    if (isNaN(num)) return '0,00';
    return num.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function parseMoney(value) {
    if (!value) return 0;
    return parseFloat(value.replace(/\./g, '').replace(',', '.'));
}

// ============================================
// DATAS - EVENTOS E VALIDAÇÃO
// ============================================

function initDateDefaults() {
    // Não preenche datas automaticamente - usuário deve escolher
    // Apenas adiciona evento para abrir datepicker no focus
    const allDateInputs = [
        'completoDataFinal', 'correcaoDataFinal', 'jurosDataFinal',
        'completoDataInicial', 'correcaoDataInicial', 'jurosDataInicial'
    ];
    
    allDateInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            // Abrir datepicker automaticamente ao focar
            el.addEventListener('focus', function() {
                try {
                    this.showPicker();
                } catch (e) {
                    // showPicker() não suportado em alguns navegadores
                    this.click();
                }
            });
        }
    });
}

// Valida se as datas estão preenchidas
function validarDatas(dataInicialId, dataFinalId) {
    const dataInicial = document.getElementById(dataInicialId)?.value;
    const dataFinal = document.getElementById(dataFinalId)?.value;
    
    if (!dataInicial || !dataFinal) {
        const campoVazio = !dataInicial ? 'Data Inicial' : 'Data Final';
        return { valido: false, erro: `Por favor, preencha o campo "${campoVazio}"` };
    }
    
    if (new Date(dataInicial) > new Date(dataFinal)) {
        return { valido: false, erro: 'A Data Inicial não pode ser posterior à Data Final' };
    }
    
    return { valido: true };
}

// ============================================
// HANDLERS DOS FORMULÁRIOS
// ============================================

function initFormHandlers() {
    console.log('[CALCULATOR] Registrando handlers de formulários...');
    
    // Cálculo Completo
    const formCompleto = document.getElementById('formCompleto');
    console.log('[CALCULATOR] formCompleto encontrado:', !!formCompleto);
    formCompleto?.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('[CALCULATOR] Submit formCompleto');
        await calcularCompleto();
    });
    
    // Correção Monetária
    const formCorrecao = document.getElementById('formCorrecao');
    console.log('[CALCULATOR] formCorrecao encontrado:', !!formCorrecao);
    formCorrecao?.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('[CALCULATOR] Submit formCorrecao');
        await calcularCorrecao();
    });
    
    // Juros
    const formJuros = document.getElementById('formJuros');
    console.log('[CALCULATOR] formJuros encontrado:', !!formJuros);
    formJuros?.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('[CALCULATOR] Submit formJuros');
        await calcularJuros();
    });
    
    // Honorários
    const formHonorarios = document.getElementById('formHonorarios');
    console.log('[CALCULATOR] formHonorarios encontrado:', !!formHonorarios);
    formHonorarios?.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('[CALCULATOR] Submit formHonorarios');
        await calcularHonorarios();
    });
}

// ============================================
// CAMPOS DINÂMICOS
// ============================================

function initDynamicFields() {
    // Toggle campos de honorários
    document.getElementById('honorariosTipo')?.addEventListener('change', function(e) {
        const percentualGroup = document.getElementById('percentualGroup');
        const valorFixoGroup = document.getElementById('valorFixoGroup');
        
        // Esconder todos
        percentualGroup.style.display = 'none';
        valorFixoGroup.style.display = 'none';
        
        switch(e.target.value) {
            case 'contratual':
            case 'ad_exitum':
            case 'sucumbencia':
                percentualGroup.style.display = 'block';
                break;
            case 'fixo':
                valorFixoGroup.style.display = 'block';
                break;
        }
    });
    
    // Toggle SELIC (já inclui correção)
    document.getElementById('completoIndice')?.addEventListener('change', function(e) {
        const jurosSwitch = document.getElementById('completoAplicarJuros');
        const jurosLabel = jurosSwitch?.parentElement.querySelector('label');
        
        if (e.target.value === 'SELIC') {
            jurosSwitch.checked = false;
            jurosSwitch.disabled = true;
            if (jurosLabel) {
                jurosLabel.textContent = 'SELIC já inclui correção + juros';
            }
        } else {
            jurosSwitch.disabled = false;
            jurosSwitch.checked = true;
            if (jurosLabel) {
                jurosLabel.textContent = 'Aplicar juros';
            }
        }
    });
}

// ============================================
// EXIBIÇÃO DE RESULTADO INLINE (abaixo do botão)
// ============================================

function mostrarResultadoInline(containerId, valorFinal, detalhes, parametros) {
    const container = document.getElementById(containerId);
    
    // Debug: listar todos os containers de resultado
    const allContainers = document.querySelectorAll('.resultado-inline');
    console.log('[CALCULATOR] Containers disponíveis:', Array.from(allContainers).map(c => c.id));
    
    if (!container) {
        console.error('[CALCULATOR] Container não encontrado:', containerId);
        // Tentar encontrar o container dentro da tab ativa
        const activePane = document.querySelector('.tab-pane.active');
        const altContainer = activePane?.querySelector('.resultado-inline');
        if (altContainer) {
            console.log('[CALCULATOR] Usando container alternativo:', altContainer.id);
            return mostrarResultadoInline(altContainer.id, valorFinal, detalhes, parametros);
        }
        return;
    }
    
    container.style.display = 'block';
    container.innerHTML = `
        <div class="resultado-card mt-3 p-3 bg-primary-subtle rounded border border-primary">
            <div class="text-center mb-3">
                <small class="text-muted d-block">VALOR TOTAL</small>
                <span class="display-6 fw-bold text-primary">${formatCurrency(valorFinal)}</span>
            </div>
            <div class="detalhes-calculo small">
                ${detalhes}
            </div>
            <div class="mt-2 pt-2 border-top small text-muted">
                ${parametros}
            </div>
            <div class="mt-2">
                <button type="button" class="btn btn-sm btn-primary w-100" onclick="copiarResultadoInline(this)">
                    <i class="fas fa-copy me-1"></i>Copiar
                </button>
            </div>
        </div>
    `;
    
    // Scroll suave para resultado (com try/catch para não travar)
    try {
        container.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (e) {
        console.warn('[CALCULATOR] Erro no scroll:', e);
    }
    
    console.log('[CALCULATOR] ✅ Resultado exibido com sucesso!');
}

function mostrarErroInline(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.style.display = 'block';
    container.innerHTML = `
        <div class="alert alert-danger mt-3 small">
            <i class="fas fa-exclamation-circle me-1"></i>${message}
        </div>
    `;
}

function copiarResultadoInline(btn) {
    const card = btn.closest('.resultado-card');
    const texto = card.innerText.replace('Copiar', '').trim();
    
    navigator.clipboard.writeText(texto).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check me-1"></i>Copiado!';
        setTimeout(() => btn.innerHTML = originalText, 2000);
    });
}

// Manter compatibilidade (agora usa inline)
function mostrarResultadoLateral(valorFinal, detalhes, parametros) {
    // Detecta qual aba está ativa e mostra no container correto
    const activeTab = document.querySelector('.calculator-nav .nav-link.active');
    let containerId = 'resultadoCompleto';
    
    if (activeTab) {
        const tabId = activeTab.id;
        console.log('[CALCULATOR] Tab ativa:', tabId);
        if (tabId.includes('correcao')) containerId = 'resultadoCorrecao';
        else if (tabId.includes('juros')) containerId = 'resultadoJuros';
        else if (tabId.includes('honorarios')) containerId = 'resultadoHonorarios';
    }
    
    console.log('[CALCULATOR] Mostrando resultado em:', containerId);
    mostrarResultadoInline(containerId, valorFinal, detalhes, parametros);
}

function mostrarErroLateral(message) {
    const activeTab = document.querySelector('.calculator-nav .nav-link.active');
    let containerId = 'resultadoCompleto';
    
    if (activeTab) {
        const tabId = activeTab.id;
        if (tabId.includes('correcao')) containerId = 'resultadoCorrecao';
        else if (tabId.includes('juros')) containerId = 'resultadoJuros';
        else if (tabId.includes('honorarios')) containerId = 'resultadoHonorarios';
    }
    
    mostrarErroInline(containerId, message);
}

// ============================================
// FUNÇÕES DE CÁLCULO (LOCAL - SEM CHAMADA API)
// ============================================

async function calcularCompleto() {
    console.log('[CALCULATOR] calcularCompleto() iniciado');
    
    const btn = document.querySelector('#formCompleto button[type="submit"]');
    const indiceSelect = document.getElementById('completoIndice');
    const tipoJurosSelect = document.getElementById('completoTipoJuros');
    
    // Validar datas antes de continuar
    const validacao = validarDatas('completoDataInicial', 'completoDataFinal');
    if (!validacao.valido) {
        mostrarErroInline('resultadoCompleto', validacao.erro);
        return;
    }
    
    // Coletar dados do formulário
    const valor = parseMoney(document.getElementById('completoValor').value);
    const dataInicial = document.getElementById('completoDataInicial').value;
    const dataFinal = document.getElementById('completoDataFinal').value;
    const indice = indiceSelect.value;
    const tipoJuros = tipoJurosSelect.value;
    const aplicarJuros = document.getElementById('completoAplicarJuros').checked;
    
    console.log('[CALCULATOR] Dados:', { valor, dataInicial, dataFinal, indice, aplicarJuros });
    
    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculando...';
        
        // Aguardar índices se ainda estão carregando
        if (indicesCarregando) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Aguardando índices...';
            await aguardarIndices();
        }
        
        // Verificar se temos índices
        if (!indicesBCB) {
            indicesBCB = getIndicesFallback();
        }
        
        // Calcular localmente
        const resultado = calcularCorrecaoLocal(valor, dataInicial, dataFinal, indice, aplicarJuros, tipoJuros);
        
        console.log('[CALCULATOR] Resultado local:', resultado);
        
        // Exibir resultado
        const r = resultado;
        
        const detalhes = `
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Valor Original:</span>
                <strong>${formatCurrency(r.valor_original)}</strong>
            </div>
            <div class="d-flex justify-content-between mb-2 text-info">
                <span>Correção (${r.indice}):</span>
                <strong>+ ${formatCurrency(r.correcao_monetaria)}</strong>
            </div>
            ${r.juros > 0 ? `
            <div class="d-flex justify-content-between mb-2 text-warning">
                <span>Juros:</span>
                <strong>+ ${formatCurrency(r.juros)}</strong>
            </div>
            ` : ''}
            <hr>
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Período:</span>
                <span>${formatDate(r.data_inicial)} a ${formatDate(r.data_final)}</span>
            </div>
            <div class="d-flex justify-content-between">
                <span class="text-muted">Acréscimo Total:</span>
                <strong class="text-primary">${r.percentual_total.toFixed(2)}%</strong>
            </div>
        `;
        
        const parametros = `
            <div><i class="fas fa-chart-line text-primary me-1"></i> <strong>Índice:</strong> ${r.indice}</div>
            <div><i class="fas fa-calculator text-primary me-1"></i> <strong>Fator:</strong> ${r.fator_correcao.toFixed(6)}</div>
            ${r.juros > 0 ? `<div><i class="fas fa-percentage text-primary me-1"></i> <strong>Juros:</strong> ${tipoJurosSelect.options[tipoJurosSelect.selectedIndex].text}</div>` : ''}
            <div class="mt-2 ${r.fonte === 'BCB' ? 'text-info' : 'text-warning'} small">
                <i class="fas fa-${r.fonte === 'BCB' ? 'check-circle' : 'exclamation-triangle'} me-1"></i> 
                Fonte: ${r.fonte === 'BCB' ? 'Banco Central do Brasil' : 'Valores estimados'}
            </div>
        `;
        
        mostrarResultadoLateral(r.valor_final, detalhes, parametros);
        
        console.log('[CALCULATOR] ✅ Cálculo completo finalizado com sucesso!');
        
    } catch (error) {
        console.error('[CALCULATOR] Erro:', error);
        mostrarErroLateral('Erro ao calcular: ' + error.message);
    } finally {
        console.log('[CALCULATOR] Finally: restaurando botão');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-calculator me-2"></i>Calcular';
    }
}

// Aguarda índices carregarem (max 5 segundos)
function aguardarIndices() {
    return new Promise((resolve) => {
        let tentativas = 0;
        const interval = setInterval(() => {
            tentativas++;
            if (!indicesCarregando || tentativas > 50) {
                clearInterval(interval);
                resolve();
            }
        }, 100);
    });
}

// Cálculo local usando índices pré-carregados
function calcularCorrecaoLocal(valor, dataInicial, dataFinal, indice, aplicarJuros = false, tipoJuros = 'simples_1') {
    const dtInicial = new Date(dataInicial);
    const dtFinal = new Date(dataFinal);
    
    // Calcular meses entre datas
    const meses = ((dtFinal.getFullYear() - dtInicial.getFullYear()) * 12) + 
                  (dtFinal.getMonth() - dtInicial.getMonth()) +
                  (dtFinal.getDate() - dtInicial.getDate()) / 30;
    
    // Obter taxa do índice (pode vir como taxa_mensal ou ultimo_valor)
    const dadosIndice = indicesBCB[indice] || indicesBCB['IPCA'] || getIndicesFallback()['IPCA'];
    
    // Verificar qual campo tem o valor da taxa
    let taxaMensalPercent = dadosIndice.taxa_mensal || dadosIndice.ultimo_valor || 0.40;
    const taxaMensal = taxaMensalPercent / 100;
    const fonte = dadosIndice.fonte || dadosIndice.status || 'Estimativa';
    
    console.log('[CALCULATOR] Índice:', indice, 'Taxa:', taxaMensalPercent, '% Meses:', meses.toFixed(1));
    
    // Calcular fator de correção (juros compostos)
    const fatorCorrecao = Math.pow(1 + taxaMensal, meses);
    const valorCorrigido = valor * fatorCorrecao;
    const correcaoMonetaria = valorCorrigido - valor;
    
    // Calcular juros se aplicável
    let juros = 0;
    if (aplicarJuros && indice !== 'SELIC') {
        juros = calcularJurosLocal(valorCorrigido, meses, tipoJuros);
    }
    
    const valorFinal = valorCorrigido + juros;
    const percentualTotal = ((valorFinal - valor) / valor) * 100;
    
    // Determinar fonte (BCB se veio da API, senão Estimativa)
    const fonteReal = (fonte === 'BCB' || fonte === 'disponivel') ? 'BCB' : 'Estimativa';
    
    return {
        valor_original: valor,
        valor_corrigido: valorCorrigido,
        correcao_monetaria: correcaoMonetaria,
        juros: juros,
        valor_final: valorFinal,
        fator_correcao: fatorCorrecao,
        percentual_total: percentualTotal,
        meses: meses,
        indice: dadosIndice.nome || indice,
        data_inicial: dataInicial,
        data_final: dataFinal,
        fonte: fonteReal
    };
}

// Calcular juros localmente
function calcularJurosLocal(valorBase, meses, tipoJuros) {
    const taxas = {
        'simples_1': 0.01,      // 1% ao mês
        'simples_0.5': 0.005,   // 0.5% ao mês  
        'composto_1': 0.01,     // 1% ao mês composto
        'legal': 0.01           // Taxa legal 1% ao mês
    };
    
    const taxa = taxas[tipoJuros] || 0.01;
    
    if (tipoJuros.includes('composto')) {
        return valorBase * (Math.pow(1 + taxa, meses) - 1);
    } else {
        return valorBase * taxa * meses;
    }
}

async function calcularCorrecao() {
    const btn = document.querySelector('#formCorrecao button[type="submit"]');
    const indiceSelect = document.getElementById('correcaoIndice');
    
    // Validar datas antes de continuar
    const validacao = validarDatas('correcaoDataInicial', 'correcaoDataFinal');
    if (!validacao.valido) {
        mostrarErroInline('resultadoCorrecao', validacao.erro);
        return;
    }
    
    const valor = parseMoney(document.getElementById('correcaoValor').value);
    const dataInicial = document.getElementById('correcaoDataInicial').value;
    const dataFinal = document.getElementById('correcaoDataFinal').value;
    const indice = indiceSelect.value;
    
    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculando...';
        
        // Aguardar índices se ainda estão carregando
        if (indicesCarregando) {
            await aguardarIndices();
        }
        
        if (!indicesBCB) {
            indicesBCB = getIndicesFallback();
        }
        
        // Calcular localmente (sem juros)
        const r = calcularCorrecaoLocal(valor, dataInicial, dataFinal, indice, false);
        
        const detalhes = `
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Valor Original:</span>
                <strong>${formatCurrency(r.valor_original)}</strong>
            </div>
            <div class="d-flex justify-content-between mb-2 text-info">
                <span>Correção:</span>
                <strong>+ ${formatCurrency(r.correcao_monetaria)} (${r.percentual_total.toFixed(2)}%)</strong>
            </div>
            <hr>
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Período:</span>
                <span>${formatDate(r.data_inicial)} a ${formatDate(r.data_final)}</span>
            </div>
            <div class="d-flex justify-content-between">
                <span class="text-muted">Meses:</span>
                <span>${r.meses.toFixed(1)}</span>
            </div>
        `;
        
        const parametros = `
            <div><i class="fas fa-chart-line text-primary me-1"></i> <strong>Índice:</strong> ${r.indice}</div>
            <div><i class="fas fa-calculator text-primary me-1"></i> <strong>Fator:</strong> ${r.fator_correcao.toFixed(6)}</div>
            <div class="mt-2 ${r.fonte === 'BCB' ? 'text-info' : 'text-warning'} small">
                <i class="fas fa-${r.fonte === 'BCB' ? 'check-circle' : 'exclamation-triangle'} me-1"></i> 
                Fonte: ${r.fonte === 'BCB' ? 'Banco Central do Brasil' : 'Valores estimados'}
            </div>
        `;
        
        mostrarResultadoLateral(r.valor_final, detalhes, parametros);
        
    } catch (error) {
        console.error('[CALCULATOR] Erro:', error);
        mostrarErroLateral('Erro ao calcular: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-calculator me-2"></i>Calcular Correção';
    }
}

async function calcularJuros() {
    const btn = document.querySelector('#formJuros button[type="submit"]');
    const tipoJurosSelect = document.getElementById('jurosTipo');
    
    // Validar datas antes de continuar
    const validacao = validarDatas('jurosDataInicial', 'jurosDataFinal');
    if (!validacao.valido) {
        mostrarErroInline('resultadoJuros', validacao.erro);
        return;
    }
    
    const valor = parseMoney(document.getElementById('jurosValor').value);
    const dataInicial = document.getElementById('jurosDataInicial').value;
    const dataFinal = document.getElementById('jurosDataFinal').value;
    const tipoJuros = tipoJurosSelect.value;
    
    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculando...';
        
        // Calcular período
        const dtInicial = new Date(dataInicial);
        const dtFinal = new Date(dataFinal);
        const meses = ((dtFinal.getFullYear() - dtInicial.getFullYear()) * 12) + 
                      (dtFinal.getMonth() - dtInicial.getMonth()) +
                      (dtFinal.getDate() - dtInicial.getDate()) / 30;
        const dias = Math.floor((dtFinal - dtInicial) / (1000 * 60 * 60 * 24));
        
        // Calcular juros
        const juros = calcularJurosLocal(valor, meses, tipoJuros);
        const valorFinal = valor + juros;
        const percentual = (juros / valor) * 100;
        
        // Taxa mensal baseada no tipo
        const taxas = { 'simples_1': 1, 'simples_0.5': 0.5, 'composto_1': 1, 'legal': 1 };
        const taxaMensal = taxas[tipoJuros] || 1;
        
        const detalhes = `
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Valor Principal:</span>
                <strong>${formatCurrency(valor)}</strong>
            </div>
            <div class="d-flex justify-content-between mb-2 text-warning">
                <span>Juros:</span>
                <strong>+ ${formatCurrency(juros)} (${percentual.toFixed(2)}%)</strong>
            </div>
            <hr>
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Período:</span>
                <span>${meses.toFixed(1)} meses (${dias} dias)</span>
            </div>
        `;
        
        const parametros = `
            <div><i class="fas fa-percentage text-primary me-1"></i> <strong>Taxa:</strong> ${taxaMensal}% ao mês</div>
            <div><i class="fas fa-gavel text-primary me-1"></i> <strong>Base:</strong> ${tipoJurosSelect.options[tipoJurosSelect.selectedIndex].text}</div>
            <div class="mt-2 text-muted small"><i class="fas fa-info-circle me-1"></i> ${tipoJuros.includes('composto') ? 'Juros compostos' : 'Juros simples'}</div>
        `;
        
        mostrarResultadoLateral(valorFinal, detalhes, parametros);
        
    } catch (error) {
        console.error('[CALCULATOR] Erro:', error);
        mostrarErroLateral('Erro ao calcular: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-calculator me-2"></i>Calcular Juros';
    }
}

async function calcularHonorarios() {
    const btn = document.querySelector('#formHonorarios button[type="submit"]');
    const tipoHonorario = document.getElementById('honorariosTipo').value;
    
    const valorCausa = parseMoney(document.getElementById('honorariosValorCausa').value);
    const percentual = parseFloat(document.getElementById('honorariosPercentual').value) || 20;
    const valorFixo = parseMoney(document.getElementById('honorariosValorFixo')?.value || '0');
    
    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculando...';
        
        // Calcular honorários localmente
        let honorarios = 0;
        let descricao = '';
        
        switch (tipoHonorario) {
            case 'contratual':
                honorarios = valorCausa * (percentual / 100);
                descricao = 'Honorários Contratuais';
                break;
            case 'ad_exitum':
                honorarios = valorCausa * (percentual / 100);
                descricao = 'Honorários Ad Exitum (êxito)';
                break;
            case 'sucumbencia':
                honorarios = valorCausa * (percentual / 100);
                descricao = 'Honorários Sucumbenciais';
                break;
            case 'fixo':
                honorarios = valorFixo;
                descricao = 'Honorários Fixos';
                break;
            default:
                honorarios = valorCausa * 0.20;
                descricao = 'Honorários (20% padrão)';
        }
        
        const detalhes = `
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Valor da Causa:</span>
                <strong>${formatCurrency(valorCausa)}</strong>
            </div>
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Tipo:</span>
                <span>${descricao}</span>
            </div>
            ${tipoHonorario !== 'fixo' ? `
            <div class="d-flex justify-content-between mb-2">
                <span class="text-muted">Percentual:</span>
                <strong>${percentual}%</strong>
            </div>
            ` : ''}
        `;
        
        const parametros = `
            <div><i class="fas fa-gavel text-primary me-1"></i> <strong>Base Legal:</strong> Art. 22, EOAB</div>
            <div class="mt-2 text-muted small"><i class="fas fa-info-circle me-1"></i> Consulte a tabela OAB local</div>
        `;
        
        mostrarResultadoLateral(honorarios, detalhes, parametros);
        
    } catch (error) {
        console.error('[CALCULATOR] Erro:', error);
        mostrarErroLateral('Erro ao calcular: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-calculator me-2"></i>Calcular Honorários';
    }
}

// ============================================
// UTILITÁRIOS
// ============================================

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const [year, month, day] = dateStr.split('-');
    return `${day}/${month}/${year}`;
}

function copiarResultado() {
    const valorEl = document.getElementById('resultadoValorFinal');
    if (!valorEl) return;
    
    navigator.clipboard.writeText(valorEl.textContent).then(() => {
        showToast('Valor copiado: ' + valorEl.textContent);
    });
}

function showToast(message) {
    const toastEl = document.getElementById('calculatorToast');
    const messageEl = document.getElementById('toastMessage');
    
    if (toastEl && messageEl) {
        messageEl.textContent = message;
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || 
           document.querySelector('input[name="csrf_token"]')?.value || '';
}
