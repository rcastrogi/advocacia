# DEBUG GUIDE - Como Identificar Erros

## Passo 1: Abra o Console do Navegador

**Chrome/Edge/Firefox:**
- Pressione `F12` ou `Ctrl+Shift+I`
- Vá para a aba **Console**

## Passo 2: Reproduce o Erro

1. Navegue até o Dashboard
2. Clique no elemento que causa o erro
3. Observe as mensagens no console

## Passo 3: Procure por Mensagens

No console, você verá mensagens assim:

### Mensagens do DEBUG-CONSOLE (Nosso Sistema)
```
[DEBUG-CONSOLE] Enhanced debug console initialized
[FETCH-abc123] GET /admin/dashboard
[FETCH-abc123] Response 200 /admin/dashboard
[FETCH-abc123] Error body: {...}
[XHR] POST /api/endpoint
[UNHANDLED-REJECTION] Promise rejeitada: ...
```

### Se Houver um Erro:
```
[FETCH-abc123] Network error: ...
[UNHANDLED-REJECTION] {reason: Error(...), message: "...", stack: "..."}
[ERROR] ...
```

## Passo 4: Ver Todos os Logs

No console, execute:
```javascript
window.showAllLogs()
```

Isso mostrará TODOS os logs desde o carregamento da página.

## Passo 5: Copiar e Enviar

1. Clique com botão direito no console
2. Selecione "Copy All"
3. Cole aqui para análise

---

## Erros Comuns

### "Ocorreu erro inesperado"
- Veja o console para a mensagem específica
- Procure por `[FETCH-]` com status >= 400
- Procure por `[UNHANDLED-REJECTION]`

### "Erro de conexão"
- Verifique se o servidor está rodando
- Veja se há `[FETCH-] Network error`

### Nada no console?
- Abra o console ANTES de carregar a página
- Se ainda nada, pode ser erro do navegador, não da app

---

## Logs do Servidor

Verifique os logs:
```bash
tail -f logs/petitio.log
```

Procure por:
- `ERROR`
- `Traceback`
- `Exception`

---

## Próximas Ações

1. **Abra o browser console (F12)**
2. **Reproduza o erro**
3. **Procure pelas mensagens [FETCH-] ou [UNHANDLED-REJECTION]**
4. **Cole a mensagem de erro aqui**
