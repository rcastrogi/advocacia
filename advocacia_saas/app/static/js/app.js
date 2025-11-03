// Main JavaScript file for Petitio

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert-dismissible').fadeOut('slow');
    }, 5000);

    // Add fade-in animation to cards
    $('.card').addClass('fade-in');

    // Smooth scrolling for anchor links
    $('a[href*="#"]').on('click', function(e) {
        if (this.hash !== '') {
            e.preventDefault();
            var hash = this.hash;
            $('html, body').animate({
                scrollTop: $(hash).offset().top - 70
            }, 800);
        }
    });

    // Format phone inputs
    $('input[type="tel"], input[name*="phone"]').on('input', function() {
        let value = this.value.replace(/\D/g, '');
        if (value.length <= 11) {
            if (value.length <= 10) {
                value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
            } else {
                value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
            }
            this.value = value;
        }
    });

    // Format CPF/CNPJ input
    $('input[name*="cpf"], input[name*="cnpj"]').on('input', function() {
        let value = this.value.replace(/\D/g, '');
        if (value.length <= 11) {
            // CPF format
            value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
        } else {
            // CNPJ format
            value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        this.value = value;
    });

    // Format CEP input
    $('input[name*="cep"]').on('input', function() {
        let value = this.value.replace(/\D/g, '');
        if (value.length <= 8) {
            value = value.replace(/(\d{5})(\d{3})/, '$1-$2');
            this.value = value;
        }
    });

    // Auto search CEP when 8 digits are entered
    $('input[name*="cep"]').on('input', function() {
        const cep = this.value.replace(/\D/g, '');
        if (cep.length === 8) {
            searchCEP(cep);
        }
    });
});

// CEP search function
function searchCEP(cep) {
    if (cep.length === 8) {
        // Show loading
        const button = document.getElementById('searchCep');
        if (button) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            button.disabled = true;
        }

        fetch(`/api/cep/${cep}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showAlert('error', data.error);
                } else {
                    console.log('✅ CEP encontrado! Preenchendo e bloqueando campos...');
                    
                    // Get field references
                    const streetField = document.getElementById('street');
                    const neighborhoodField = document.getElementById('neighborhood');
                    const ufField = document.getElementById('uf');
                    const cityField = document.getElementById('city');
                    
                    // Fill street and neighborhood
                    if (streetField && data.street) {
                        streetField.value = data.street;
                        $(streetField).addClass('slide-up');
                    }
                    if (neighborhoodField && data.neighborhood) {
                        neighborhoodField.value = data.neighborhood;
                        $(neighborhoodField).addClass('slide-up');
                    }
                    
                    // Fill UF and trigger city loading
                    if (ufField && data.uf) {
                        ufField.value = data.uf;
                        $(ufField).addClass('slide-up');
                        // Trigger change to load cities
                        ufField.dispatchEvent(new Event('change'));
                    }
                    
                    // Wait for cities to load, then set city and lock fields
                    setTimeout(() => {
                        if (cityField && data.city) {
                            cityField.value = data.city;
                            $(cityField).addClass('slide-up');
                        }
                        
                        // Now lock the fields that came from CEP
                        lockCEPFields(streetField, neighborhoodField, ufField, cityField);
                    }, 600);

                    showAlert('success', 'Endereço preenchido automaticamente!');
                }
            })
            .catch(error => {
                showAlert('error', 'Erro ao buscar CEP');
            })
            .finally(() => {
                // Hide loading
                if (button) {
                    button.innerHTML = '<i class="fas fa-search"></i>';
                    button.disabled = false;
                }
            });
    }
}

// Lock fields filled by CEP API
function lockCEPFields(streetField, neighborhoodField, ufField, cityField) {
    console.log('🔒 Bloqueando campos preenchidos pelo CEP...');
    
    const lockedValues = {
        street: streetField ? streetField.value : '',
        neighborhood: neighborhoodField ? neighborhoodField.value : '',
        uf: ufField ? ufField.value : '',
        city: cityField ? cityField.value : ''
    };
    
    // Function to prevent changes
    const preventChange = function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        showAlert('warning', '⛔ Este campo foi preenchido pelo CEP e está bloqueado. Altere o CEP para desbloquear.');
        return false;
    };
    
    const restoreValue = function(field, value) {
        return function() {
            field.value = value;
        };
    };
    
    // Lock each field
    [streetField, neighborhoodField, ufField, cityField].forEach((field, index) => {
        if (!field) return;
        
        const fieldName = ['street', 'neighborhood', 'uf', 'city'][index];
        const value = lockedValues[fieldName];
        
        // Mark as locked
        field.dataset.cepLocked = 'true';
        field.dataset.lockedValue = value;
        
        // Set readonly/disabled
        if (field.tagName === 'SELECT') {
            field.disabled = true;
        } else {
            field.readOnly = true;
        }
        
        // Style
        field.style.pointerEvents = 'none';
        field.style.cursor = 'not-allowed';
        field.style.backgroundColor = '#e9ecef';
        field.classList.add('cep-locked');
        
        // Add event blockers
        field.addEventListener('keydown', preventChange, true);
        field.addEventListener('keypress', preventChange, true);
        field.addEventListener('paste', preventChange, true);
        field.addEventListener('cut', preventChange, true);
        field.addEventListener('input', restoreValue(field, value), true);
        field.addEventListener('change', restoreValue(field, value), true);
        field.addEventListener('focus', preventChange, true);
        field.addEventListener('mousedown', preventChange, true);
    });
    
    console.log('✅ Campos bloqueados com sucesso!');
}

// Unlock fields when CEP changes
$(document).ready(function() {
    $('input[name*="cep"]').on('input', function() {
        const cepValue = this.value.replace(/\D/g, '');
        
        // If user is typing/changing CEP, unlock fields
        const streetField = document.getElementById('street');
        const neighborhoodField = document.getElementById('neighborhood');
        const ufField = document.getElementById('uf');
        const cityField = document.getElementById('city');
        
        [streetField, neighborhoodField, ufField, cityField].forEach(field => {
            if (field && field.dataset.cepLocked === 'true') {
                console.log('🔓 Desbloqueando campo:', field.id);
                
                // Clone to remove all event listeners
                const newField = field.cloneNode(true);
                field.parentNode.replaceChild(newField, field);
                
                const unlockedField = document.getElementById(newField.id);
                
                // Remove locked state
                delete unlockedField.dataset.cepLocked;
                delete unlockedField.dataset.lockedValue;
                
                // Remove restrictions
                unlockedField.readOnly = false;
                unlockedField.disabled = false;
                unlockedField.style.pointerEvents = '';
                unlockedField.style.cursor = '';
                unlockedField.style.backgroundColor = '';
                unlockedField.classList.remove('cep-locked', 'bg-light');
                
                // Re-attach UF change listener if needed
                if (unlockedField.id === 'uf') {
                    unlockedField.addEventListener('change', function() {
                        const ufValue = this.value;
                        const citySelect = document.getElementById('city');
                        
                        if (!ufValue || !citySelect) return;
                        
                        citySelect.disabled = true;
                        citySelect.innerHTML = '<option value="">Carregando...</option>';
                        
                        fetch(`/api/estados/${ufValue}/cidades`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.error) {
                                    citySelect.innerHTML = '<option value="">Erro</option>';
                                } else {
                                    citySelect.innerHTML = '<option value="">Selecione...</option>';
                                    data.forEach(cidade => {
                                        const option = document.createElement('option');
                                        option.value = cidade.nome;
                                        option.textContent = cidade.nome;
                                        citySelect.appendChild(option);
                                    });
                                    citySelect.disabled = false;
                                }
                            });
                    });
                }
            }
        });
    });
});

// Show alert function
function showAlert(type, message) {
    const alertClass = type === 'error' ? 'alert-danger' : `alert-${type}`;
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Remove existing alerts
    $('.alert').remove();
    
    // Add new alert
    $('.container').first().prepend(alertHtml);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        $('.alert').fadeOut('slow');
    }, 3000);
}

// Form validation helpers
function validateCPF(cpf) {
    cpf = cpf.replace(/\D/g, '');
    if (cpf.length !== 11) return false;
    
    // Check for repeated digits
    if (/^(\d)\1+$/.test(cpf)) return false;
    
    // Validate check digits
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let remainder = 11 - (sum % 11);
    if (remainder === 10 || remainder === 11) remainder = 0;
    if (remainder !== parseInt(cpf.charAt(9))) return false;
    
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    remainder = 11 - (sum % 11);
    if (remainder === 10 || remainder === 11) remainder = 0;
    return remainder === parseInt(cpf.charAt(10));
}

function validateCNPJ(cnpj) {
    cnpj = cnpj.replace(/\D/g, '');
    if (cnpj.length !== 14) return false;
    
    // Check for repeated digits
    if (/^(\d)\1+$/.test(cnpj)) return false;
    
    // Validate check digits
    const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    
    let sum = 0;
    for (let i = 0; i < 12; i++) {
        sum += parseInt(cnpj.charAt(i)) * weights1[i];
    }
    let remainder = sum % 11;
    const checkDigit1 = remainder < 2 ? 0 : 11 - remainder;
    if (checkDigit1 !== parseInt(cnpj.charAt(12))) return false;
    
    sum = 0;
    for (let i = 0; i < 13; i++) {
        sum += parseInt(cnpj.charAt(i)) * weights2[i];
    }
    remainder = sum % 11;
    const checkDigit2 = remainder < 2 ? 0 : 11 - remainder;
    return checkDigit2 === parseInt(cnpj.charAt(13));
}

// File upload preview
function previewImage(input, previewId) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById(previewId).src = e.target.result;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Print function
function printPage() {
    window.print();
}

// Export to PDF (placeholder - would need a PDF library)
function exportToPDF() {
    showAlert('info', 'Funcionalidade de exportação será implementada em breve.');
}

// Loading state management
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Carregando...';
    } else {
        element.disabled = false;
        element.innerHTML = element.getAttribute('data-original-text') || 'Salvar';
    }
}

// Confirmation dialogs
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Local storage helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {
        console.warn('Could not save to localStorage:', e);
    }
}

function getFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        console.warn('Could not read from localStorage:', e);
        return null;
    }
}

// Auto-save form data (draft functionality)
function enableAutoSave(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('change', function() {
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            saveToLocalStorage(`draft_${formId}`, data);
        });
    });
}

// Initialize auto-save for client form
if (document.getElementById('clientForm')) {
    enableAutoSave('clientForm');
}
