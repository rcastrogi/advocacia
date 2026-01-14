# 🔌 Serviços Externos - Petitio

> Documentação de todas as integrações externas do sistema.
> **Atualizado em**: 14/01/2026

---

## 📧 Email - Resend

### Descrição
Serviço de email transacional para envio de:
- Códigos 2FA (autenticação em dois fatores)
- Convites para escritório
- Alertas de prazos
- Notificações gerais

### Configuração
| Item | Valor |
|------|-------|
| **Serviço** | [Resend](https://resend.com) |
| **Plano** | Free (3.000 emails/mês, 100/dia) |
| **Biblioteca** | `resend==2.6.0` (requirements.txt) |
| **Variável** | `RESEND_API_KEY` |
| **Remetente** | `noreply@petitio.com.br` |

### Arquivos Relacionados
- `app/services/email_service.py` - Classe EmailService com métodos de envio
- `app/utils/email.py` - Funções auxiliares (send_office_invite_email)
- `app/templates/emails/` - Templates HTML dos emails

### Métodos Disponíveis (EmailService)
```python
EmailService.send_2fa_code_email(email, code)           # Código 2FA
EmailService.send_2fa_enabled_notification(email, name)  # 2FA ativado
EmailService.send_2fa_disabled_notification(email, name) # 2FA desativado
EmailService.send_office_invite(...)                     # Convite escritório
```

### Como Testar
```bash
# No Render logs, procure por:
"Email 2FA enviado com sucesso para xxx@xxx.com"
"Convite de escritório enviado para xxx@xxx.com"
```

---

## ⏰ Cron Job - cron-job.org

### Descrição
Agendador de tarefas para executar rotinas automáticas:
- Envio de alertas de prazos próximos (diário)

### Configuração
| Item | Valor |
|------|-------|
| **Serviço** | [cron-job.org](https://cron-job.org) |
| **Plano** | Free (ilimitado) |
| **Variável** | `CRON_API_KEY` |

### Jobs Configurados

#### 1. Alertas de Prazos
| Campo | Valor |
|-------|-------|
| **Nome** | Petitio - Alertas de Prazos |
| **URL** | `https://petitio.onrender.com/deadlines/api/send-alerts` |
| **Método** | POST |
| **Header** | `X-API-Key: [valor de CRON_API_KEY]` |
| **Horário** | Todo dia às 08:00 (horário de Brasília) |

### Endpoint Protegido
```python
# app/deadlines/routes.py
@bp.route("/api/send-alerts", methods=["POST"])
def api_send_alerts():
    # Requer header X-API-Key válido
```

### O que Faz
1. Busca prazos pendentes no banco
2. Verifica quais vencem nos próximos dias
3. Envia email de alerta para o advogado responsável
4. Cria notificação no sistema
5. Marca prazo como "alerta enviado"

---

## 💳 Pagamentos - Mercado Pago

### Descrição
Gateway de pagamento para assinaturas e cobranças.

### Configuração
| Item | Valor |
|------|-------|
| **Serviço** | [Mercado Pago](https://www.mercadopago.com.br/developers) |
| **Variáveis** | `MERCADOPAGO_ACCESS_TOKEN`, `MERCADOPAGO_PUBLIC_KEY`, `MERCADOPAGO_WEBHOOK_SECRET` |

### Arquivos Relacionados
- `app/payments/` - Blueprint de pagamentos
- `app/billing/` - Planos e assinaturas

---

## 🗄️ Banco de Dados - PostgreSQL (Render)

### Configuração
| Item | Valor |
|------|-------|
| **Serviço** | Render PostgreSQL |
| **Variável** | `DATABASE_URL` |
| **Pool Size** | 5 conexões |
| **Max Overflow** | 10 conexões |

---

## 🔴 Cache - Redis (Render)

### Descrição
Cache para rate limiting e dados temporários.

### Configuração
| Item | Valor |
|------|-------|
| **Serviço** | Render Redis |
| **Variável** | `REDIS_URL` |
| **DB 0** | Cache geral |
| **DB 1** | Rate limiting |
| **DB 2** | Sessões (futuro) |

---

## 🐛 Monitoramento - Sentry

### Descrição
Rastreamento de erros em produção.

### Configuração
| Item | Valor |
|------|-------|
| **Serviço** | [Sentry](https://sentry.io) |
| **Variável** | `SENTRY_DSN` |

---

## 📋 Resumo de Variáveis de Ambiente (Render)

```bash
# Obrigatórias
SECRET_KEY=xxx
DATABASE_URL=postgresql://...

# Email (Resend)
RESEND_API_KEY=re_xxxxxxxxxxxx

# Cron Job
CRON_API_KEY=mSveSIgeYVCkf_bAfRVqc-JCImc9iNUEz4fFKfkQp-Y

# Pagamentos (Mercado Pago)
MERCADOPAGO_ACCESS_TOKEN=xxx
MERCADOPAGO_PUBLIC_KEY=xxx
MERCADOPAGO_WEBHOOK_SECRET=xxx

# Cache (Redis)
REDIS_URL=redis://...

# Monitoramento (Sentry)
SENTRY_DSN=https://xxx@sentry.io/xxx

# Opcionais (Flask-Mail legado)
MAIL_SERVER=
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=noreply@advocaciasaas.com
```

---

## 🔄 Checklist de Deploy

Antes de fazer deploy, verifique:

- [ ] `RESEND_API_KEY` configurada no Render
- [ ] `CRON_API_KEY` configurada no Render
- [ ] Cron job criado no cron-job.org
- [ ] `MERCADOPAGO_ACCESS_TOKEN` configurada (se usar pagamentos)
- [ ] `SENTRY_DSN` configurada (se usar monitoramento)

---

## 📞 Suporte dos Serviços

| Serviço | Dashboard | Documentação |
|---------|-----------|--------------|
| Resend | https://resend.com/emails | https://resend.com/docs |
| cron-job.org | https://cron-job.org/en/members/ | https://docs.cron-job.org |
| Mercado Pago | https://www.mercadopago.com.br/developers/panel | https://www.mercadopago.com.br/developers/pt/docs |
| Render | https://dashboard.render.com | https://render.com/docs |
| Sentry | https://sentry.io | https://docs.sentry.io |
