# Configurar Petitio Code Agent MCP

## 📦 Instalação

### 1. Instale as dependências

```bash
cd advocacia_saas/.mcp/petitio-agent
npm install
```

### 2. Compile o TypeScript

```bash
npm run build
```

### 3. Reinicie o VS Code

```
Ctrl+Shift+P > Developer: Reload Window
```

## 🎮 Como Usar o Agent

### Opção 1: Chat do Copilot

Abra o Chat do Copilot (`Ctrl+L`) e veja as opções de agent:

```
Selecione o agent → "Petitio Code Agent"
```

Depois digite:

```
Analisa esse código aqui... [colar código]
```

### Opção 2: Usar como Agent no Chat

```
@petitio-code-agent Verificar vulnerabilidades neste arquivo
```

### Opção 3: Commands

```
Ctrl+Shift+P > Copilot: Agent...
```

Selecione "Petitio Code Agent"

## 🛠️ Ferramentas Disponíveis

O agent oferece 6 ferramentas:

1. **analyze_security** - Análise de vulnerabilidades
2. **check_rate_limits** - Verifica rate limiting
3. **validate_decorators** - Valida ordem de decoradores
4. **check_xss** - Detecta XSS
5. **check_input_sanitization** - Verifica sanitização
6. **suggest_fix** - Sugere correções

## 📝 Exemplos de Uso

### Exemplo 1: Analisar Segurança
```
Analisa esse código Python para vulnerabilidades:

@bp.route("/api/users", methods=["POST"])
@login_required
def create_user():
    data = request.get_json()
    name = data.get("name")
    return jsonify({"success": True})
```

**Resultado:**
```
❌ Rate limiting obrigatório está faltando em rotas
⚠️  JSON não validado após get_json()
```

### Exemplo 2: Verificar Rate Limits
```
@petitio-code-agent Verificar rate limits neste arquivo
[colar código Flask]
```

### Exemplo 3: Detectar XSS
```
Detecta XSS neste código:

element.innerHTML = `<div>${userInput}</div>`;
```

**Resultado:**
```
❌ innerHTML com template literals detectado - Risco de XSS
```

### Exemplo 4: Sugerir Correção
```
Esse código tem problema: innerHTML com interpolação
Aqui está o código:

element.innerHTML = `<div>${userInput}</div>`;
```

## 🔍 Padrões de Detecção

O agent verifica:

### Python
- ✅ Rate limiting em rotas
- ✅ SQL Injection (string interpolation)
- ✅ JSON validation
- ✅ Input sanitization
- ✅ Decorators order

### JavaScript/TypeScript
- ✅ XSS (innerHTML, onclick)
- ✅ CSRF tokens
- ✅ eval() usage
- ✅ DOM manipulation safety

## 🚀 Desenvolvimento

### Adicionar Nova Ferramenta

1. Abra `src/index.ts`
2. Adicione na array `tools`:

```typescript
{
  name: "nova_ferramenta",
  description: "...",
  inputSchema: { ... }
}
```

3. Adicione handler:

```typescript
case "nova_ferramenta":
  return handleNovaFerramenta(args);
```

4. Implemente:

```typescript
function handleNovaFerramenta(args: Record<string, unknown>) {
  // Sua lógica
  return { content: [{ type: "text", text: result }] };
}
```

5. Compile e teste:

```bash
npm run build
# Reload VS Code
```

## 🐛 Troubleshooting

### Agent não aparece

1. Verificar se compilou:
```bash
ls dist/index.js
```

2. Verificar settings.json:
```json
"github.copilot.advanced": {
  "mcp": { "enabled": true }
}
```

3. Recarregar VS Code:
```
Ctrl+Shift+P > Developer: Reload Window
```

### Erro no console

Abra Developer Tools:
```
Ctrl+Shift+P > Developer: Toggle Developer Tools
```

Procure por erros relacionados a "petitio-code-agent"

## 📚 Arquitetura MCP

```
VS Code (Client)
    ↓
    ├─ Copilot Chat UI
    └─ Copilot Agent System
        ↓
    .mcp/petitio-agent/dist/index.js (MCP Server)
        ├─ Tool: analyze_security
        ├─ Tool: check_rate_limits
        ├─ Tool: validate_decorators
        ├─ Tool: check_xss
        ├─ Tool: check_input_sanitization
        └─ Tool: suggest_fix
```

## 📄 Referências

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [VS Code Copilot Extensions](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)
- [copilot-instructions.md](../../.github/copilot-instructions.md)
