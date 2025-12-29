// Main JavaScript file for Petitio

// Use requestAnimationFrame for better performance
function scheduleTask(callback) {
    if (window.requestAnimationFrame) {
        requestAnimationFrame(callback);
    } else {
        setTimeout(callback, 16); // Fallback to ~60fps
    }
}

$(document).ready(function() {
    // Initialize tooltips with debounced initialization
    scheduleTask(function() {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    });

    // Auto-dismiss alerts after 5 seconds (but not error alerts) - use setTimeout instead of jQuery fadeOut for better performance
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible:not(.alert-danger)');
        alerts.forEach(function(alert) {
            alert.style.transition = 'opacity 0.3s ease-out';
            alert.style.opacity = '0';
            setTimeout(function() {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 300);
        });
    }, 5000);

    // Add fade-in animation to cards - batch DOM operations
    scheduleTask(function() {
        const cards = document.querySelectorAll('.card');
        cards.forEach(function(card) {
            card.classList.add('fade-in');
        });
    });

    // Smooth scrolling for anchor links - optimized event delegation
    document.addEventListener('click', function(e) {
        const target = e.target.closest('a[href*="#"]');
        if (target && target.hash !== '') {
            e.preventDefault();
            const hash = target.hash;
            const targetElement = document.querySelector(hash);
            if (targetElement) {
                const offsetTop = targetElement.offsetTop - 70;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        }
    });

    // Format phone inputs - use event delegation for better performance
    document.addEventListener('input', function(e) {
        const target = e.target;
        if (target.matches('input[type="tel"], input[name*="phone"]')) {
            let value = target.value.replace(/\D/g, '');
            if (value.length <= 11) {
                if (value.length <= 10) {
                    value = value.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
                } else {
                    value = value.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
                }
                target.value = value;
            }
        }
    });

    // Format CPF/CNPJ input - use event delegation
    document.addEventListener('input', function(e) {
        const target = e.target;
        if (target.matches('input[name*="cpf"], input[name*="cnpj"]')) {
            let value = target.value.replace(/\D/g, '');
            if (value.length <= 11) {
                // CPF format
                value = value.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
            } else {
                // CNPJ format
                value = value.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
            }
            target.value = value;
        }
    });

    // Format CEP input - use event delegation
    document.addEventListener('input', function(e) {
        const target = e.target;
        if (target.matches('input[name*="cep"]')) {
            let value = target.value.replace(/\D/g, '');
            if (value.length <= 8) {
                value = value.replace(/(\d{5})(\d{3})/, '$1-$2');
                target.value = value;
            }
        }
    });

    // Auto search CEP when 8 digits are entered (with delay to avoid too many requests)
    let cepTimeout;
    document.addEventListener('input', function(e) {
        const target = e.target;
        if (target.matches('input[name*="cep"]')) {
            const cep = target.value.replace(/\D/g, '');
            clearTimeout(cepTimeout);
            if (cep.length === 8) {
                cepTimeout = setTimeout(() => {
                    searchCEP(cep);
                }, 500); // Wait 500ms after user stops typing
            }
        }
    });
});

// CEP search function - optimized to reduce DOM operations
function searchCEP(cep) {
    if (cep.length === 8) {
        // Show loading - cache DOM element
        const button = document.getElementById('searchCep');
        if (button) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            button.disabled = true;
        }

        fetch(`/api/cep/${cep}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    // Mostrar aviso amigável para CEP não encontrado
                    if (window.showWarningToast) {
                        window.showWarningToast('CEP não encontrado. Verifique se está correto.');
                    } else {
                        showAlert('warning', 'CEP não encontrado. Verifique se está correto.');
                    }
                } else {
                    // Batch DOM operations to avoid multiple reflows
                    scheduleTask(() => {
                        // Get field references once
                        const streetField = document.getElementById('street');
                        const neighborhoodField = document.getElementById('neighborhood');
                        const ufField = document.getElementById('uf');
                        const cityField = document.getElementById('city');

                        // Prepare all field updates
                        const updates = [];

                        if (streetField && data.street) {
                            updates.push(() => {
                                streetField.value = data.street;
                                streetField.classList.add('slide-up');
                            });
                        }
                        if (neighborhoodField && data.neighborhood) {
                            updates.push(() => {
                                neighborhoodField.value = data.neighborhood;
                                neighborhoodField.classList.add('slide-up');
                            });
                        }
                        if (ufField && data.uf) {
                            updates.push(() => {
                                ufField.value = data.uf;
                                ufField.classList.add('slide-up');
                            });
                        }
                        if (cityField && data.city) {
                            updates.push(() => {
                                cityField.value = data.city;
                                cityField.classList.add('slide-up');
                            });
                        }

                        // Execute all updates in one batch
                        updates.forEach(update => update());

                        // Lock fields after all updates are complete
                        lockCEPFields(streetField, neighborhoodField, ufField, cityField);

                        // Show success message
                        showAlert('success', 'Endereço preenchido automaticamente!');
                    });
                }
            })
            .catch(error => {
                console.error('❌ Erro ao buscar CEP:', error);
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

// Lock fields filled by CEP API - optimized to reduce DOM operations
function lockCEPFields(streetField, neighborhoodField, ufField, cityField) {

    const lockedValues = {
        street: streetField ? streetField.value : '',
        neighborhood: neighborhoodField ? neighborhoodField.value : '',
        uf: ufField ? ufField.value : '',
        city: cityField ? cityField.value : ''
    };

    // Single event handler function to reduce memory usage
    const preventChange = function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        showAlert('warning', '⛔ Este campo foi preenchido pelo CEP e está bloqueado. Altere o CEP para desbloquear.');
        return false;
    };

    // Batch all DOM operations
    scheduleTask(() => {
        const fields = [streetField, neighborhoodField, ufField, cityField];
        const fieldNames = ['street', 'neighborhood', 'uf', 'city'];

        fields.forEach((field, index) => {
            if (!field) return;

            const fieldName = fieldNames[index];
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

            // Apply styles in one go using CSS custom properties for better performance
            field.style.cssText += 'pointer-events: none; cursor: not-allowed; background-color: #e9ecef;';
            field.classList.add('cep-locked');

            // Add single event listener with useCapture for better performance
            field.addEventListener('keydown', preventChange, true);
            field.addEventListener('input', function() { this.value = value; }, true);
            field.addEventListener('change', function() { this.value = value; }, true);
        });
    });
}

// Unlock fields when CEP changes - optimized
$(document).ready(function() {
    // Use event delegation for better performance
    document.addEventListener('input', function(e) {
        const target = e.target;
        if (target.matches('input[name*="cep"]')) {
            const cepValue = target.value.replace(/\D/g, '');

            // If user is typing/changing CEP, unlock fields
            if (cepValue.length > 0 && cepValue.length < 8) {
                scheduleTask(() => {
                    const streetField = document.getElementById('street');
                    const neighborhoodField = document.getElementById('neighborhood');
                    const ufField = document.getElementById('uf');
                    const cityField = document.getElementById('city');

                    [streetField, neighborhoodField, ufField, cityField].forEach(field => {
                        if (field && field.dataset.cepLocked === 'true') {
                            // Remove locked state
                            delete field.dataset.cepLocked;
                            delete field.dataset.lockedValue;

                            // Remove restrictions
                            field.readOnly = false;
                            field.disabled = false;
                            field.style.cssText = field.style.cssText.replace(/pointer-events:[^;]+;?/g, '').replace(/cursor:[^;]+;?/g, '').replace(/background-color:[^;]+;?/g, '');
                            field.classList.remove('cep-locked', 'bg-light');
                        }
                    });
                });
            }
        }
    });
});

// Show alert function - DELEGADA PARA SISTEMA UNIFICADO
function showAlert(type, message) {
    if (window.showNotification) {
        window.showNotification(message, type);
    } else {
        // Fallback se o sistema unificado não estiver carregado
    }
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
