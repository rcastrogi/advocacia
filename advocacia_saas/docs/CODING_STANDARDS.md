# Padrões de Código - Petitio SaaS

Este documento define os padrões de código e segurança do projeto.
**Use este arquivo como referência ao criar novas funcionalidades.**

---

## 🔒 Segurança

### Backend (Python/Flask)

#### 1. Rate Limiting em APIs
```python
from app.rate_limits import COUPON_LIMIT, AUTH_API_LIMIT, CRITICAL_LIMIT

@bp.route("/api/endpoint", methods=["POST"])
@limiter.limit(AUTH_API_LIMIT)  # SEMPRE adicionar rate limit em APIs
@login_required
def api_endpoint():
    ...
```

**Limites disponíveis em `app/rate_limits.py`:**
- `PUBLIC_API_LIMIT = "10 per minute"` - APIs públicas
- `AUTH_API_LIMIT = "30 per minute"` - APIs autenticadas
- `ADMIN_API_LIMIT = "60 per minute"` - APIs admin
- `FORM_SUBMIT_LIMIT = "5 per minute"` - Envio de formulários
- `LOGIN_LIMIT = "5 per minute"` - Login (anti brute-force)
- `CRITICAL_LIMIT = "2 per minute"` - Operações críticas
- `COUPON_LIMIT = "10 per minute"` - Cupons

#### 2. Sanitização de Inputs
```python
import re

def sanitize_code(code):
    """Remove caracteres não permitidos"""
    if not code:
        return ""
    return re.sub(r'[^A-Z0-9\-]', '', code.upper())[:20]

def sanitize_text(text, max_length=255):
    """Remove HTML e limita tamanho"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text.strip())
    return text[:max_length]
```

#### 3. Validação de JSON Request
```python
@bp.route("/api/endpoint", methods=["POST"])
def api_endpoint():
    data = request.get_json()
    
    # SEMPRE verificar se data existe
    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400
    
    # Sanitizar inputs
    raw_value = data.get("field", "")
    value = sanitize_code(raw_value)
    
    # Validar tamanho mínimo se necessário
    if len(value) < 3:
        return jsonify({"success": False, "message": "Valor muito curto"}), 400
```

#### 4. Retorno de JSON com Tipos Garantidos
```python
# SEMPRE garantir tipos nos retornos JSON
return jsonify({
    "success": True,
    "count": int(value or 0),           # Garante inteiro
    "name": str(value or ""),            # Garante string
    "items": list(value or []),          # Garante lista
    "date": obj.date.isoformat() if obj.date else None  # Data segura
})
```

#### 5. Decoradores de Autorização
```python
from flask_login import login_required
from app.decorators import master_required, admin_required

# Ordem correta dos decoradores:
@bp.route("/admin/endpoint")
@limiter.limit(ADMIN_API_LIMIT)  # 1. Rate limit primeiro
@login_required                   # 2. Depois login
@master_required                  # 3. Depois role
def admin_endpoint():
    ...
```

---

### Frontend (JavaScript)

#### 1. Prevenção de XSS

**NUNCA usar:**
```javascript
// ❌ ERRADO - Vulnerável a XSS
element.innerHTML = `<div>${userInput}</div>`;
element.innerHTML = data.message;
onclick="doSomething('${code}')"
```

**SEMPRE usar:**
```javascript
// ✅ CORRETO - Seguro contra XSS

// Para texto simples:
element.textContent = userInput;

// Para criar elementos com dados do usuário:
const div = document.createElement('div');
div.textContent = userInput;
parent.appendChild(div);

// Para valores validados, armazene em variável:
let validatedCode = null;

function validateCode() {
    // Após validação bem-sucedida:
    validatedCode = sanitizedCode;
}

function applyCode() {
    if (!validatedCode) return;
    // Usa validatedCode em vez de pegar do DOM
}
```

#### 2. Função de Escape HTML
```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

#### 3. Sanitização de Inputs
```javascript
function sanitizeCode(code) {
    return code.replace(/[^A-Z0-9\-]/g, '').substring(0, 20);
}
```

#### 4. Validação de Tipos CSS
```javascript
function showFeedback(type, message) {
    // SEMPRE validar valores que viram classes CSS
    const allowedTypes = ['success', 'danger', 'warning', 'info'];
    const safeType = allowedTypes.includes(type) ? type : 'info';
    
    element.className = `alert alert-${safeType}`;
}
```

#### 5. CSRF Token
```javascript
// SEMPRE enviar CSRF token em requisições POST
const response = await fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
    },
    body: JSON.stringify(data)
});

function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}
```

---

## 📁 Estrutura de Templates

### Herança de Templates
```html
<!-- Páginas admin -->
{% extends "admin/base_admin.html" %}
{% block admin_content %}...{% endblock %}

<!-- Páginas normais -->
{% extends "base.html" %}
{% block content %}...{% endblock %}
```

### Passagem de Data/Hora para Templates
```python
# Na route:
from datetime import datetime, timezone

return render_template(
    "template.html",
    now=datetime.now(timezone.utc),  # SEMPRE passar now do backend
    items=items
)
```

```html
<!-- No template: -->
{% if item.expires_at and item.expires_at < now %}
    <span class="badge bg-danger">Expirado</span>
{% endif %}
```

---

## 🗄️ Migrations

### Criar Nova Migration
```bash
# Após alterar models.py:
flask db revision --autogenerate -m "descricao_da_alteracao"
flask db upgrade
```

### Convenção de Nomes
- `add_xxx_table` - Nova tabela
- `add_xxx_column_to_yyy` - Nova coluna
- `remove_xxx_from_yyy` - Remover coluna
- `update_xxx_constraints` - Alterar constraints

---

## 🎨 Padrões de UI

### Cards de Estatísticas
```html
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card border-0 shadow-sm">
            <div class="card-body text-center">
                <h3 class="mb-1 text-primary">{{ stats.total }}</h3>
                <small class="text-muted">Label</small>
            </div>
        </div>
    </div>
</div>
```

### Botões de Ação
```html
<!-- Ação principal -->
<a href="..." class="btn btn-primary">
    <i class="fas fa-plus me-1"></i> Criar
</a>

<!-- Ação secundária -->
<a href="..." class="btn btn-outline-secondary btn-sm">
    <i class="fas fa-eye me-1"></i> Ver
</a>

<!-- Ação perigosa -->
<button class="btn btn-outline-danger btn-sm" onclick="confirmDelete(...)">
    <i class="fas fa-trash"></i>
</button>
```

### Badges de Status
```html
<span class="badge bg-success">Ativo</span>
<span class="badge bg-warning text-dark">Pendente</span>
<span class="badge bg-danger">Expirado</span>
<span class="badge bg-secondary">Inativo</span>
```

---

## ✅ Checklist para Nova Funcionalidade

### Backend
- [ ] Rate limiting aplicado nas APIs
- [ ] Inputs sanitizados
- [ ] Validação de tipos (int, str, etc.)
- [ ] Limites máximos definidos
- [ ] Decoradores de autorização corretos
- [ ] Retornos JSON com tipos garantidos
- [ ] Erros tratados com try/except

### Frontend
- [ ] Sem innerHTML com dados do usuário
- [ ] CSRF token enviado
- [ ] Funções de sanitização usadas
- [ ] Classes CSS validadas
- [ ] Manipulação DOM segura
- [ ] Estados de loading implementados

### Templates
- [ ] Herança correta (base_admin.html ou base.html)
- [ ] Variável `now` passada se necessário
- [ ] Escape automático do Jinja2 não desabilitado
- [ ] Links com url_for()

### Database
- [ ] Migration criada
- [ ] Migration aplicada no Render
- [ ] Índices em colunas de busca
- [ ] Foreign keys definidas
