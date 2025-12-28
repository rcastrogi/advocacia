// model_petition_form.js - JavaScript para formulários baseados em modelos de petição

document.addEventListener('alpine:init', () => {
    Alpine.data('modelPetitionForm', () => ({
        sections: window.PETITION_SECTIONS || [],
        formData: {},
        sectionExpanded: {},
        autoSaveStatus: 'idle',
        isGenerating: false,
        isSaving: false,
        petitionId: null,
        quillEditors: {},
        autoSaveTimeout: null,
        aiCredits: 10, // Créditos de IA disponíveis

        init() {
            // Inicializar estado de expansão das seções
            if (this.sections && this.sections.length > 0) {
                this.sections.forEach(s => {
                    this.sectionExpanded[s.section.slug] = s.is_expanded !== false;

                    // Habilitar IA para campos de texto
                    if (s.section.fields_schema) {
                        s.section.fields_schema.forEach(field => {
                            if (field.type === 'richtext' || field.type === 'textarea') {
                                field.ai_enabled = true;
                            }
                        });
                    }
                });
            }

            // Verificar se está editando uma petição existente
            if (window.EDIT_PETITION) {
                this.petitionId = window.EDIT_PETITION.id;
                this.formData = window.EDIT_PETITION.form_data || {};
            } else {
                // Carregar rascunho local se existir
                this.loadDraft();
            }

            // Inicializar editores Quill e toolbars de IA após DOM estar pronto
            this.$nextTick(() => {
                this.initAllQuillEditors();
                this.applyMasks();
                this.initAIToolbars();
            });

            // Auto-save a cada 30 segundos quando há mudanças
            this.$watch('formData', () => {
                this.scheduleAutoSave();
            }, { deep: true });
        },

        initAllQuillEditors() {
            // Encontrar todos os campos do tipo richtext e inicializá-los
            this.sections.forEach(s => {
                if (s.section.fields_schema) {
                    s.section.fields_schema.forEach(field => {
                        if (field.type === 'richtext') {
                            this.$nextTick(() => {
                                this.initQuillEditor(field.name);
                            });
                        }
                    });
                }
            });
        },

        initQuillEditor(fieldName) {
            const container = document.getElementById('quill-' + fieldName);
            if (!container || this.quillEditors[fieldName]) return;

            // Criar toolbar de IA antes do editor
            this.createAIToolbarForField(fieldName, container);

            const quill = new Quill(container, {
                theme: 'snow',
                placeholder: 'Digite o conteúdo aqui...',
                modules: {
                    toolbar: [
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        [{ 'indent': '-1'}, { 'indent': '+1' }],
                        [{ 'align': [] }],
                        ['clean']
                    ]
                }
            });

            quill.on('text-change', () => {
                this.formData[fieldName] = quill.root.innerHTML;
            });

            this.quillEditors[fieldName] = quill;

            // Restaurar conteúdo se existir
            if (this.formData[fieldName]) {
                quill.root.innerHTML = this.formData[fieldName];
            }
        },

        createAIToolbarForField(fieldName, container, fieldType = 'editor') {
            // Verificar se já existe uma toolbar
            let element = container;
            if (fieldType === 'editor') {
                const wrapper = container.closest('.quill-wrapper');
                if (wrapper && wrapper.previousElementSibling && wrapper.previousElementSibling.classList.contains('ai-toolbar')) {
                    return; // Já existe
                }
                element = wrapper;
            } else if (fieldType === 'textarea') {
                if (container.previousElementSibling && container.previousElementSibling.classList.contains('ai-toolbar')) {
                    return; // Já existe
                }
                element = container;
            }

            // Criar toolbar de IA
            const toolbar = document.createElement('div');
            toolbar.className = 'ai-toolbar d-flex justify-content-between align-items-center';
            toolbar.innerHTML = `
                <div class="d-flex gap-2">
                    <button type="button" class="btn btn-sm btn-outline-success"
                            @click="generateAIContent('${fieldName}')">
                        <i class="fas fa-magic me-1"></i> Gerar com IA
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-primary"
                            @click="improveContent('${fieldName}')">
                        <i class="fas fa-edit me-1"></i> Melhorar
                    </button>
                </div>
                <div class="ai-credits-indicator">
                    <small class="text-muted">
                        <i class="fas fa-coins me-1"></i>
                        Créditos: <span x-text="aiCredits"></span>
                    </small>
                </div>
            `;

            // Inserir antes do elemento
            if (element) {
                element.parentNode.insertBefore(toolbar, element);
            }
        },

        initAIToolbars() {
            // Procurar todos os campos que têm IA habilitada
            this.sections.forEach(section => {
                if (section.section.fields_schema) {
                    section.section.fields_schema.forEach(field => {
                        if (field.ai_enabled && (field.type === 'richtext' || field.type === 'textarea')) {
                            const fieldName = field.name;
                            const element = document.querySelector(`[name="${fieldName}"]`) ||
                                          document.getElementById('quill-' + fieldName);

                            if (element) {
                                if (field.type === 'richtext') {
                                    const container = element;
                                    this.createAIToolbarForField(fieldName, container);
                                } else if (field.type === 'textarea') {
                                    this.createAIToolbarForField(fieldName, element, 'textarea');
                                }
                            }
                        }
                    });
                }
            });
        },

        applyMasks() {
            // Aplicar máscaras se necessário
            // Implementar conforme necessário
        },

        getFieldColClass(field) {
            // Campos de texto longo ocupam toda a largura
            if (['textarea', 'richtext'].includes(field.type)) {
                return 'col-12';
            }
            return 'col-md-6';
        },

        getFieldValue(fieldName) {
            return this.formData[fieldName] || '';
        },

        updateFieldValue(fieldName, value) {
            this.formData[fieldName] = value;
        },

        getFieldValidationClass(fieldName) {
            const value = this.getFieldValue(fieldName);
            if (!value || value.toString().trim() === '') {
                return '';
            }
            // Implementar validação se necessário
            return 'field-valid';
        },

        findFieldByName(fieldName) {
            for (const section of this.sections) {
                if (section.section.fields_schema) {
                    for (const field of section.section.fields_schema) {
                        if (field.name === fieldName) {
                            return {
                                ...field,
                                section_name: section.section.name
                            };
                        }
                    }
                }
            }
            return null;
        },

        async generateAIContent(fieldName) {
            if (typeof PetitioAI === 'undefined') {
                this.showToast('Sistema de IA não disponível', 'error');
                return;
            }

            const ai = PetitioAI;
            const field = this.findFieldByName(fieldName);

            if (!field) {
                this.showToast('Campo não encontrado', 'error');
                return;
            }

            // Verificar créditos
            if (!ai.isUnlimited && ai.userCredits < ai.creditCosts.section) {
                this.showToast('Créditos insuficientes para gerar conteúdo', 'warning');
                return;
            }

            const existingContent = this.formData[fieldName] || '';

            // Confirmação se já tem conteúdo
            if (existingContent && existingContent.length > 50) {
                if (!confirm('Este campo já tem conteúdo. Deseja substituir pelo conteúdo gerado?')) {
                    return;
                }
            }

            try {
                // Mostrar loading
                this.showToast('Gerando conteúdo com IA...', 'info');

                // Preparar contexto
                const context = {
                    petition_type: window.PETITION_MODEL?.slug || 'petition',
                    section_type: field.section_name || 'general'
                };

                // Fazer requisição para gerar conteúdo
                const response = await fetch('/ai/api/generate/section', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        section_type: field.section_name || 'general',
                        petition_type: window.PETITION_MODEL?.slug || 'petition',
                        context: context,
                        existing_content: existingContent,
                        premium: false
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Inserir conteúdo no campo
                    if (field.type === 'richtext' && this.quillEditors[fieldName]) {
                        this.quillEditors[fieldName].root.innerHTML = data.content;
                    }
                    this.formData[fieldName] = data.content;

                    // Atualizar créditos se necessário
                    if (data.credits_remaining !== '∞') {
                        this.aiCredits = data.credits_remaining;
                    }

                    this.showToast('Conteúdo gerado com sucesso!', 'success');
                } else {
                    if (response.status === 402) {
                        this.showToast('Créditos insuficientes', 'warning');
                    } else {
                        this.showToast(data.error || 'Erro ao gerar conteúdo', 'error');
                    }
                }
            } catch (error) {
                console.error('Erro ao gerar conteúdo com IA:', error);
                this.showToast('Erro ao gerar conteúdo com IA', 'error');
            }
        },

        async improveContent(fieldName) {
            if (typeof PetitioAI === 'undefined') {
                this.showToast('Sistema de IA não disponível', 'error');
                return;
            }

            const ai = PetitioAI;
            const currentContent = this.formData[fieldName] || '';

            if (!currentContent.trim()) {
                this.showToast('Campo vazio. Digite algum conteúdo primeiro.', 'warning');
                return;
            }

            // Verificar créditos
            if (!ai.isUnlimited && ai.userCredits < ai.creditCosts.improve) {
                this.showToast('Créditos insuficientes para melhorar conteúdo', 'warning');
                return;
            }

            try {
                // Mostrar loading
                this.showToast('Melhorando conteúdo com IA...', 'info');

                // Preparar contexto
                const context = {
                    petition_type: window.PETITION_MODEL?.slug || 'petition',
                    section_type: this.findFieldByName(fieldName)?.section_name || 'general'
                };

                // Fazer requisição para melhorar conteúdo
                const response = await fetch('/ai/api/generate/improve', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        text: currentContent,
                        context: JSON.stringify(context),
                        premium: false
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Atualizar conteúdo no campo
                    if (this.quillEditors[fieldName]) {
                        this.quillEditors[fieldName].root.innerHTML = data.content;
                    }
                    this.formData[fieldName] = data.content;

                    // Atualizar créditos se necessário
                    if (data.credits_remaining !== '∞') {
                        this.aiCredits = data.credits_remaining;
                    }

                    this.showToast('Conteúdo melhorado com sucesso!', 'success');
                } else {
                    if (response.status === 402) {
                        this.showToast('Créditos insuficientes', 'warning');
                    } else {
                        this.showToast(data.error || 'Erro ao melhorar conteúdo', 'error');
                    }
                }
            } catch (error) {
                console.error('Erro ao melhorar conteúdo com IA:', error);
                this.showToast('Erro ao melhorar conteúdo com IA', 'error');
            }
        },

        async savePetition() {
            this.isSaving = true;

            try {
                const response = await fetch('/petitions/api/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        petition_id: this.petitionId,
                        petition_model_id: window.PETITION_MODEL.id,
                        form_data: this.formData,
                        action: 'save'
                    })
                });

                const data = await response.json();

                if (data.success) {
                    this.petitionId = data.petition_id;
                    this.showToast('Petição salva com sucesso!', 'success');
                } else {
                    this.showToast(data.error || 'Erro ao salvar petição', 'error');
                }
            } catch (error) {
                console.error('Erro:', error);
                this.showToast('Erro ao salvar petição. Tente novamente.', 'error');
            } finally {
                this.isSaving = false;
            }
        },

        async validateForm() {
            // Implementar validação do formulário
            this.showToast('Validação concluída', 'success');
        },

        async previewPetition() {
            // Implementar preview da petição
            const modal = new bootstrap.Modal(document.getElementById('previewModal'));
            const content = document.getElementById('previewContent');

            let html = '<div class="text-center mb-4">';
            html += '<h4>PREVIEW DA PETIÇÃO</h4>';
            html += '<p>Baseado no modelo: ' + window.PETITION_MODEL.name + '</p>';
            html += '</div>';

            // Mostrar dados preenchidos
            Object.entries(this.formData).forEach(([key, value]) => {
                if (value && value.toString().trim() !== '') {
                    html += `<div class="mb-2"><strong>${key}:</strong> ${value}</div>`;
                }
            });

            content.innerHTML = html;
            modal.show();
        },

        async generatePetition() {
            this.isGenerating = true;

            try {
                const response = await fetch('/petitions/generate-model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        petition_model_id: window.PETITION_MODEL.id,
                        form_data: this.formData
                    })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = window.PETITION_MODEL.name.replace(/ /g, '_') + '.pdf';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                } else {
                    const error = await response.json();
                    this.showToast('Erro ao gerar petição: ' + (error.error || 'Erro desconhecido'), 'error');
                }
            } catch (error) {
                console.error('Erro:', error);
                this.showToast('Erro ao gerar petição. Tente novamente.', 'error');
            } finally {
                this.isGenerating = false;
            }
        },

        scheduleAutoSave() {
            if (this.autoSaveTimeout) {
                clearTimeout(this.autoSaveTimeout);
            }
            this.autoSaveTimeout = setTimeout(() => {
                this.saveAsDraft();
            }, 30000);
        },

        async saveAsDraft() {
            this.autoSaveStatus = 'saving';

            try {
                const key = 'petition_model_draft_' + window.PETITION_MODEL.slug;
                localStorage.setItem(key, JSON.stringify({
                    formData: this.formData,
                    timestamp: new Date().toISOString()
                }));

                this.autoSaveStatus = 'saved';
                setTimeout(() => {
                    this.autoSaveStatus = 'idle';
                }, 2000);
            } catch (error) {
                this.autoSaveStatus = 'error';
                console.error('Erro ao salvar rascunho:', error);
            }
        },

        loadDraft() {
            try {
                const key = 'petition_model_draft_' + window.PETITION_MODEL.slug;
                const saved = localStorage.getItem(key);
                if (saved) {
                    const data = JSON.parse(saved);
                    this.formData = data.formData || {};
                }
            } catch (error) {
                console.error('Erro ao carregar rascunho:', error);
            }
        },

        showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
            toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            toast.innerHTML = `
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
            `;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.remove();
            }, 3000);
        }
    }));
});