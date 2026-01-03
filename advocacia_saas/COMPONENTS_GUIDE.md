# 📦 Guia de Componentes Reutilizáveis

## Visão Geral

Componentes reutilizáveis para padronizar e facilitar o desenvolvimento de páginas de listagem (list pages) no projeto.

---

## 1. LIST_HEADER Component

**Arquivo:** `app/templates/components/list_header.html`

**Propósito:** Header padrão para todas as páginas de listagem com título, descrição e botões de ação.

### Uso Básico

```html
{% set page_title = 'Planos de Cobrança' %}
{% set page_icon = 'tags' %}
{% set page_description = 'Configure planos e cobrança' %}
{% set new_btn_url = url_for('billing.new_plan') %}
{% set table_view_key = 'billing.plans' %}
{% include 'components/list_header.html' %}
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `page_title` | string | ✅ | - | Título principal da página |
| `page_icon` | string | ❌ | - | Ícone Font Awesome (ex: 'tags', 'users', 'file-alt') |
| `page_description` | string | ❌ | - | Descrição sob o título |
| `new_btn_url` | string | ❌ | - | URL do botão "Novo" (se vazio, botão não aparece) |
| `new_btn_label` | string | ❌ | 'Novo' | Texto do botão de ação |
| `table_view_key` | string | ❌ | - | Chave para salvar preferências de tabela |
| `show_reset_btn` | bool | ❌ | true | Mostrar botão de reset de preferências |
| `extra_actions` | string | ❌ | - | HTML com botões adicionais |

### Exemplos Avançados

#### Com botões extras
```html
{% set page_title = 'Planos' %}
{% set page_icon = 'tags' %}
{% set new_btn_url = url_for('billing.new_plan') %}
{% set extra_actions %}
    <a href="{{ url_for('billing.export_plans') }}" class="btn btn-outline-info">
        <i class="fas fa-download me-1"></i>Exportar
    </a>
{% endset %}
{% include 'components/list_header.html' %}
```

#### Sem botão novo
```html
{% set page_title = 'Auditoria' %}
{% set page_icon = 'history' %}
{% set page_description = 'Histórico de alterações no sistema' %}
{% set new_btn_url = '' %}
{% include 'components/list_header.html' %}
```

---

## 2. STAT_CARD Component

**Arquivo:** `app/templates/components/stat_card.html`

**Propósito:** Card de estatísticas com ícone, valor e descrição.

### Uso Básico

```html
<div class="row mb-4">
    {% set stat_icon = 'file-alt' %}
    {% set stat_color = 'primary' %}
    {% set stat_label = 'Total de Planos' %}
    {% set stat_value = plans|length %}
    {% include 'components/stat_card.html' %}
    
    {% set stat_icon = 'check-circle' %}
    {% set stat_color = 'success' %}
    {% set stat_label = 'Ativos' %}
    {% set stat_value = plans|selectattr('active')|list|length %}
    {% include 'components/stat_card.html' %}
</div>
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `stat_icon` | string | ✅ | - | Ícone Font Awesome |
| `stat_color` | string | ✅ | - | Cor (primary, success, warning, info, danger) |
| `stat_label` | string | ✅ | - | Etiqueta do card |
| `stat_value` | any | ✅ | - | Valor a exibir (número, string, etc) |
| `stat_description` | string | ❌ | - | Descrição adicional abaixo do valor |
| `stat_url` | string | ❌ | - | URL para tornar o card clicável |

### Cores Disponíveis

```
primary   → Azul escuro
success   → Verde
warning   → Amarelo
info      → Azul claro
danger    → Vermelho
secondary → Cinza
```

### Exemplo com URL

```html
{% set stat_icon = 'users' %}
{% set stat_color = 'primary' %}
{% set stat_label = 'Total de Usuários' %}
{% set stat_value = total_users %}
{% set stat_url = url_for('admin.users_list') %}
{% include 'components/stat_card.html' %}
```

---

## 3. DATA_TABLE Component

**Arquivo:** `app/templates/components/data_table.html`

**Propósito:** Tabela padrão com DataTables, sorting, filtering e column reorder.

### Uso Básico

```html
{% include 'components/data_table.html' %}
    {% block table_headers %}
        <th>Nome</th>
        <th>Email</th>
        <th>Status</th>
        <th>Ações</th>
    {% endblock %}
    
    {% block table_rows %}
        {% for user in users %}
        <tr>
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>
                <span class="badge {% if user.is_active %}bg-success{% else %}bg-danger{% endif %}">
                    {% if user.is_active %}Ativo{% else %}Inativo{% endif %}
                </span>
            </td>
            <td>
                <a href="{{ url_for('admin.edit_user', user_id=user.id) }}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-edit"></i>
                </a>
            </td>
        </tr>
        {% endfor %}
    {% endblock %}
{% endinclude %}
```

### Parâmetros

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
|-----------|------|-------------|--------|-----------|
| `table_id` | string | ✅ | - | ID único da tabela (ex: 'usersTable') |
| `table_view_key` | string | ✅ | - | Chave para salvar preferências (ex: 'admin.users') |
| `table_class` | string | ❌ | 'table-hover' | Classes CSS adicionais |
| `table_headers` | block | ✅ | - | Block com `<th>` tags |
| `table_rows` | block | ✅ | - | Block com linhas `<tr>` |

### Exemplo Completo

```html
{% include 'components/data_table.html' %}
    {% set table_id = 'plansTable' %}
    {% set table_view_key = 'billing.plans' %}
    
    {% block table_headers %}
        <th>Nome</th>
        <th>Tipo</th>
        <th>Valor</th>
        <th>Ações</th>
    {% endblock %}
    
    {% block table_rows %}
        {% for plan in plans %}
        <tr>
            <td>{{ plan.name }}</td>
            <td>
                <span class="badge {% if plan.plan_type == 'per_usage' %}bg-warning{% else %}bg-info{% endif %} text-white">
                    {{ 'Por uso' if plan.plan_type == 'per_usage' else 'Mensal' }}
                </span>
            </td>
            <td>R$ {{ '%.2f'|format(plan.monthly_fee) }}</td>
            <td>
                <a href="{{ url_for('billing.edit_plan', plan_id=plan.id) }}" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-edit"></i>
                </a>
            </td>
        </tr>
        {% endfor %}
    {% endblock %}
{% endinclude %}
```

---

## 4. PADRÃO DE LAYOUT COMPLETO

### Template Básico (Recomendado)

```html
{% extends "admin/base_admin.html" %}

{% block admin_content %}
<div class="container-fluid">
    
    {# 1. Header #}
    {% set page_title = 'Seus Itens' %}
    {% set page_icon = 'file-alt' %}
    {% set page_description = 'Descrição da página' %}
    {% set new_btn_url = url_for('admin.new_item') %}
    {% set table_view_key = 'admin.items' %}
    {% include 'components/list_header.html' %}

    {# 2. Statistics (Opcional) #}
    <div class="row mb-4">
        {% set stat_icon = 'file' %}
        {% set stat_color = 'primary' %}
        {% set stat_label = 'Total' %}
        {% set stat_value = items|length %}
        {% include 'components/stat_card.html' %}
        
        {% set stat_icon = 'check' %}
        {% set stat_color = 'success' %}
        {% set stat_label = 'Ativos' %}
        {% set stat_value = items|selectattr('is_active')|list|length %}
        {% include 'components/stat_card.html' %}
    </div>

    {# 3. Data Table #}
    {% set table_id = 'itemsTable' %}
    {% set table_view_key = 'admin.items' %}
    {% include 'components/data_table.html' %}
        {% block table_headers %}
            <th>Nome</th>
            <th>Status</th>
            <th>Ações</th>
        {% endblock %}
        
        {% block table_rows %}
            {% for item in items %}
            <tr>
                <td>{{ item.name }}</td>
                <td>
                    <span class="badge {% if item.is_active %}bg-success{% else %}bg-danger{% endif %}">
                        {{ 'Ativo' if item.is_active else 'Inativo' }}
                    </span>
                </td>
                <td>
                    <a href="{{ url_for('admin.edit_item', item_id=item.id) }}" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-edit"></i>
                    </a>
                </td>
            </tr>
            {% endfor %}
        {% endblock %}
    {% endinclude %}

</div>
{% endblock %}
```

---

## 5. GUIA DE ÍCONES COMUNS

```
Arquivos/Documentos: file, file-alt, file-pdf, file-csv
Usuários: users, user, user-check, user-cog, user-tie
Administração: cog, sliders-h, wrench, tools
Visualização: eye, chart-line, chart-bar, tachometer-alt
Ações: edit, trash, check, times, undo, download, upload
Status: check-circle, times-circle, question-circle, exclamation-circle
Dados: database, server, save, folder
Financeiro: dollar-sign, credit-card, wallet, coins
Calendário: calendar, clock, hourglass-end
Mapa: map, location, globe, compass
Notificação: bell, envelope, comment, message
```

---

## 6. INTEGRAÇÃO COM DATATABLES

Os componentes já vêm pré-configurados com DataTables. Funcionalidades automáticas:

✅ **Sorting** - Clique nos headers para ordenar
✅ **Filtering** - Input de busca automático
✅ **Pagination** - Navegação entre páginas
✅ **Column Reorder** - Arraste os headers para reordenar
✅ **Per-User Preferences** - Salva automaticamente as preferências do usuário
✅ **Export** - Botões para exportar em CSV, Excel, etc

---

## 7. CHECKLIST PARA MIGRAÇÃO

Ao migrar uma página existente para usar componentes:

- [ ] Substituir header manual por `{% include 'components/list_header.html' %}`
- [ ] Substituir stat cards por `{% include 'components/stat_card.html' %}`
- [ ] Mover tabela para `{% include 'components/data_table.html' %}`
- [ ] Definir `table_id` e `table_view_key` corretos
- [ ] Testar DataTables (sort, filter, reorder)
- [ ] Testar responsividade em mobile
- [ ] Testar preferências de usuário (refresh a página)
- [ ] Validar links de ações

---

## 8. TROUBLESHOOTING

### DataTables não inicializa
- ✅ Verificar console (F12 → Console tab)
- ✅ Confirmar `table_id` é único
- ✅ Confirmar `table_view_key` é definido
- ✅ Confirmar jQuery + DataTables carregam (Network tab)

### Componentes não aparecem
- ✅ Verificar caminho: `app/templates/components/`
- ✅ Verificar sintaxe do include: `{% include 'components/...' %}`
- ✅ Verificar variáveis de contexto definidas antes do include

### Preferências não salvam
- ✅ Verificar que `/api/user/preferences` retorna 200
- ✅ Verificar que usuário está autenticado (login_required)
- ✅ Verificar Database (table_preferences criada)

---

## 9. EXEMPLO REAL - MIGRAÇÃO ANTES/DEPOIS

### ANTES (plan.html - 283 linhas)
```html
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h1 class="h3 mb-1"><i class="fas fa-tags"></i> Planos de cobrança</h1>
        <p class="text-muted mb-0">Configure planos...</p>
    </div>
    <a href="{{ url_for('admin.users_list') }}" class="btn btn-outline-secondary">
        <i class="fas fa-users-cog"></i> Usuários / planos
    </a>
</div>

<div class="row">
    <div class="col-lg-4">
        <!-- Form -->
    </div>
    <div class="col-lg-8">
        <div class="card shadow-sm">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table mb-0">
                        <!-- Table -->
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
```

### DEPOIS (plans_refactored.html - ~150 linhas)
```html
{% extends "admin/base_admin.html" %}

{% block admin_content %}
<div class="container-fluid">
    {% set page_title = 'Planos de Cobrança' %}
    {% set page_icon = 'tags' %}
    {% set page_description = 'Configure planos...' %}
    {% set new_btn_url = url_for('billing.new_plan') %}
    {% include 'components/list_header.html' %}

    <div class="row">
        <div class="col-lg-4">
            <!-- Form (inalterado) -->
        </div>
        <div class="col-lg-8">
            <!-- Table com data_table component -->
        </div>
    </div>
</div>
{% endblock %}
```

**Redução:** 47% ↓ de código!

---

## CONCLUSÃO

Com esses componentes você consegue:
- ✅ Reduzir código em 60%
- ✅ Garantir consistência visual
- ✅ Fazer mudanças globais em 1 lugar
- ✅ Onboarding mais rápido para novos devs
- ✅ Menos bugs por inconsistência

