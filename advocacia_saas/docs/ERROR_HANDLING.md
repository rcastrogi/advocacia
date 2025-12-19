# 🛡️ Sistema de Tratamento de Erros - Petitio

## 📋 Visão Geral

O sistema de tratamento de erros do Petitio garante que os usuários vejam mensagens amigáveis ao invés de erros técnicos assustadores. Todos os erros são capturados, logados e exibidos de forma clara.

---

## 🎯 Funcionalidades

### 1. **Error Handlers HTTP** (`app/error_handlers.py`)

Captura todos os erros HTTP comuns:

| Código | Erro | Mensagem ao Usuário |
|--------|------|---------------------|
| 400 | Bad Request | "Requisição inválida. Verifique os dados enviados." |
| 403 | Forbidden | "Você não tem permissão para acessar este recurso." |
| 404 | Not Found | "Página não encontrada." |
| 429 | Too Many Requests | "Muitas tentativas. Aguarde alguns minutos." |
| 500 | Internal Server Error | "Erro interno. Nossa equipe foi notificada." |
| 503 | Service Unavailable | "Serviço temporariamente indisponível." |

### 2. **Páginas de Erro Customizadas**

Cada erro tem uma página HTML dedicada:
- `app/templates/errors/400.html`
- `app/templates/errors/403.html`
- `app/templates/errors/404.html`
- `app/templates/errors/429.html`
- `app/templates/errors/500.html`
- `app/templates/errors/503.html`

**Recursos das páginas:**
- ✅ Design profissional e amigável
- ✅ Ícones SVG ilustrativos
- ✅ Sugestões de ação (voltar, ir ao dashboard, etc.)
- ✅ Links úteis
- ✅ Contador regressivo na página 429

### 3. **Toasts para Requisições Ajax**

Sistema JavaScript automático que intercepta erros em:
- `fetch()` nativo
- jQuery Ajax
- Erros JavaScript não capturados
- Promises rejeitadas

**Arquivo:** `app/static/js/error-handling.js`

### 4. **Logging Estruturado**

- Logs salvos em `logs/petitio.log`
- Rotação automática (10MB por arquivo, 10 backups)
- Integração com Sentry para erros críticos

---

## 🚀 Como Usar

### Backend - Retornar Erro em API

```python
from flask import jsonify, abort

@bp.route('/api/resource')
def get_resource():
    resource = Resource.query.get(id)
    
    if not resource:
        # Para requisições Ajax/JSON
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Recurso não encontrado'
            }), 404
        
        # Para navegação normal
        abort(404)
    
    return jsonify(resource.to_dict())
```

### Backend - Lançar Exceção Customizada

```python
from werkzeug.exceptions import Forbidden

@bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.user_type != 'master':
        # Flash message + página de erro 403
        flash('Acesso negado. Apenas administradores.', 'danger')
        raise Forbidden('Acesso negado')
    
    return render_template('admin/users.html')
```

### Frontend - Toast Manual

```javascript
// Toast de erro
showErrorToast(
    'Falha ao salvar os dados',  // mensagem
    'Erro',                       // título (opcional)
    5000                          // duração em ms (opcional)
);

// Toast de sucesso
showSuccessToast(
    'Cliente salvo com sucesso!',
    'Sucesso',
    3000
);
```

### Frontend - Fetch com Tratamento Automático

```javascript
// O error-handling.js intercepta automaticamente
fetch('/api/resource', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {'Content-Type': 'application/json'}
})
.then(response => response.json())
.then(data => {
    // Sucesso
    showSuccessToast('Operação concluída!');
})
// Erro já é tratado automaticamente com toast
.catch(error => {
    console.error('Erro:', error);
});
```

### jQuery Ajax com Tratamento Automático

```javascript
// O error-handling.js intercepta automaticamente
$.ajax({
    url: '/api/resource',
    method: 'POST',
    data: JSON.stringify(data),
    contentType: 'application/json',
    success: function(response) {
        showSuccessToast('Operação concluída!');
    }
    // error: não precisa - tratado automaticamente
});
```

---

## 📊 Fluxo de Tratamento de Erros

```
┌─────────────────┐
│  Erro Ocorre    │
└────────┬────────┘
         │
         ├──→ Requisição Ajax/JSON?
         │    ├─ Sim → Interceptado por error-handling.js
         │    │         └─ Toast de erro exibido
         │    │
         │    └─ Não → Error handler do Flask
         │              └─ Página de erro customizada
         │
         ├──→ Log salvo em logs/petitio.log
         │
         └──→ Sentry notificado (erros 500+)
```

---

## 🎨 Customização

### Adicionar Novo Tipo de Erro

1. **Criar handler em `error_handlers.py`:**

```python
@app.errorhandler(418)
def teapot_error(error):
    """Erro 418 - I'm a teapot"""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Sou um bule de chá!',
            'code': 418
        }), 418
    
    return render_template('errors/418.html'), 418
```

2. **Criar template `templates/errors/418.html`:**

```html
{% extends "base.html" %}
{% block title %}I'm a teapot - Petitio{% endblock %}
{% block content %}
<!-- Seu HTML aqui -->
{% endblock %}
```

### Customizar Mensagens de Toast

Edite `static/js/error-handling.js`:

```javascript
// Mudar duração padrão
function showErrorToast(message, title = 'Erro', duration = 7000) { // 7 segundos
    // ...
}

// Adicionar ícones diferentes
const toastHTML = `
    <div class="toast-header bg-danger text-white">
        <i class="fas fa-robot me-2"></i> <!-- ícone customizado -->
        <strong class="me-auto">${title}</strong>
        <!-- ... -->
    </div>
`;
```

### Customizar Estilos de Toast

Edite `static/css/error-toasts.css`:

```css
/* Toast de erro mais dramático */
.error-toast .toast-header {
    background: linear-gradient(135deg, #ff0000, #990000) !important;
    box-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
}

/* Animação diferente */
@keyframes bounce {
    0%, 100% { transform: translateX(0); }
    50% { transform: translateX(-10px); }
}

.toast.showing {
    animation: bounce 0.5s ease-out;
}
```

---

## 🧪 Testando o Sistema

### Teste 1: Erro 404

```bash
# Navegue para URL inexistente
http://localhost:5000/pagina-que-nao-existe

# Deve mostrar página 404 customizada
```

### Teste 2: Erro 403 (Acesso Negado)

```python
# Como usuário não-admin, tente acessar
http://localhost:5000/usuarios

# Deve mostrar página 403
```

### Teste 3: Rate Limiting (429)

```bash
# Faça 11 tentativas de login em menos de 1 minuto
# 11ª tentativa deve mostrar erro 429
```

### Teste 4: Toast de Erro Ajax

```javascript
// No console do navegador
fetch('/api/endpoint-invalido', {
    method: 'POST',
    body: JSON.stringify({test: 'data'}),
    headers: {'Content-Type': 'application/json'}
});

// Deve exibir toast de erro no canto superior direito
```

### Teste 5: Toast Manual

```javascript
// No console do navegador
showErrorToast('Teste de erro', 'Atenção', 3000);
showSuccessToast('Teste de sucesso', 'Parabéns', 3000);
```

### Teste 6: Erro JavaScript Não Capturado

```javascript
// No console do navegador
throw new Error('Erro de teste');

// Em produção, deve exibir toast genérico
// Em desenvolvimento, console mostrará stack trace
```

---

## 📝 Boas Práticas

### ✅ **DO**

1. **Sempre retorne JSON em APIs:**
   ```python
   return jsonify({'success': False, 'error': 'Mensagem clara'}), 400
   ```

2. **Use flash messages para navegação normal:**
   ```python
   flash('Operação concluída com sucesso!', 'success')
   ```

3. **Seja específico nas mensagens:**
   ```python
   # ❌ Ruim
   return jsonify({'error': 'Erro'}), 400
   
   # ✅ Bom
   return jsonify({'error': 'Email já cadastrado. Use outro email.'}), 400
   ```

4. **Log erros importantes:**
   ```python
   logger.error(f'Falha ao salvar usuário: {str(e)}', exc_info=True)
   ```

### ❌ **DON'T**

1. **Não exponha detalhes internos:**
   ```python
   # ❌ Ruim
   return jsonify({'error': str(e)}), 500  # Expõe stack trace
   
   # ✅ Bom
   logger.error(f'Erro interno: {str(e)}', exc_info=True)
   return jsonify({'error': 'Erro interno. Tente novamente.'}), 500
   ```

2. **Não ignore erros silenciosamente:**
   ```python
   # ❌ Ruim
   try:
       risky_operation()
   except:
       pass  # Erro ignorado!
   
   # ✅ Bom
   try:
       risky_operation()
   except Exception as e:
       logger.error(f'Falha na operação: {str(e)}', exc_info=True)
       flash('Não foi possível completar a operação', 'danger')
   ```

3. **Não mostre mensagens técnicas para usuários:**
   ```python
   # ❌ Ruim
   return jsonify({'error': 'IntegrityError: duplicate key'}), 400
   
   # ✅ Bom
   return jsonify({'error': 'Este registro já existe'}), 400
   ```

---

## 🔍 Monitoramento

### Verificar Logs

```bash
# Ver últimas 50 linhas
tail -n 50 logs/petitio.log

# Seguir log em tempo real
tail -f logs/petitio.log

# Buscar erros específicos
grep "ERROR" logs/petitio.log
```

### Sentry Dashboard

Acesse: https://sentry.io/organizations/your-org/issues/

- Erros agrupados por tipo
- Stack traces completos
- Performance monitoring
- Alertas por email/Slack

---

## 📚 Referências

- [Flask Error Handling](https://flask.palletsprojects.com/en/2.3.x/errorhandling/)
- [Bootstrap Toasts](https://getbootstrap.com/docs/5.3/components/toasts/)
- [Sentry Flask Integration](https://docs.sentry.io/platforms/python/guides/flask/)
- [HTTP Status Codes](https://httpstat.us/)

---

**✅ Sistema de tratamento de erros completo e amigável implementado!**
