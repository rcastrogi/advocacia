# 🚀 Guia Completo de Deploy - Petitio

## ✅ Pré-requisitos

### 1. Instalar Git (se ainda não tiver)

**Download:** https://git-scm.com/download/win

Após instalar, reinicie o VS Code e o terminal.

### 2. Criar conta no GitHub

**Link:** https://github.com/signup

### 3. Criar conta no Render

**Link:** https://render.com/register

---

## 📦 Passo 1: Preparar o Projeto para Git

Abra o terminal do VS Code (Ctrl + `) e execute:

```bash
# Navegar para a pasta do projeto
cd F:\PROJETOS\advocacia\advocacia_saas

# Inicializar repositório Git
git init

# Configurar nome e email (substitua pelos seus dados)
git config user.name "Seu Nome"
git config user.email "seu.email@example.com"

# Adicionar todos os arquivos
git add .

# Fazer o primeiro commit
git commit -m "Initial commit - Petitio v1.0"
```

---

## 🌐 Passo 2: Enviar para o GitHub

### 2.1. Criar repositório no GitHub

1. Acesse https://github.com/new
2. Nome do repositório: `petitio`
3. Descrição: `Sistema de Gestão para Advogados`
4. **Deixe DESMARCADO** "Initialize this repository with a README"
5. Clique em **"Create repository"**

### 2.2. Conectar repositório local ao GitHub

O GitHub vai mostrar comandos. Use estes no terminal:

```bash
# Adicionar o repositório remoto (substitua SEU_USUARIO pelo seu nome de usuário do GitHub)
git remote add origin https://github.com/SEU_USUARIO/petitio.git

# Renomear branch para main
git branch -M main

# Enviar para o GitHub
git push -u origin main
```

💡 **Se pedir autenticação:** Use seu nome de usuário e **Personal Access Token** (não senha).

Para criar um token: https://github.com/settings/tokens
- Marque: `repo` (Full control of private repositories)
- Copie o token e use como senha

---

## 🎯 Passo 3: Deploy no Render

### 3.1. Conectar GitHub ao Render

1. Acesse https://dashboard.render.com
2. Clique em **"New +"** → **"Blueprint"**
3. Clique em **"Connect GitHub"**
4. Autorize o Render a acessar seus repositórios
5. Selecione o repositório **"petitio"**

### 3.2. Configurar o Deploy

O Render vai detectar automaticamente o arquivo `render.yaml` e vai criar:

- ✅ **Web Service** - Aplicação Flask
- ✅ **PostgreSQL Database** - Banco de dados

Clique em **"Apply"** para iniciar o deploy.

### 3.3. Aguardar o Deploy

- ⏱️ Primeira vez: 5-10 minutos
- 📦 O Render vai instalar todas as dependências
- 🗄️ Criar o banco de dados PostgreSQL
- 👤 Criar usuário admin automaticamente
- 📍 Popular estados e cidades do Brasil

### 3.4. Acessar a Aplicação

Após o deploy, sua aplicação estará disponível em:

```
https://petitio.onrender.com
```

ou similar (o Render vai te dar a URL exata)

---

## 🔐 Credenciais de Acesso

**Login padrão:**
- Email: `admin@petitio.com`
- Senha: `admin123`

⚠️ **IMPORTANTE:** Altere estas credenciais imediatamente após o primeiro acesso!

---

## 🔄 Como Fazer Atualizações

Sempre que você fizer alterações no código:

```bash
# 1. Adicionar arquivos modificados
git add .

# 2. Fazer commit com descrição
git commit -m "Descrição das alterações"

# 3. Enviar para o GitHub
git push

# 4. O Render faz deploy automático! 🎉
```

O Render detecta o push e faz o deploy automaticamente em 2-5 minutos.

---

## 🐛 Troubleshooting

### Erro: "Git não encontrado"
- Instale o Git: https://git-scm.com/download/win
- Reinicie o VS Code
- Tente novamente

### Erro: "Authentication failed"
- Use Personal Access Token ao invés de senha
- Gere em: https://github.com/settings/tokens

### Erro no deploy do Render
- Veja os logs no painel do Render
- Verifique se o `render.yaml` está correto
- Confirme que o `requirements.txt` está completo

### Database não conecta
- Verifique se o PostgreSQL foi criado
- Confirme que a variável `DATABASE_URL` está configurada
- Aguarde o banco terminar de inicializar (pode levar 2-3 minutos)

---

## 📊 Monitoramento

No painel do Render você pode ver:

- ✅ Status do deploy
- 📈 Uso de recursos
- 📝 Logs em tempo real
- 🔧 Variáveis de ambiente
- 💾 Status do banco de dados

---

## 💰 Custos

**Render Free Tier:**
- ✅ 750 horas/mês de web service (suficiente para 1 app)
- ✅ 90 dias de banco PostgreSQL grátis
- ⚠️ Após 15 minutos de inatividade, o app "hiberna" (demora ~30s para acordar)
- 💡 Para evitar hibernação: upgrade para plano pago ($7/mês)

---

## 📞 Links Úteis

- **Render Dashboard:** https://dashboard.render.com
- **Render Docs:** https://render.com/docs
- **GitHub:** https://github.com
- **Git Docs:** https://git-scm.com/doc

---

## ✅ Checklist Final

Antes de compartilhar com o cliente:

- [ ] Git instalado
- [ ] Repositório criado no GitHub
- [ ] Código enviado para o GitHub
- [ ] Deploy feito no Render
- [ ] Aplicação acessível pela URL
- [ ] Login funcionando
- [ ] Estados e cidades populados
- [ ] CEP funcionando
- [ ] Bloqueio de campos funcionando

---

**🎉 Parabéns! Sua aplicação está no ar!**

Compartilhe a URL com seu cliente e mostre o sistema funcionando.

---

*Dúvidas? Verifique os logs no Render Dashboard → Services → petitio → Logs*
