# Melhorias de Acessibilidade (WCAG 2.1 Level AA)

## ✅ Implementações Realizadas

### 1. **Landmarks ARIA e Semântica HTML5**
- ✅ Navegação principal com `role="navigation"` e `aria-label`
- ✅ Conteúdo principal com `<main role="main">` e `id="main-content"`
- ✅ Rodapé com `role="contentinfo"` e `aria-label`
- ✅ Barra de acessibilidade com `role="complementary"`

### 2. **Navegação por Teclado**
- ✅ Skip link funcional (Alt + S ou Tab inicial)
- ✅ Todos os elementos interativos acessíveis via Tab
- ✅ Indicadores de foco visíveis (outline + box-shadow)
- ✅ Trap de foco em modais
- ✅ ESC para fechar modais
- ✅ Atalhos de teclado (Alt+1, Alt+2, Alt+3, Alt+H)

### 3. **Screen Readers**
- ✅ Região de anúncios com `aria-live="polite"`
- ✅ Loading spinner com `role="status"` e `aria-live="assertive"`
- ✅ Toasts com `role="alert"` e navegáveis por teclado
- ✅ Ícones decorativos com `aria-hidden="true"`
- ✅ Imagens com alt text descritivo
- ✅ Botões com `aria-label` quando necessário

### 4. **Formulários Acessíveis**
- ✅ Labels associados a campos (for/id)
- ✅ `aria-required="true"` em campos obrigatórios
- ✅ `aria-invalid="true"` em campos com erro
- ✅ `aria-describedby` vinculando mensagens de erro
- ✅ Macros Jinja2 para facilitar implementação:
  - `render_field()` - inputs de texto
  - `render_checkbox()` - checkboxes
  - `render_select()` - selects/dropdowns
  - `render_textarea()` - textareas

### 5. **Controles de Acessibilidade**
- ✅ Ajuste de tamanho de fonte (4 níveis)
- ✅ Modo de alto contraste
- ✅ Persistência via localStorage
- ✅ Botão flutuante sempre acessível

### 6. **Responsividade e Touch**
- ✅ Alvos de toque mínimo de 44x44px
- ✅ Espaçamento adequado entre elementos interativos
- ✅ Suporte a gestos e teclado virtual

### 7. **Tabelas Acessíveis**
- ✅ `role="table"` quando necessário
- ✅ Headers com `scope="col"` ou `scope="row"`
- ✅ Captions descritivos (visualmente ocultos se necessário)

## 📋 Como Usar as Macros de Formulários

### Importar no Template
```jinja2
{% from "macros/accessible_forms.html" import render_field, render_checkbox, render_select, render_textarea %}
```

### Exemplos de Uso

#### Campo de Texto
```jinja2
{{ render_field(form.full_name, placeholder="Ex: João Silva", help_text="Nome completo conforme RG") }}
```

#### Checkbox
```jinja2
{{ render_checkbox(form.accept_terms, help_text="Li e concordo com os termos de uso") }}
```

#### Select/Dropdown
```jinja2
{{ render_select(form.civil_status, help_text="Selecione seu estado civil") }}
```

#### Textarea
```jinja2
{{ render_textarea(form.observations, rows=5, help_text="Observações adicionais") }}
```

## 🧪 Como Testar

### Navegação por Teclado
1. Use apenas o teclado (sem mouse)
2. Navegue com Tab/Shift+Tab
3. Ative elementos com Enter/Space
4. Verifique indicadores de foco visíveis

### Screen Reader (NVDA/JAWS)
1. Baixe NVDA (gratuito) ou use JAWS
2. Navegue por landmarks (D para próximo landmark)
3. Liste links (Insert+F7)
4. Liste headers (H para próximo heading)
5. Verifique anúncios de mudanças dinâmicas

### Contraste de Cores
1. Use extensão "WCAG Color contrast checker"
2. Ratio mínimo: 4.5:1 para texto normal
3. Ratio mínimo: 3:1 para texto grande (18pt+ ou 14pt+ negrito)

### Ferramentas Automatizadas
- Lighthouse Accessibility Audit (Chrome DevTools)
- axe DevTools (extensão do navegador)
- WAVE Web Accessibility Evaluation Tool

## 📚 Recursos Adicionais

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM](https://webaim.org/)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

## 🔄 Próximos Passos Recomendados

1. Auditar todas as páginas com Lighthouse
2. Testar com usuários reais que usam tecnologia assistiva
3. Revisar contraste de cores em componentes personalizados
4. Adicionar captions em vídeos (se houver)
5. Garantir que todos os novos componentes sigam estes padrões

## 🐛 Reportar Problemas de Acessibilidade

Encontrou um problema de acessibilidade? 
- Descreva o problema
- Especifique a tecnologia assistiva usada
- Indique a página/componente afetado
- Sugira uma solução se possível
