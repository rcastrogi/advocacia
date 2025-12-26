# Petitio

Sistema completo de gestão para escritórios de advocacia desenvolvido em Python Flask.

## Características

- **Gestão de Clientes**: Cadastro completo com dados pessoais, endereço, contatos e dependentes
- **Autenticação**: Sistema de login com três tipos de usuário (Administrador, Advogado e Escritório)
- **Dashboard**: Painel com estatísticas e informações importantes
- **Peticionador**: Módulo para geração de petições e procurações (em desenvolvimento)
- **API CEP**: Integração com ViaCEP para preenchimento automático de endereços
- **Upload de Logo**: Logo personalizado para cada usuário
- **Interface Responsiva**: Design moderno com Bootstrap 5
- **Notificações por Email**: Alertas automáticos de prazos próximos (SendGrid)

## Requisitos

- Python 3.8+
- SQLite (padrão) ou MySQL (configurável)

## Instalação

1. **Clone ou baixe o projeto**
```bash
cd F:\PROJETOS\advocacia\advocacia_saas
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Configure as variáveis de ambiente**
Edite o arquivo `.env` conforme necessário:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
FLASK_ENV=development
```

4. **Inicialize o banco de dados**
```bash
python init_db.py
```

5. **Execute a aplicação**
```bash
python run.py
```

A aplicação estará disponível em: `http://localhost:5000`

## Usuário Padrão

Após a inicialização do banco de dados, um usuário administrador será criado:

- **Email**: admin@advocaciasaas.com
- **Senha**: admin123
- **Tipo**: Administrador

⚠️ **IMPORTANTE**: Altere a senha padrão após o primeiro login!

## Estrutura do Projeto

```
advocacia_saas/
├── app/
│   ├── __init__.py          # Configuração da aplicação Flask
│   ├── models.py            # Modelos do banco de dados
│   ├── auth/                # Módulo de autenticação
│   │   ├── __init__.py
│   │   ├── forms.py         # Formulários de login/cadastro
│   │   └── routes.py        # Rotas de autenticação
│   ├── main/                # Módulo principal
│   │   ├── __init__.py
│   │   └── routes.py        # Dashboard e páginas principais
│   ├── clients/             # Módulo de clientes
│   │   ├── __init__.py
│   │   ├── forms.py         # Formulário de cadastro de clientes
│   │   └── routes.py        # CRUD de clientes
│   ├── api/                 # API endpoints
│   │   ├── __init__.py
│   │   └── routes.py        # API para CEP, etc.
│   ├── templates/           # Templates HTML
│   │   ├── base.html        # Template base
│   │   ├── index.html       # Landing page
│   │   ├── dashboard.html   # Dashboard
│   │   ├── auth/            # Templates de autenticação
│   │   └── clients/         # Templates de clientes
│   └── static/              # Arquivos estáticos
│       ├── css/
│       ├── js/
│       └── uploads/         # Logos dos usuários
├── config.py                # Configurações da aplicação
├── requirements.txt         # Dependências Python
├── run.py                   # Arquivo principal para executar
├── init_db.py              # Script de inicialização do DB
└── .env                     # Variáveis de ambiente
```

## Funcionalidades

### 1. Autenticação
- Login/cadastro de usuários
- Três tipos de usuário: Administrador, Advogado e Escritório
- Upload de logo personalizado
- Gestão de perfil

### 2. Gestão de Clientes
- Cadastro completo com:
  - Dados pessoais (nome, RG, CPF/CNPJ, etc.)
  - Endereço (com busca automática por CEP)
  - Contatos (telefone, email, celular)
  - Condições especiais (LGBT, PcD, gestante, etc.)
  - Dependentes ilimitados
- Listagem com paginação
- Busca e filtros
- Visualização detalhada
- Edição e exclusão

### 3. Dashboard
- Estatísticas gerais
- Clientes recentes
- Ações rápidas
- Informações da conta

### 4. API
- Endpoint para consulta de CEP
- Integração com ViaCEP
- Preenchimento automático de endereços

### 5. Sistema Peticionador (em desenvolvimento)
- Geração de petições automatizadas
- Templates personalizáveis
- Procurações integradas
- Assinatura digital

## Campos do Cadastro de Cliente

### Dados Pessoais
- Nome Completo *
- RG
- CPF ou CNPJ *
- Estado Civil
- Data de Nascimento
- Profissão
- Nacionalidade
- Naturalidade
- Nome da Mãe
- Nome do Pai

### Endereço
- Tipo (Residencial/Comercial)
- CEP (com busca automática)
- Logradouro
- Número (editável)
- Complemento
- Bairro
- Cidade
- UF

### Contatos
- Telefone Fixo
- E-mail * (obrigatório)
- Celular * (obrigatório)

### Condições Pessoais
- Autodeclarado LGBT?
- Pessoa com deficiência?
  - Tipos: Auditiva, Física, Intelectual, Mental, Visual
- Gestante/Puérpera/Lactante?
  - Data do parto (com calendário)

### Dependentes
- Nome completo
- Parentesco
- Data de nascimento
- CPF

## Tecnologias Utilizadas

### Backend
- **Flask** - Framework web Python
- **SQLAlchemy** - ORM para banco de dados
- **Flask-Login** - Gerenciamento de sessões
- **WTForms** - Formulários e validação
- **Flask-Migrate** - Migrações de banco de dados

### Frontend
- **Bootstrap 5** - Framework CSS
- **Font Awesome** - Ícones
- **jQuery** - Manipulação DOM e AJAX

### Banco de Dados
- **SQLite** (padrão para desenvolvimento)
- **MySQL** (configurável para produção)

## Configuração para Produção

1. **Altere as configurações no arquivo .env**:
```
SECRET_KEY=your-production-secret-key
DATABASE_URL=mysql://user:password@host:port/database
FLASK_ENV=production
```

2. **Configure um servidor web** (nginx + gunicorn recomendado)

3. **Configure backup automático** do banco de dados

4. **Implemente HTTPS** para segurança

## Próximas Funcionalidades

- [ ] Geração de petições e procurações em PDF
- [ ] Sistema de templates personalizáveis
- [ ] Relatórios avançados
- [ ] Integração com assinatura digital
- [ ] Sistema de notificações
- [ ] API completa REST
- [ ] Aplicativo móvel
- [ ] Integração com sistemas tribunais

## Suporte

Para dúvidas, sugestões ou problemas, entre em contato através do email: suporte@advocaciasaas.com

## Licença

Este projeto é proprietário. Todos os direitos reservados.

---

**Petitio** - Modernizando a advocacia, um escritório por vez.
