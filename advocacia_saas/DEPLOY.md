# 🚀 Guia de Deploy - Advocacia SaaS

Este guia mostra como hospedar o projeto nas principais plataformas.

## Pré-requisitos

1. Conta no GitHub com o repositório
3. **Redis (Opcional mas Recomendado)** - Para cache e rate limiting
   - `REDIS_URL` - URL da instância Redis

---

## 🔴 Redis Setup (Cache & Rate Limiting)

**Benefícios:** Cache de queries, rate limiting distribuído, melhor performance

### Render (Recomendado)
1. No dashboard Render, vá para **Redis**
2. Clique **"Create Redis"**
3. Escolha plano:
   - **Free**: 512MB (suficiente para testes)
   - **Paid**: $6/mês (10GB, produção)
4. Copie a **REDIS_URL** gerada
5. Adicione nas variáveis de ambiente do seu web service

### Railway
1. No dashboard, clique **"+ Add"** → **"Database"**
2. Selecione **Redis**
3. Configure e copie a connection URL
4. Adicione como `REDIS_URL` nas variáveis de ambiente

### Variáveis de Ambiente Redis
```bash
# Obrigatório
REDIS_URL=redis://username:password@host:port

# Opcional (padrões funcionam)
REDIS_CACHE_DB=0          # DB para cache
REDIS_RATELIMIT_DB=1      # DB para rate limiting
CACHE_DEFAULT_TIMEOUT=300 # Timeout em segundos
CACHE_KEY_PREFIX=petitio  # Prefixo das chaves
```

### Teste da Configuração
```bash
# Execute o script de teste
python test_redis.py
```

### Sem Redis
- O sistema funciona normalmente usando cache em memória
- Rate limiting será por instância (não distribuído)
- Performance será menor em alta carga

---

## 🚂 Railway (Recomendado)

**Custo:** ~$5-20/mês | **Dificuldade:** Fácil

### Passos:

1. Acesse [railway.app](https://railway.app) e faça login com GitHub

2. Clique em **"New Project"** → **"Deploy from GitHub repo"**

3. Selecione o repositório `advocacia`

4. Railway detectará automaticamente o projeto Python

5. Configure as variáveis de ambiente:
   - Vá em **Variables** → **Add Variable**
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/postgres
   SECRET_KEY=sua-chave-secreta-aqui
   STRIPE_SECRET_KEY=sk_live_xxx
   STRIPE_PUBLIC_KEY=pk_live_xxx
   FLASK_ENV=production
   ```

6. Deploy automático será iniciado

7. Acesse o domínio gerado: `seu-app.up.railway.app`

### Domínio Personalizado:
- Vá em **Settings** → **Networking** → **Custom Domain**
- Adicione seu domínio e configure DNS

---

## 🎨 Render

**Custo:** $7/mês (Starter) ou Free (hiberna) | **Dificuldade:** Fácil

### Passos:

1. Acesse [render.com](https://render.com) e faça login

2. Clique em **"New +"** → **"Web Service"**

3. Conecte seu repositório GitHub

4. Configure:
   - **Name:** advocacia-saas
   - **Region:** Oregon (ou mais próximo)
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn run:app --bind 0.0.0.0:$PORT`

5. Adicione variáveis de ambiente em **Environment**

6. Escolha o plano e clique em **Create Web Service**

### Alternativa com Blueprint:
```bash
# O arquivo render.yaml já está configurado
# Basta ir em Dashboard → Blueprints → New Blueprint
```

---

## 🪁 Fly.io

**Custo:** ~$5-10/mês | **Dificuldade:** Médio (requer CLI)

### Passos:

1. Instale o Fly CLI:
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   
   # Ou via scoop
   scoop install flyctl
   ```

2. Faça login:
   ```bash
   fly auth login
   ```

3. No diretório do projeto, inicie:
   ```bash
   fly launch
   # Escolha região: gru (São Paulo)
   # Não crie banco PostgreSQL (usamos Supabase)
   ```

4. Configure secrets:
   ```bash
   fly secrets set DATABASE_URL="postgresql://..."
   fly secrets set SECRET_KEY="sua-chave"
   fly secrets set STRIPE_SECRET_KEY="sk_live_xxx"
   fly secrets set STRIPE_PUBLIC_KEY="pk_live_xxx"
   fly secrets set FLASK_ENV="production"
   ```

5. Deploy:
   ```bash
   fly deploy
   ```

6. Acesse: `seu-app.fly.dev`

---

## 🌊 DigitalOcean App Platform

**Custo:** $5-12/mês | **Dificuldade:** Fácil

### Passos:

1. Acesse [cloud.digitalocean.com](https://cloud.digitalocean.com)

2. Vá em **Apps** → **Create App**

3. Conecte GitHub e selecione o repositório

4. Configure:
   - **Type:** Web Service
   - **Run Command:** `gunicorn run:app --bind 0.0.0.0:$PORT`
   - **HTTP Port:** 8080

5. Adicione variáveis de ambiente

6. Escolha plano Basic ($5/mês)

7. Deploy!

---

## 📋 Checklist Pré-Deploy

- [ ] Commit e push de todas as alterações
- [ ] Verificar `requirements.txt` atualizado
- [ ] Configurar variáveis de ambiente
- [ ] Testar localmente com `gunicorn run:app`
- [ ] Verificar conexão com Supabase
- [ ] Configurar domínio personalizado (opcional)
- [ ] Configurar SSL (automático na maioria)

---

## 🔧 Variáveis de Ambiente Necessárias

```env
# Banco de Dados (Supabase)
DATABASE_URL=postgresql://postgres.[projeto]:[senha]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

# Flask
SECRET_KEY=gere-uma-chave-segura-aqui
FLASK_ENV=production

# Mercado Pago (Pagamentos)
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-xxx
MERCADO_PAGO_PUBLIC_KEY=APP_USR-xxx

# Admin inicial
ADMIN_EMAIL=admin@seudominio.com
ADMIN_PASSWORD=senha-segura-123
```

### Gerar SECRET_KEY:
```python
import secrets
print(secrets.token_hex(32))
```

---

## 📧 Configuração de Email - SendGrid

### 1. Criar Conta no SendGrid

1. Acesse [sendgrid.com](https://sendgrid.com) e crie conta gratuita
2. Verifique seu email
3. Vá para **Settings** → **API Keys** → **Create API Key**
4. Dê um nome (ex: "Petitio Production") e selecione **Full Access**
5. **COPIE E SALVE** a API Key gerada (não poderá ver novamente!)

### 2. Configurar Domínio (Importante!)

1. Vá para **Settings** → **Sender Authentication**
2. Clique em **Authenticate Your Domain**
3. Adicione seu domínio (ex: `seudominio.com`)
4. Siga as instruções para configurar os registros DNS
5. Aguarde verificação (pode levar até 48h)

### 3. Variáveis de Ambiente para SendGrid

```env
# SendGrid SMTP Configuration
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.SEU_SENDGRID_API_KEY_AQUI
MAIL_DEFAULT_SENDER=noreply@seudominio.com
```

### 4. Teste Local

Antes de fazer deploy, teste localmente:

```bash
# 1. Instale as dependências
pip install Flask-Mail

# 2. Configure .env com as variáveis acima

# 3. Teste o envio
python -c "
from app.utils.email import send_email
send_email('seu-email@teste.com', 'Teste', 'emails/deadline_alert.html', deadline={'title': 'Teste', 'user': {'name': 'Teste'}, 'due_date': '2025-01-01', 'days_until': 5})
print('Email enviado!')
"
```

### 5. Limites do Plano Gratuito
- **100 emails/dia**
- Para produção, considere upgrade para plano pago ($19.95/mês = 40.000 emails)

---

## 🌐 Configurar Domínio Personalizado

1. Compre um domínio (Registro.br, GoDaddy, Cloudflare)

2. Configure DNS:
   ```
   Tipo: CNAME
   Nome: @ ou www
   Valor: seu-app.railway.app (ou equivalente)
   ```

3. Na plataforma de hospedagem, adicione o domínio personalizado

4. Aguarde propagação DNS (até 48h, geralmente minutos)

---

## 📊 Comparativo de Preços

| Plataforma | Plano Gratuito | Plano Pago | Servidor Brasil |
|------------|----------------|------------|-----------------|
| Railway    | $5 créditos/mês | ~$5-20/mês | ❌ |
| Render     | Sim (hiberna) | $7/mês | ❌ |
| Fly.io     | Sim (limitado) | ~$5/mês | ✅ São Paulo |
| DigitalOcean | ❌ | $5/mês | ❌ |

---

## 🆘 Troubleshooting

### Erro de build
```bash
# Verifique se requirements.txt está correto
pip freeze > requirements.txt
```

### Erro de conexão com banco
- Verifique se DATABASE_URL está correto
- Confirme que IP do servidor está liberado no Supabase

### App não inicia
- Verifique logs na plataforma
- Teste localmente: `gunicorn run:app --bind 0.0.0.0:5000`

### Timeout
- Aumente timeout no gunicorn: `--timeout 300`
