# 🚀 Aplicar Migrações no Render

## 📋 Migrações Pendentes

As seguintes mudanças de banco precisam ser aplicadas no Render:

### ✅ Migrações Já Criadas:
- `7a6c7aa40f2c_add_flexible_billing_periods.py` - Campos de períodos flexíveis no BillingPlan
- Campos de política de cancelamento no Subscription

## 🔧 Como Aplicar no Render

### Método 1: Shell do Render (Recomendado)

1. **Acesse o dashboard do Render**
2. **Vá para seu serviço web**
3. **Clique em "Shell"** (ícone do terminal)
4. **Execute os comandos:**

```bash
# Entrar no diretório do projeto
cd /opt/render/project/src

# Ativar ambiente virtual (se existir)
source venv/bin/activate

# Aplicar migrações
flask db upgrade

# Verificar status
flask db current
```

### Método 2: Deploy com Migração

Adicione ao seu `build.sh` ou script de deploy:

```bash
#!/bin/bash
# build.sh ou deploy script

# ... outros comandos ...

# Aplicar migrações após deploy
echo "🔄 Aplicando migrações..."
flask db upgrade

# ... continuar deploy ...
```

### Método 3: Comando Manual via API

Se você tem acesso SSH ou via API do Render:

```bash
# Via SSH (se disponível)
render ssh your-service-name
cd /opt/render/project/src
flask db upgrade
```

## 📊 Verificar Status

Após aplicar, verifique se as migrações foram aplicadas:

```bash
flask db current
# Deve mostrar: 996cf696b786 (head)
```

## ⚠️ Importante

- **Backup primeiro**: Sempre faça backup do banco antes
- **Teste local**: Teste as migrações localmente primeiro
- **Monitoramento**: Monitore logs após aplicar
- **Rollback**: Tenha plano de rollback se algo der errado

## 🔍 Comandos Úteis

```bash
# Ver histórico de migrações
flask db history

# Ver status atual
flask db current

# Ver migrações pendentes
flask db check

# Downgrade (se necessário)
flask db downgrade <revision_id>
```

## 📞 Suporte

Se tiver problemas:
1. Verifique logs do Render
2. Confirme variáveis de ambiente (DATABASE_URL)
3. Teste conexão com banco: `flask db check`