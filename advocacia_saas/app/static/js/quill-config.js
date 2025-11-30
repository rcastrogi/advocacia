/**
 * Quill Editor Configuration for Petitio
 * Editor de texto rico gratuito com suporte a variáveis Jinja
 * 
 * Quill é 100% gratuito e open-source (BSD license)
 * Substitui o TinyMCE que requer pagamento após 14 dias
 */

// Variáveis disponíveis para petições cíveis
const CIVIL_VARIABLES = [
    { value: '{{ forum }}', text: 'Fórum', category: 'processo' },
    { value: '{{ vara }}', text: 'Vara', category: 'processo' },
    { value: '{{ process_number }}', text: 'Número do Processo', category: 'processo' },
    { value: '{{ author_name }}', text: 'Nome do Autor', category: 'partes' },
    { value: '{{ author_qualification }}', text: 'Qualificação do Autor', category: 'partes' },
    { value: '{{ defendant_name }}', text: 'Nome do Réu', category: 'partes' },
    { value: '{{ defendant_qualification }}', text: 'Qualificação do Réu', category: 'partes' },
    { value: '{{ facts }}', text: 'Fatos', category: 'conteudo' },
    { value: '{{ fundamentos }}', text: 'Fundamentação', category: 'conteudo' },
    { value: '{{ pedidos }}', text: 'Pedidos', category: 'conteudo' },
    { value: '{{ valor_causa }}', text: 'Valor da Causa', category: 'processo' },
    { value: '{{ cidade }}', text: 'Cidade', category: 'assinatura' },
    { value: '{{ data_assinatura }}', text: 'Data de Assinatura', category: 'assinatura' },
    { value: '{{ advogado_nome }}', text: 'Nome do Advogado', category: 'assinatura' },
    { value: '{{ advogado_oab }}', text: 'OAB do Advogado', category: 'assinatura' },
];

// Variáveis para petições de família
const FAMILY_VARIABLES = [
    ...CIVIL_VARIABLES.filter(v => ['forum', 'vara', 'process_number', 'facts', 'fundamentos', 'pedidos', 'cidade', 'data_assinatura', 'advogado_nome', 'advogado_oab'].some(k => v.value.includes(k))),
    { value: '{{ action_type }}', text: 'Tipo de Ação', category: 'processo' },
    { value: '{{ marriage_date }}', text: 'Data do Casamento', category: 'casamento' },
    { value: '{{ marriage_city }}', text: 'Cidade do Casamento', category: 'casamento' },
    { value: '{{ marriage_regime }}', text: 'Regime de Bens', category: 'casamento' },
    { value: '{{ prenup_summary }}', text: 'Pacto Antenupcial', category: 'casamento' },
    { value: '{{ spouse_one_name }}', text: 'Nome do Cônjuge 1', category: 'partes' },
    { value: '{{ spouse_one_qualification }}', text: 'Qualificação do Cônjuge 1', category: 'partes' },
    { value: '{{ spouse_two_name }}', text: 'Nome do Cônjuge 2', category: 'partes' },
    { value: '{{ spouse_two_qualification }}', text: 'Qualificação do Cônjuge 2', category: 'partes' },
    { value: '{{ children_info }}', text: 'Informações dos Filhos', category: 'filhos' },
    { value: '{{ custody_plan }}', text: 'Plano de Guarda', category: 'filhos' },
    { value: '{{ alimony_plan }}', text: 'Plano de Alimentos', category: 'filhos' },
    { value: '{{ property_description }}', text: 'Descrição dos Bens', category: 'patrimonio' },
];

// Toolbar configurations
const TOOLBAR_FULL = [
    [{ 'header': [1, 2, 3, false] }],
    ['bold', 'italic', 'underline', 'strike'],
    [{ 'color': [] }, { 'background': [] }],
    [{ 'align': [] }],
    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
    [{ 'indent': '-1'}, { 'indent': '+1' }],
    ['blockquote', 'link'],
    ['clean']
];

const TOOLBAR_SIMPLE = [
    ['bold', 'italic', 'underline'],
    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
    [{ 'indent': '-1'}, { 'indent': '+1' }],
    ['clean']
];

const TOOLBAR_TEMPLATE = [
    [{ 'header': [1, 2, 3, false] }],
    [{ 'font': [] }],
    ['bold', 'italic', 'underline', 'strike'],
    [{ 'color': [] }, { 'background': [] }],
    [{ 'align': [] }],
    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
    [{ 'indent': '-1'}, { 'indent': '+1' }],
    ['blockquote', 'link'],
    ['clean']
];

/**
 * CSS styles for legal documents
 */
const LEGAL_STYLES = `
    .ql-container {
        font-family: 'Times New Roman', Times, serif;
        font-size: 12pt;
    }
    .ql-editor {
        line-height: 1.5;
        text-align: justify;
        min-height: 200px;
    }
    .ql-editor p {
        margin-bottom: 12pt;
    }
    .ql-editor h1 {
        font-size: 16pt;
        font-weight: bold;
        text-align: center;
        margin-bottom: 24pt;
    }
    .ql-editor h2 {
        font-size: 14pt;
        font-weight: bold;
        margin: 18pt 0 12pt 0;
    }
    .ql-editor h3 {
        font-size: 12pt;
        font-weight: bold;
        margin: 12pt 0 8pt 0;
    }
    .ql-editor blockquote {
        border-left: 3px solid #ccc;
        margin: 12pt 2cm;
        padding-left: 12pt;
        font-style: italic;
    }
    .ql-editor ul, .ql-editor ol {
        padding-left: 1.5cm;
    }
    .ql-editor li {
        margin-bottom: 6pt;
    }
    .jinja-variable {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 3px;
        padding: 2px 4px;
        font-family: monospace;
        font-size: 11pt;
    }
    .ql-toolbar.ql-snow {
        border-radius: 4px 4px 0 0;
        background: #f8f9fa;
    }
    .ql-container.ql-snow {
        border-radius: 0 0 4px 4px;
    }
`;

/**
 * Inject legal styles into page
 */
function injectLegalStyles() {
    if (document.getElementById('quill-legal-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'quill-legal-styles';
    style.textContent = LEGAL_STYLES;
    document.head.appendChild(style);
}

/**
 * Initialize a Quill editor
 * @param {string|HTMLElement} container - Container element or selector
 * @param {Object} options - Configuration options
 * @returns {Quill} Quill editor instance
 */
function initQuillEditor(container, options = {}) {
    injectLegalStyles();
    
    const element = typeof container === 'string' ? document.querySelector(container) : container;
    if (!element) {
        console.error('Quill container not found:', container);
        return null;
    }

    const quill = new Quill(element, {
        theme: 'snow',
        modules: {
            toolbar: options.toolbar || TOOLBAR_SIMPLE
        },
        placeholder: options.placeholder || 'Digite o conteúdo aqui...'
    });

    // Set initial content
    if (options.content) {
        quill.root.innerHTML = options.content;
    }

    // Change callback
    if (options.onChange) {
        quill.on('text-change', function() {
            options.onChange(quill.root.innerHTML);
        });
    }

    // Save shortcut (Ctrl+S)
    if (options.onSave) {
        quill.root.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                options.onSave(quill.root.innerHTML);
            }
        });
    }

    return quill;
}

/**
 * Convert textarea to Quill editor
 * @param {HTMLTextAreaElement} textarea - Textarea to convert
 * @param {Object} options - Options
 * @returns {Object} Object with quill instance and helpers
 */
function textareaToQuill(textarea, options = {}) {
    if (!textarea || textarea._quillInitialized) return null;

    injectLegalStyles();

    // Create editor container
    const editorDiv = document.createElement('div');
    editorDiv.className = 'quill-editor';
    editorDiv.style.minHeight = options.height || '200px';
    
    // Insert before textarea and hide textarea
    textarea.parentNode.insertBefore(editorDiv, textarea);
    textarea.style.display = 'none';
    textarea._quillInitialized = true;

    // Create Quill instance
    const quill = new Quill(editorDiv, {
        theme: 'snow',
        modules: {
            toolbar: options.toolbar || TOOLBAR_SIMPLE
        },
        placeholder: options.placeholder || textarea.placeholder || 'Digite aqui...'
    });

    // Set initial content from textarea
    if (textarea.value) {
        quill.root.innerHTML = textarea.value;
    }

    // Sync changes to textarea
    quill.on('text-change', function() {
        textarea.value = quill.root.innerHTML;
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
        
        if (options.onChange) {
            options.onChange(quill.root.innerHTML);
        }
    });

    // Store reference
    textarea._quill = quill;

    return {
        quill: quill,
        element: editorDiv,
        textarea: textarea,
        
        getContent: function() {
            return quill.root.innerHTML;
        },
        
        setContent: function(html) {
            quill.root.innerHTML = html;
            textarea.value = html;
        },
        
        getText: function() {
            return quill.getText();
        },
        
        sync: function() {
            textarea.value = quill.root.innerHTML;
        }
    };
}

/**
 * Initialize template editor with variable insertion support
 * @param {string} selector - Editor container selector
 * @param {string} category - 'civel' or 'familia'
 * @returns {Object} Editor instance with variable support
 */
function initTemplateEditor(selector, category = 'civel') {
    const container = document.querySelector(selector);
    if (!container) return null;

    const variables = category === 'familia' ? FAMILY_VARIABLES : CIVIL_VARIABLES;
    
    const quill = initQuillEditor(container, {
        toolbar: TOOLBAR_TEMPLATE,
        placeholder: 'Digite o conteúdo do template aqui...'
    });

    if (!quill) return null;

    return {
        quill: quill,
        variables: variables,
        
        insertVariable: function(variable) {
            const range = quill.getSelection(true);
            const varText = typeof variable === 'string' ? variable : variable.value;
            quill.insertText(range.index, varText, { 
                'background': '#fff3cd'
            });
            quill.insertText(range.index + varText.length, ' ');
            quill.setSelection(range.index + varText.length + 1);
        },
        
        getContent: function() {
            return quill.root.innerHTML;
        },
        
        setContent: function(html) {
            quill.root.innerHTML = html;
        },

        highlightVariables: function() {
            // Variables are already highlighted by background color
        }
    };
}

/**
 * Initialize default text editor for template defaults
 * @param {string} selector - Textarea selector
 * @returns {Object} Editor instance
 */
function initDefaultTextEditor(selector) {
    const textarea = document.querySelector(selector);
    if (!textarea) return null;
    
    return textareaToQuill(textarea, {
        toolbar: TOOLBAR_SIMPLE,
        height: '250px'
    });
}

/**
 * Initialize petition form editor
 * @param {string} selector - Textarea selector
 * @returns {Object} Editor instance
 */
function initPetitionFormEditor(selector) {
    const textarea = document.querySelector(selector);
    if (!textarea) return null;
    
    return textareaToQuill(textarea, {
        toolbar: TOOLBAR_SIMPLE,
        height: '200px'
    });
}

/**
 * Auto-initialize editors for elements with .petition-editor class
 */
function autoInitEditors() {
    document.querySelectorAll('.petition-editor').forEach(textarea => {
        if (textarea.tagName === 'TEXTAREA' && !textarea._quillInitialized) {
            textareaToQuill(textarea, {
                toolbar: TOOLBAR_SIMPLE,
                height: '250px'
            });
        }
    });
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInitEditors);
} else {
    autoInitEditors();
}

// Re-initialize after HTMX swaps
document.addEventListener('htmx:afterSwap', autoInitEditors);

// Export for global use
window.PetitioEditor = {
    initTemplateEditor,
    initDefaultTextEditor,
    initPetitionFormEditor,
    textareaToQuill,
    autoInitEditors,
    CIVIL_VARIABLES,
    FAMILY_VARIABLES,
    TOOLBAR_FULL,
    TOOLBAR_SIMPLE,
    TOOLBAR_TEMPLATE
};
