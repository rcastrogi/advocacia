# Guia de Migração - Paginação Universal

## 📋 Objetivo

Padronizar paginação em TODAS as listagens do Petitio usando `PaginationHelper`.

## 🔄 Antes vs Depois

### ❌ Antes (inconsistente)
```python
@bp.route("/usuarios")
def users_list():
    page = request.args.get("page", 1, type=int)
    per_page = 20
    
    query = User.query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template("admin/users.html", users=pagination.items, pagination=pagination)
```

### ✅ Depois (universal)
```python
from app.utils.pagination import PaginationHelper

@bp.route("/usuarios")
def users_list():
    search = request.args.get("search", "").strip()
    
    query = User.query.filter(User.name.ilike(f"%{search}%")).order_by(User.created_at.desc())
    
    pagination = PaginationHelper(
        query=query,
        per_page=20,
        filters={'search': search}
    )
    
    return render_template("admin/users.html", items=pagination.items, pagination=pagination)
```

## 📝 Passo a Passo

### 1. Importar PaginationHelper
```python
from app.utils.pagination import PaginationHelper
```

### 2. Substituir código de paginação
```python
# Antigo
pagination = query.paginate(page=page, per_page=per_page, error_out=False)

# Novo
pagination = PaginationHelper(
    query=query,
    per_page=per_page,
    filters={'search': search, 'status': status}  # Filtros ativos
)
```

### 3. Usar no template
```html
{# Antigo #}
<table>
    {% for item in items %}
    <tr>...</tr>
    {% endfor %}
</table>

{# Novo - agora com acesso universal #}
<table>
    {% for item in pagination %}  {# Itera diretamente #}
    <tr>...</tr>
    {% endfor %}
</table>

{# Paginação reutilizável #}
{% include 'components/pagination.html' %}
```

## 🎯 Rotas a Migrar (70% → 100%)

### Admin
- [ ] `/admin/usuarios` - users_list()
- [ ] `/admin/audit-logs` - audit_logs()
- [ ] `/admin/roadmap/feedback` - roadmap_feedback()
- [ ] `/admin/petition-sections` - petition_sections_list()
- [ ] `/admin/petition-types` - petition_types_list()
- [ ] `/admin/petition-models` - petition_models_list()

### Usuário
- [ ] `/clients` - clients_list()
- [ ] `/processes` - processes_list()
- [ ] `/petitions/saved` - saved_list()
- [ ] `/ai/generations` - generations_history()
- [ ] `/chat/history` - chat_history()

### API
- [ ] `/api/processes` - get_processes()
- [ ] `/api/notifications` - get_notifications()

## 💡 Benefícios

✅ **Consistência** - Mesmo padrão em todas as páginas
✅ **Acessibilidade** - Componente ARIA-compliant
✅ **Responsivo** - Funciona bem em mobile
✅ **Manutenibilidade** - Uma única fonte de verdade
✅ **Performance** - Limite máximo de per_page (anti-abuso)

## 🧪 Teste

```python
# Testar PaginationHelper
from app.utils.pagination import PaginationHelper
from app.models import User

pagination = PaginationHelper(
    query=User.query.order_by(User.id),
    per_page=20
)

# Acessar propriedades
print(pagination.page)      # 1
print(pagination.total)     # Número total
print(pagination.items)     # Itens da página
print(pagination.pages)     # Total de páginas
```

## 📱 Template Minimalista

Se preferir um template simpler para mobile:

```html
{% if pagination.pages > 1 %}
<nav class="pagination-simple" aria-label="Paginação">
    <div class="btn-group" role="group">
        {% if pagination.has_prev %}
        <a href="?page={{ pagination.prev_num }}" class="btn btn-sm btn-outline-secondary">
            ← Anterior
        </a>
        {% endif %}
        
        <span class="btn btn-sm btn-secondary disabled">
            {{ pagination.page }} / {{ pagination.pages }}
        </span>
        
        {% if pagination.has_next %}
        <a href="?page={{ pagination.next_num }}" class="btn btn-sm btn-outline-secondary">
            Próximo →
        </a>
        {% endif %}
    </div>
</nav>
{% endif %}
```

## 🔗 Referências

- Helper: `app/utils/pagination.py`
- Componente: `app/templates/components/pagination.html`
- Instruções: `.github/copilot-instructions.md`
