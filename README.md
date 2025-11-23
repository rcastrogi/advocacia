# Petitio - Sistema de Gestão para Advogados

Sistema completo de gestão de clientes e processos para escritórios de advocacia.

## 🚀 Tecnologias

- Flask 2.3.3
- SQLAlchemy
- Bootstrap 5
- PostgreSQL (produção) / SQLite (desenvolvimento)
- ViaCEP API

## 🏃 Executar Localmente

```bash
cd advocacia_saas
pip install -r requirements.txt
python run.py
```

Acesse: http://localhost:5000

## 🔐 Credenciais Padrão

- Email: admin@petitio.com
- Senha: admin123

⚠️ Altere após o primeiro login!

## 📦 Deploy

O projeto está configurado para deploy no Render.com via arquivo `render.yaml` na raiz do repositório.

## 🔧 Inicialização do Admin (deploy)

O repositório inclui um script de inicialização do usuário administrador: `init_admin.py`.
Durante o build (`build.sh`) o script é chamado para garantir que exista um admin inicial.

- Variáveis de ambiente úteis:
	- `ADMIN_EMAIL` — Email do administrador (padrão: `admin@advocaciasaas.com`).
	- `ADMIN_PASSWORD` — Senha do administrador (opcional). Se omitida, uma senha forte será gerada.
	- `ADMIN_FORCE` — Se `true`/`1`/`yes`, o build passará `--force` ao script e tentará recriar o admin.

Consulte `docs/INIT_ADMIN.md` para instruções completas e recomendações de segurança.

## ✨ Features

- ✅ Gestão de clientes completa
- ✅ Sistema de dependentes
- ✅ Busca automática de CEP
- ✅ Estados e cidades do Brasil
- ✅ Dashboard com estatísticas
- ✅ Design profissional responsivo
- ✅ Bloqueio de campos preenchidos por API

---

**Desenvolvido com ❤️ para advogados brasileiros**
