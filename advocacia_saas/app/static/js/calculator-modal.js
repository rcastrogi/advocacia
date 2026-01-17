/**
 * Calculadora Modal - Popup Flutuante
 * Permite calcular correção monetária, juros e honorários de qualquer página
 */

(function() {
    'use strict';
    
    // Estado global
    let indicesCarregados = null;
    let indicesCarregando = false;
    let modalAberto = false;
    let tabAtiva = 'completo';
    
    // Estado para arrastar
    let isDragging = false;
    let dragOffset = { x: 0, y: 0 };
    
    // Índices fallback (caso API falhe)
    const INDICES_FALLBACK = {
        'IPCA': { nome: 'IPCA', taxa_mensal: 0.40 },
        'INPC': { nome: 'INPC', taxa_mensal: 0.45 },
        'IGPM': { nome: 'IGP-M', taxa_mensal: 0.50 },
        'TR': { nome: 'TR', taxa_mensal: 0.10 },
        'SELIC': { nome: 'SELIC', taxa_mensal: 0.85 }
    };
    
    // Inicializar quando DOM estiver pronto
    document.addEventListener('DOMContentLoaded', init);
    
    function init() {
        // Só inicializa se existe o modal
        if (!document.getElementById('calculatorModal')) return;
        
        // Event listeners
        document.getElementById('calculatorModalOverlay').addEventListener('click', fecharModal);
        document.getElementById('calculatorModalClose').addEventListener('click', fecharModal);
        
        // Tabs
        document.querySelectorAll('.calc-tab').forEach(tab => {
            tab.addEventListener('click', () => trocarTab(tab.dataset.tab));
        });
        
        // Toggle índices
        document.getElementById('indicesToggle')?.addEventListener('click', toggleIndices);
        
        // Form submit
        document.getElementById('calcModalForm').addEventListener('submit', calcular);
        
        // Botão copiar
        document.getElementById('btnCopiarModal')?.addEventListener('click', copiarResultado);
        
        // Datepicker automático
        document.querySelectorAll('#calculatorModal input[type="date"]').forEach(input => {
            input.addEventListener('focus', function() {
                try { this.showPicker(); } catch(e) { this.click(); }
            });
        });
        
        // Formatação monetária nos campos de valor
        document.querySelectorAll('#calculatorModal input[data-money]').forEach(input => {
            input.addEventListener('input', formatarCampoMonetario);
            input.addEventListener('focus', function() {
                // Posicionar cursor no final
                const len = this.value.length;
                this.setSelectionRange(len, len);
            });
        });
        
        // Inicializar arrastar
        initDrag();
        
        // Pré-carregar índices
        carregarIndices();
        
        // Atalho de teclado (Ctrl+Shift+C)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'C') {
                e.preventDefault();
                toggleModal();
            }
        });
    }
    
    // Formatar campo monetário em tempo real
    function formatarCampoMonetario(e) {
        const input = e.target;
        let value = input.value;
        
        // Salvar posição do cursor
        const cursorPos = input.selectionStart;
        const oldLength = value.length;
        
        // Remove tudo que não é número
        value = value.replace(/\D/g, '');
        
        // Se vazio, limpa
        if (!value) {
            input.value = '';
            return;
        }
        
        // Limitar a 12 dígitos (até 9.999.999.999,99)
        if (value.length > 12) {
            value = value.substring(0, 12);
        }
        
        // Converte para número (centavos)
        let numero = parseInt(value, 10);
        
        // Formata como moeda brasileira
        let formatted = (numero / 100).toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        
        input.value = formatted;
        
        // Reposicionar cursor
        const newLength = formatted.length;
        const diff = newLength - oldLength;
        const newPos = Math.max(0, cursorPos + diff);
        
        // Mover cursor para o final se estava no final
        if (cursorPos >= oldLength - 1) {
            input.setSelectionRange(newLength, newLength);
        } else {
            input.setSelectionRange(newPos, newPos);
        }
    }
    
    // ========================================
    // ARRASTAR MODAL
    // ========================================
    
    function initDrag() {
        const modal = document.getElementById('calculatorModal');
        const header = document.querySelector('.calculator-modal-header');
        
        if (!modal || !header) return;
        
        header.addEventListener('mousedown', startDrag);
        header.addEventListener('touchstart', startDrag, { passive: false });
        
        document.addEventListener('mousemove', drag);
        document.addEventListener('touchmove', drag, { passive: false });
        
        document.addEventListener('mouseup', stopDrag);
        document.addEventListener('touchend', stopDrag);
    }
    
    function startDrag(e) {
        // Não arrastar se clicar no botão de fechar
        if (e.target.closest('.btn-close')) return;
        
        const modal = document.getElementById('calculatorModal');
        const rect = modal.getBoundingClientRect();
        
        isDragging = true;
        
        const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;
        
        dragOffset.x = clientX - rect.left;
        dragOffset.y = clientY - rect.top;
        
        modal.style.transition = 'none';
        
        if (e.type === 'touchstart') {
            e.preventDefault();
        }
    }
    
    function drag(e) {
        if (!isDragging) return;
        
        const modal = document.getElementById('calculatorModal');
        
        const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
        
        let newX = clientX - dragOffset.x;
        let newY = clientY - dragOffset.y;
        
        // Limitar dentro da tela
        const maxX = window.innerWidth - modal.offsetWidth;
        const maxY = window.innerHeight - modal.offsetHeight;
        
        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));
        
        // Aplicar posição (usando left/top ao invés de right/bottom)
        modal.style.right = 'auto';
        modal.style.bottom = 'auto';
        modal.style.left = newX + 'px';
        modal.style.top = newY + 'px';
        
        if (e.type === 'touchmove') {
            e.preventDefault();
        }
    }
    
    function stopDrag() {
        if (!isDragging) return;
        
        isDragging = false;
        
        const modal = document.getElementById('calculatorModal');
        modal.style.transition = '';
    }
    
    function toggleModal() {
        if (modalAberto) {
            fecharModal();
        } else {
            abrirModal();
        }
    }
    
    function abrirModal() {
        const modal = document.getElementById('calculatorModal');
        
        // Resetar posição para o padrão
        modal.style.left = '';
        modal.style.top = '';
        modal.style.right = '24px';
        modal.style.bottom = '90px';
        
        document.getElementById('calculatorModalOverlay').classList.add('show');
        modal.classList.add('show');
        modalAberto = true;
        
        // Inicializar na aba "completo"
        trocarTab('completo');
        
        // Foco no primeiro input
        setTimeout(() => {
            document.getElementById('calcModalValor')?.focus();
        }, 300);
    }
    
    function fecharModal() {
        document.getElementById('calculatorModalOverlay').classList.remove('show');
        document.getElementById('calculatorModal').classList.remove('show');
        modalAberto = false;
    }
    
    function trocarTab(tab) {
        tabAtiva = tab;
        
        // Atualizar visual das tabs
        document.querySelectorAll('.calc-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        
        // Mostrar/esconder campos específicos
        const jurosGroup = document.getElementById('jurosGroup');
        const indiceGroup = document.getElementById('indiceGroup');
        const honorariosFields = document.getElementById('honorariosFields');
        const camposCalculo = document.getElementById('camposCalculo');
        
        // Reset visibility
        jurosGroup.style.display = 'none';
        indiceGroup.style.display = 'block';
        honorariosFields.style.display = 'none';
        camposCalculo.style.display = 'block';
        
        if (tab === 'completo') {
            jurosGroup.style.display = 'block';
        } else if (tab === 'juros') {
            indiceGroup.style.display = 'none';
            jurosGroup.style.display = 'block';
        } else if (tab === 'honorarios') {
            camposCalculo.style.display = 'none';
            honorariosFields.style.display = 'block';
        }
        
        // Limpar resultado
        document.getElementById('resultadoModal').classList.remove('show');
        document.getElementById('erroModal').classList.remove('show');
    }
    
    function toggleIndices() {
        const panel = document.getElementById('indicesPanel');
        const toggle = document.getElementById('indicesToggle');
        
        panel.classList.toggle('show');
        toggle.classList.toggle('expanded');
    }
    
    async function carregarIndices() {
        if (indicesCarregados || indicesCarregando) return;
        
        indicesCarregando = true;
        
        try {
            const response = await fetch('/calculadora/api/indices', {
                headers: { 'X-CSRFToken': getCsrfToken() }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.indices) {
                    indicesCarregados = data.indices;
                    atualizarPainelIndices();
                }
            }
        } catch (error) {
            console.warn('[CalcModal] Erro ao carregar índices, usando fallback');
            indicesCarregados = INDICES_FALLBACK;
        } finally {
            indicesCarregando = false;
        }
    }
    
    function atualizarPainelIndices() {
        const panel = document.getElementById('indicesPanel');
        if (!panel || !indicesCarregados) return;
        
        let html = '';
        for (const [key, info] of Object.entries(indicesCarregados)) {
            const taxa = info.taxa_mensal || info.ultimo_valor || 0;
            html += `
                <div class="indice-item">
                    <span class="indice-nome">${key}</span>
                    <span class="indice-valor">${taxa.toFixed(2)}% a.m.</span>
                </div>
            `;
        }
        panel.innerHTML = html;
    }
    
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
    
    async function calcular(e) {
        e.preventDefault();
        
        const btn = document.getElementById('btnCalcularModal');
        const resultado = document.getElementById('resultadoModal');
        const erro = document.getElementById('erroModal');
        
        // Esconder mensagens anteriores
        resultado.classList.remove('show');
        erro.classList.remove('show');
        
        // Validar datas
        if (tabAtiva !== 'honorarios') {
            const dataInicial = document.getElementById('calcModalDataInicial').value;
            const dataFinal = document.getElementById('calcModalDataFinal').value;
            
            if (!dataInicial || !dataFinal) {
                mostrarErro('Por favor, preencha as datas');
                return;
            }
            
            if (new Date(dataInicial) > new Date(dataFinal)) {
                mostrarErro('A Data Inicial não pode ser posterior à Data Final');
                return;
            }
        }
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Calculando...';
        
        try {
            // Garantir que temos índices
            if (!indicesCarregados) {
                indicesCarregados = INDICES_FALLBACK;
            }
            
            let resultadoCalculo;
            
            if (tabAtiva === 'honorarios') {
                resultadoCalculo = calcularHonorarios();
            } else {
                resultadoCalculo = calcularCorrecaoJuros();
            }
            
            mostrarResultado(resultadoCalculo);
            
        } catch (error) {
            console.error('[CalcModal] Erro:', error);
            mostrarErro('Erro ao calcular: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-calculator me-1"></i>Calcular';
        }
    }
    
    function calcularCorrecaoJuros() {
        const valor = parseMoney(document.getElementById('calcModalValor').value);
        const dataInicial = document.getElementById('calcModalDataInicial').value;
        const dataFinal = document.getElementById('calcModalDataFinal').value;
        const indice = document.getElementById('calcModalIndice').value;
        const aplicarJuros = document.getElementById('calcModalJuros')?.checked || tabAtiva === 'juros';
        const tipoJuros = document.getElementById('calcModalTipoJuros')?.value || 'simples_1';
        
        // Calcular período
        const dtInicial = new Date(dataInicial);
        const dtFinal = new Date(dataFinal);
        const meses = ((dtFinal.getFullYear() - dtInicial.getFullYear()) * 12) + 
                      (dtFinal.getMonth() - dtInicial.getMonth()) +
                      (dtFinal.getDate() - dtInicial.getDate()) / 30;
        
        // Correção monetária
        let correcao = 0;
        let fator = 1;
        let fonte = 'Fallback';
        
        if (tabAtiva !== 'juros') {
            const indiceInfo = indicesCarregados[indice] || INDICES_FALLBACK[indice];
            const taxaMensal = (indiceInfo?.taxa_mensal || indiceInfo?.ultimo_valor || 0.5) / 100;
            fator = Math.pow(1 + taxaMensal, meses);
            correcao = valor * (fator - 1);
            fonte = indiceInfo ? 'BCB' : 'Estimado';
        }
        
        // Juros
        let juros = 0;
        if (aplicarJuros) {
            const taxas = { 'simples_1': 1, 'simples_0.5': 0.5, 'composto_1': 1, 'legal': 1 };
            const taxaMensalJuros = (taxas[tipoJuros] || 1) / 100;
            
            if (tipoJuros.includes('composto')) {
                juros = (valor + correcao) * (Math.pow(1 + taxaMensalJuros, meses) - 1);
            } else {
                juros = (valor + correcao) * taxaMensalJuros * meses;
            }
        }
        
        const valorFinal = valor + correcao + juros;
        const percentualTotal = ((valorFinal / valor) - 1) * 100;
        
        return {
            tipo: tabAtiva,
            valor_original: valor,
            correcao: correcao,
            juros: juros,
            valor_final: valorFinal,
            percentual: percentualTotal,
            meses: meses,
            indice: indice,
            fator: fator,
            fonte: fonte,
            data_inicial: dataInicial,
            data_final: dataFinal
        };
    }
    
    function calcularHonorarios() {
        const valorCausa = parseMoney(document.getElementById('calcModalValorCausa').value);
        const percentual = parseFloat(document.getElementById('calcModalPercentual').value) || 20;
        
        const honorarios = valorCausa * (percentual / 100);
        
        return {
            tipo: 'honorarios',
            valor_causa: valorCausa,
            percentual: percentual,
            honorarios: honorarios
        };
    }
    
    function mostrarResultado(r) {
        const container = document.getElementById('resultadoModal');
        const valorEl = document.getElementById('resultadoValorModal');
        const detalhesEl = document.getElementById('resultadoDetalhesModal');
        
        if (r.tipo === 'honorarios') {
            valorEl.innerHTML = `<small>HONORÁRIOS</small><div class="valor">${formatCurrency(r.honorarios)}</div>`;
            detalhesEl.innerHTML = `
                <div class="item"><span>Valor da Causa:</span><strong>${formatCurrency(r.valor_causa)}</strong></div>
                <div class="item"><span>Percentual:</span><strong>${r.percentual}%</strong></div>
            `;
        } else {
            valorEl.innerHTML = `<small>VALOR ATUALIZADO</small><div class="valor">${formatCurrency(r.valor_final)}</div>`;
            
            let detalhes = `<div class="item"><span>Valor Original:</span><strong>${formatCurrency(r.valor_original)}</strong></div>`;
            
            if (r.correcao > 0) {
                detalhes += `<div class="item"><span>Correção (${r.indice}):</span><strong style="color:#0891b2">+${formatCurrency(r.correcao)}</strong></div>`;
            }
            if (r.juros > 0) {
                detalhes += `<div class="item"><span>Juros:</span><strong style="color:#d97706">+${formatCurrency(r.juros)}</strong></div>`;
            }
            detalhes += `<div class="item"><span>Acréscimo Total:</span><strong style="color:#663399">${r.percentual.toFixed(2)}%</strong></div>`;
            
            detalhesEl.innerHTML = detalhes;
        }
        
        // Guardar resultado para copiar
        container.dataset.resultado = JSON.stringify(r);
        container.classList.add('show');
    }
    
    function mostrarErro(msg) {
        const erro = document.getElementById('erroModal');
        erro.textContent = msg;
        erro.classList.add('show');
    }
    
    function copiarResultado() {
        const container = document.getElementById('resultadoModal');
        const r = JSON.parse(container.dataset.resultado || '{}');
        
        let texto = '';
        
        if (r.tipo === 'honorarios') {
            texto = `Honorários Advocatícios: ${formatCurrency(r.honorarios)} (${r.percentual}% sobre ${formatCurrency(r.valor_causa)})`;
        } else {
            texto = `Valor atualizado: ${formatCurrency(r.valor_final)}`;
            if (r.correcao > 0) {
                texto += ` (Correção ${r.indice}: ${formatCurrency(r.correcao)}`;
            }
            if (r.juros > 0) {
                texto += ` + Juros: ${formatCurrency(r.juros)}`;
            }
            if (r.correcao > 0 || r.juros > 0) {
                texto += ')';
            }
            texto += ` - Período: ${formatDate(r.data_inicial)} a ${formatDate(r.data_final)}`;
        }
        
        navigator.clipboard.writeText(texto).then(() => {
            const btn = document.getElementById('btnCopiarModal');
            const original = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check me-1"></i>Copiado!';
            setTimeout(() => btn.innerHTML = original, 2000);
        });
    }
    
    // Utilitários
    function parseMoney(value) {
        if (!value) return 0;
        return parseFloat(value.toString().replace(/[^\d,.-]/g, '').replace(',', '.')) || 0;
    }
    
    function formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    }
    
    function formatDate(dateStr) {
        if (!dateStr) return '';
        const [y, m, d] = dateStr.split('-');
        return `${d}/${m}/${y}`;
    }
    
    // Expor função para abrir externamente
    window.abrirCalculadoraModal = abrirModal;
    
})();
