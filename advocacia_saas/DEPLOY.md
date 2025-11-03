# Petitio - Sistema de Gestão para Advogados

Sistema completo de gestão de clientes e processos para escritórios de advocacia.

## 🚀 Deploy no Render.com

### Passo 1: Preparar o Repositório Git

```bash
# Inicialize o Git (se ainda não tiver)
git init

# Adicione todos os arquivos
git add .

# Commit inicial
git commit -m "Preparando para deploy no Render"

# Crie um repositório no GitHub e conecte
git remote add origin https://github.com/SEU_USUARIO/petitio.git
git branch -M main
git push -u origin main
```

### Passo 2: Deploy no Render

1. Acesse https://render.com e faça login (ou crie conta gratuita)

2. Clique em **"New +"** → **"Blueprint"**

3. Conecte seu repositório GitHub

4. O Render vai detectar automaticamente o arquivo `render.yaml`

5. Clique em **"Apply"** para criar:
   - ✅ Web Service (aplicação Flask)
   - ✅ PostgreSQL Database (banco de dados)

6. Aguarde o deploy (5-10 minutos na primeira vez)

7. Sua aplicação estará disponível em: `https://petitio.onrender.com`

### Passo 3: Configurar Variáveis de Ambiente (Opcional)

No painel do Render, você pode adicionar mais variáveis:

- `SECRET_KEY` - Já gerada automaticamente
- `FLASK_ENV` - Já definida como "production"
- `DATABASE_URL` - Já conectada automaticamente

### 🔄 Atualizações Futuras

Para atualizar a aplicação em produção:

```bash
git add .
git commit -m "Descrição das alterações"
git push
```

O Render fará deploy automaticamente a cada push! 🎉

## 💻 Desenvolvimento Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Copiar arquivo de exemplo
copy .env.example .env

# Executar aplicação
python run.py
```

Acesse: http://localhost:5000

## 📝 Credenciais Padrão

**Usuário Master (criado automaticamente):**
- Email: admin@petitio.com
- Senha: admin123

⚠️ **IMPORTANTE:** Altere estas credenciais após o primeiro login!

## 🛠️ Tecnologias

- Flask 2.3.3
- SQLAlchemy (SQLite local / PostgreSQL produção)
- Bootstrap 5
- Font Awesome 6
- ViaCEP API

## 📊 Banco de Dados

### Desenvolvimento
- SQLite (app.db)

### Produção
- PostgreSQL (gerenciado pelo Render)

Para popular estados e cidades:
```bash
python populate_locations.py
```

## 🎨 Features

- ✅ Sistema de autenticação completo
- ✅ Gestão de clientes com dados completos
- ✅ Sistema de dependentes
- ✅ Busca automática de CEP
- ✅ Estados e cidades do Brasil
- ✅ Dashboard com estatísticas
- ✅ Design profissional responsivo
- ✅ Bloqueio de campos preenchidos por API

## 📞 Suporte

Para dúvidas sobre o deploy, consulte:
- https://render.com/docs/deploy-flask
- https://render.com/docs/databases

---

**Desenvolvido com ❤️ para advogados brasileiros**
