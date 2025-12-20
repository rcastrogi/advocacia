# Configuração do Stripe para Checkout de Créditos IA

Este guia explica como configurar o Stripe para aceitar pagamentos de créditos de IA no Petitio.

## 📋 Pré-requisitos

1. Conta no Stripe (https://stripe.com)
2. Chaves de API do Stripe (test e production)

## 🔑 Configuração das Chaves

### 1. Obter as Chaves no Stripe Dashboard

1. Acesse: https://dashboard.stripe.com/test/apikeys
2. Copie as chaves:
   - **Publishable key** (começa com `pk_test_` ou `pk_live_`)
   - **Secret key** (começa com `sk_test_` ou `sk_live_`)

### 2. Configurar no .env

Adicione as chaves no arquivo `.env`:

```env
STRIPE_SECRET_KEY=sk_test_sua_chave_secreta_aqui
STRIPE_PUBLISHABLE_KEY=pk_test_sua_chave_publica_aqui
STRIPE_WEBHOOK_SECRET=whsec_seu_webhook_secret_aqui
```

## 🎯 Configurar Webhooks

Os webhooks permitem que o Stripe notifique sua aplicação sobre eventos de pagamento.

### 1. Criar Webhook no Stripe

1. Acesse: https://dashboard.stripe.com/test/webhooks
2. Clique em "Add endpoint"
3. Configure:
   - **Endpoint URL**: `https://seu-dominio.com/stripe/webhook`
   - **Events to send**:
     - `checkout.session.completed`
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`

### 2. Copiar Webhook Secret

Após criar o webhook, copie o **Signing secret** (começa com `whsec_`) e adicione no `.env`:

```env
STRIPE_WEBHOOK_SECRET=whsec_seu_webhook_secret_aqui
```

## 📦 Popular Pacotes de Créditos

Execute o script para criar os pacotes iniciais no banco de dados:

```bash
python scripts/populate_credit_packages.py
```

Isso criará 4 pacotes:
- **Starter**: 50 créditos por R$ 49,90
- **Professional**: 150 + 20 bônus por R$ 129,90
- **Business**: 300 + 50 bônus por R$ 239,90
- **Enterprise**: 500 + 100 bônus por R$ 379,90

## 🧪 Testar Localmente

### 1. Instalar Stripe CLI

```bash
# Windows (com Scoop)
scoop install stripe

# macOS
brew install stripe/stripe-cli/stripe

# Linux
wget https://github.com/stripe/stripe-cli/releases/download/v1.19.0/stripe_1.19.0_linux_x86_64.tar.gz
tar -xvf stripe_1.19.0_linux_x86_64.tar.gz
```

### 2. Fazer Login no Stripe CLI

```bash
stripe login
```

### 3. Encaminhar Webhooks para Localhost

```bash
stripe listen --forward-to localhost:5000/stripe/webhook
```

O CLI exibirá um webhook secret temporário. Use-o no `.env` para testes locais.

### 4. Testar Pagamento

Use os cartões de teste do Stripe:

#### Cartão de Sucesso
- **Número**: 4242 4242 4242 4242
- **Validade**: Qualquer data futura (ex: 12/25)
- **CVC**: Qualquer 3 dígitos (ex: 123)
- **CEP**: Qualquer CEP válido

#### Cartão que Requer Autenticação
- **Número**: 4000 0025 0000 3155

#### Cartão Recusado
- **Número**: 4000 0000 0000 0002

## 🚀 Fluxo de Pagamento

1. **Usuário escolhe pacote**: `/ai/credits/buy/professional`
2. **Clica em "Pagar"**: JavaScript chama `/stripe/create-checkout-session`
3. **Backend cria sessão**: Stripe retorna URL de checkout
4. **Redirecionamento**: Usuário é levado ao checkout do Stripe
5. **Pagamento**: Usuário preenche dados do cartão
6. **Sucesso**: Redireciona para `/stripe/checkout/success`
7. **Créditos adicionados**: Sistema adiciona créditos automaticamente

## 📊 Endpoints Criados

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/stripe/create-checkout-session` | Cria sessão de checkout |
| GET | `/stripe/checkout/success` | Página de sucesso |
| GET | `/stripe/checkout/cancel` | Página de cancelamento |
| POST | `/stripe/webhook` | Recebe notificações do Stripe |

## 🔍 Verificar Pagamentos

### No Dashboard do Stripe
1. Acesse: https://dashboard.stripe.com/test/payments
2. Veja todas as transações e status

### No Banco de Dados
```sql
-- Ver transações de créditos
SELECT * FROM credit_transactions 
WHERE user_id = 1 
ORDER BY created_at DESC;

-- Ver saldo de usuário
SELECT * FROM user_credits 
WHERE user_id = 1;
```

## ⚠️ Troubleshooting

### Erro: "Stripe not configured"
- Verifique se `STRIPE_SECRET_KEY` está no `.env`
- Reinicie a aplicação Flask

### Webhook não está funcionando
- Verifique se `STRIPE_WEBHOOK_SECRET` está configurado
- Use `stripe listen` para testes locais
- Verifique logs do webhook no Stripe Dashboard

### Créditos não foram adicionados
- Verifique se o webhook `checkout.session.completed` foi recebido
- Veja logs da aplicação
- Verifique tabela `credit_transactions`

## 🔐 Segurança em Produção

1. **Use chaves de produção**:
   ```env
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_PUBLISHABLE_KEY=pk_live_...
   ```

2. **Configure HTTPS**:
   - Stripe requer HTTPS em produção
   - Use certificado SSL válido

3. **Valide Webhooks**:
   - O sistema valida assinatura do webhook automaticamente
   - Nunca desabilite a validação em produção

4. **Monitore Transações**:
   - Configure alertas no Stripe Dashboard
   - Monitore logs de erro

## 📚 Recursos Adicionais

- [Documentação Stripe Checkout](https://stripe.com/docs/payments/checkout)
- [Testar Webhooks](https://stripe.com/docs/webhooks/test)
- [Cartões de Teste](https://stripe.com/docs/testing)
- [Stripe CLI](https://stripe.com/docs/stripe-cli)

## 💡 Dicas

1. **Sempre teste com cartões de teste** antes de ir para produção
2. **Use o Stripe CLI** para simular webhooks localmente
3. **Monitore o Dashboard** do Stripe regularmente
4. **Configure emails** de recibo no Stripe Dashboard
5. **Mantenha logs** de todas as transações para auditoria
