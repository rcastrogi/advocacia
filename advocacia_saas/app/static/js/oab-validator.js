/**
 * Validador de OAB em tempo real
 * Valida formato e consulta informações online
 */

class OABValidator {
    constructor(inputElement, feedbackElement) {
        this.input = inputElement;
        this.feedback = feedbackElement;
        this.debounceTimer = null;
        
        this.init();
    }
    
    init() {
        if (!this.input) return;
        
        // Adicionar evento de input com debounce
        this.input.addEventListener('input', (e) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.validar(e.target.value);
            }, 800);
        });
        
        // Formatar OAB ao perder foco
        this.input.addEventListener('blur', (e) => {
            const valor = e.target.value.trim().toUpperCase();
            if (valor) {
                e.target.value = valor;
            }
        });
    }
    
    async validar(numeroOAB) {
        if (!numeroOAB || numeroOAB.length < 6) {
            this.limparFeedback();
            return;
        }
        
        this.mostrarCarregando();
        
        try {
            const response = await fetch('/api/oab/validar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    numero_oab: numeroOAB
                })
            });
            
            const resultado = await response.json();
            this.mostrarResultado(resultado);
            
        } catch (error) {
            this.mostrarErro('Erro ao validar OAB. Tente novamente.');
            console.error('Erro na validação:', error);
        }
    }
    
    mostrarCarregando() {
        if (!this.feedback) return;
        
        this.feedback.innerHTML = `
            <div class="d-flex align-items-center text-muted">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Validando...</span>
                </div>
                <small>Validando OAB...</small>
            </div>
        `;
        this.feedback.style.display = 'block';
    }
    
    mostrarResultado(resultado) {
        if (!this.feedback) return;
        
        if (resultado.formato_valido) {
            // Formato válido
            let html = `
                <div class="alert alert-success alert-sm mb-0 py-2" role="alert">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>OAB válida!</strong>
                    <div class="small mt-1">
                        <strong>UF:</strong> ${resultado.uf || 'N/A'}
            `;
            
            if (resultado.nome) {
                html += ` | <strong>Nome:</strong> ${resultado.nome}`;
            }
            
            if (resultado.situacao) {
                html += ` | <strong>Situação:</strong> ${resultado.situacao}`;
            }
            
            html += `
                    </div>
                </div>
            `;
            
            this.feedback.innerHTML = html;
            this.input.classList.remove('is-invalid');
            this.input.classList.add('is-valid');
            
        } else {
            // Formato inválido
            this.feedback.innerHTML = `
                <div class="alert alert-danger alert-sm mb-0 py-2" role="alert">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong>OAB inválida!</strong>
                    <div class="small mt-1">${resultado.mensagem}</div>
                </div>
            `;
            
            this.input.classList.remove('is-valid');
            this.input.classList.add('is-invalid');
        }
        
        this.feedback.style.display = 'block';
    }
    
    mostrarErro(mensagem) {
        if (!this.feedback) return;
        
        this.feedback.innerHTML = `
            <div class="alert alert-warning alert-sm mb-0 py-2" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <small>${mensagem}</small>
            </div>
        `;
        this.feedback.style.display = 'block';
    }
    
    limparFeedback() {
        if (!this.feedback) return;
        
        this.feedback.innerHTML = '';
        this.feedback.style.display = 'none';
        this.input.classList.remove('is-valid', 'is-invalid');
    }
}

// Inicializar validador quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    const oabInput = document.getElementById('oab_number');
    const oabFeedback = document.getElementById('oab-feedback');
    
    if (oabInput) {
        new OABValidator(oabInput, oabFeedback);
    }
});
