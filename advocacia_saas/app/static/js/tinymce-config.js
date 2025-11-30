/**
 * TinyMCE Configuration for Petitio
 * Configuração do editor de texto rico com suporte a variáveis Jinja
 */

// Variáveis disponíveis para petições cíveis
const CIVIL_VARIABLES = [
    { value: '{{ forum }}', text: 'Fórum' },
    { value: '{{ vara }}', text: 'Vara' },
    { value: '{{ process_number }}', text: 'Número do Processo' },
    { value: '{{ author_name }}', text: 'Nome do Autor' },
    { value: '{{ author_qualification }}', text: 'Qualificação do Autor' },
    { value: '{{ defendant_name }}', text: 'Nome do Réu' },
    { value: '{{ defendant_qualification }}', text: 'Qualificação do Réu' },
    { value: '{{ facts }}', text: 'Fatos' },
    { value: '{{ fundamentos }}', text: 'Fundamentação' },
    { value: '{{ pedidos }}', text: 'Pedidos' },
    { value: '{{ valor_causa }}', text: 'Valor da Causa' },
    { value: '{{ cidade }}', text: 'Cidade' },
    { value: '{{ data_assinatura }}', text: 'Data de Assinatura' },
    { value: '{{ advogado_nome }}', text: 'Nome do Advogado' },
    { value: '{{ advogado_oab }}', text: 'OAB do Advogado' },
];

// Variáveis para petições de família
const FAMILY_VARIABLES = [
    ...CIVIL_VARIABLES.filter(v => ['forum', 'vara', 'process_number', 'facts', 'fundamentos', 'pedidos', 'cidade', 'data_assinatura', 'advogado_nome', 'advogado_oab'].some(k => v.value.includes(k))),
    { value: '{{ action_type }}', text: 'Tipo de Ação' },
    { value: '{{ marriage_date }}', text: 'Data do Casamento' },
    { value: '{{ marriage_city }}', text: 'Cidade do Casamento' },
    { value: '{{ marriage_regime }}', text: 'Regime de Bens' },
    { value: '{{ prenup_summary }}', text: 'Pacto Antenupcial' },
    { value: '{{ spouse_one_name }}', text: 'Nome do Cônjuge 1' },
    { value: '{{ spouse_one_qualification }}', text: 'Qualificação do Cônjuge 1' },
    { value: '{{ spouse_two_name }}', text: 'Nome do Cônjuge 2' },
    { value: '{{ spouse_two_qualification }}', text: 'Qualificação do Cônjuge 2' },
    { value: '{{ children_info }}', text: 'Informações dos Filhos' },
    { value: '{{ custody_plan }}', text: 'Plano de Guarda' },
    { value: '{{ alimony_plan }}', text: 'Plano de Alimentos' },
    { value: '{{ property_description }}', text: 'Descrição dos Bens' },
];

// Configuração base do TinyMCE
function getTinyMCEConfig(options = {}) {
    const defaultConfig = {
        height: options.height || 400,
        language: 'pt_BR',
        language_url: 'https://cdn.tiny.cloud/1/no-api-key/tinymce/7/langs/pt_BR.js',
        plugins: [
            'advlist', 'autolink', 'lists', 'link', 'charmap', 'preview',
            'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
            'insertdatetime', 'table', 'wordcount', 'help'
        ],
        toolbar: options.toolbar || 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | variableinsert | help',
        menubar: options.menubar !== undefined ? options.menubar : 'file edit view insert format tools table help',
        content_style: `
            body { 
                font-family: 'Times New Roman', Times, serif; 
                font-size: 12pt; 
                line-height: 1.5;
                margin: 1cm;
            }
            p { margin: 0 0 12pt 0; }
            .jinja-variable {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 3px;
                padding: 2px 4px;
                font-family: monospace;
                font-size: 11pt;
            }
        `,
        font_family_formats: 'Arial=arial,helvetica,sans-serif; Times New Roman=times new roman,times,serif; Courier New=courier new,courier,monospace; Georgia=georgia,palatino,serif; Verdana=verdana,geneva,sans-serif',
        font_size_formats: '8pt 10pt 11pt 12pt 14pt 16pt 18pt 24pt 36pt',
        block_formats: 'Parágrafo=p; Cabeçalho 1=h1; Cabeçalho 2=h2; Cabeçalho 3=h3; Cabeçalho 4=h4',
        branding: false,
        promotion: false,
        // Callbacks
        setup: function(editor) {
            // Adiciona botão customizado para inserir variáveis
            editor.ui.registry.addMenuButton('variableinsert', {
                text: 'Inserir Campo',
                icon: 'template',
                tooltip: 'Inserir variável do formulário',
                fetch: function(callback) {
                    const variables = options.variables || CIVIL_VARIABLES;
                    const items = variables.map(function(variable) {
                        return {
                            type: 'menuitem',
                            text: variable.text,
                            onAction: function() {
                                editor.insertContent('<span class="jinja-variable">' + variable.value + '</span>&nbsp;');
                            }
                        };
                    });
                    callback(items);
                }
            });

            // Destaca variáveis Jinja ao carregar conteúdo
            editor.on('SetContent', function() {
                highlightJinjaVariables(editor);
            });
        },
        // Limpa as classes de destaque antes de salvar
        init_instance_callback: function(editor) {
            editor.on('GetContent', function(e) {
                // Remove span wrapper mas mantém a variável
                e.content = e.content.replace(/<span class="jinja-variable">(.*?)<\/span>/g, '$1');
            });
        }
    };

    return { ...defaultConfig, ...options };
}

// Função para destacar variáveis Jinja no editor
function highlightJinjaVariables(editor) {
    const content = editor.getContent();
    const highlighted = content.replace(
        /(\{\{[^}]+\}\})/g,
        function(match) {
            if (match.includes('class="jinja-variable"')) {
                return match;
            }
            return '<span class="jinja-variable">' + match + '</span>';
        }
    );
    if (highlighted !== content) {
        editor.setContent(highlighted);
    }
}

// Inicializa TinyMCE para editores de template (conteúdo completo da petição)
function initTemplateEditor(selector, category = 'civel') {
    const variables = category === 'familia' ? FAMILY_VARIABLES : CIVIL_VARIABLES;
    
    return tinymce.init({
        selector: selector,
        ...getTinyMCEConfig({
            height: 600,
            variables: variables,
            toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | table | removeformat | variableinsert | code fullscreen | help',
        })
    });
}

// Inicializa TinyMCE para campos de texto padrão (fatos, fundamentos, pedidos)
function initDefaultTextEditor(selector) {
    return tinymce.init({
        selector: selector,
        ...getTinyMCEConfig({
            height: 250,
            menubar: false,
            toolbar: 'undo redo | bold italic underline | bullist numlist | removeformat',
            plugins: ['advlist', 'autolink', 'lists', 'wordcount'],
        })
    });
}

// Inicializa TinyMCE para formulário de petição (campos de entrada do usuário)
function initPetitionFormEditor(selector) {
    return tinymce.init({
        selector: selector,
        ...getTinyMCEConfig({
            height: 200,
            menubar: false,
            toolbar: 'undo redo | bold italic underline | bullist numlist outdent indent | removeformat',
            plugins: ['advlist', 'autolink', 'lists', 'wordcount'],
            content_style: `
                body { 
                    font-family: 'Times New Roman', Times, serif; 
                    font-size: 12pt; 
                    line-height: 1.5;
                    margin: 0.5cm;
                }
                p { margin: 0 0 8pt 0; }
            `,
        })
    });
}

// Exporta funções globalmente
window.PetitioEditor = {
    initTemplateEditor,
    initDefaultTextEditor,
    initPetitionFormEditor,
    getTinyMCEConfig,
    CIVIL_VARIABLES,
    FAMILY_VARIABLES,
};
