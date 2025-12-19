# Inicialização do usuário admin

Este documento descreve como usar o script `init_admin.py` e como o `build.sh` o integra durante o deploy.

Resumo
- Arquivo principal: `init_admin.py`
- Chamado pelo `build.sh` durante o build/deploy
- Gera logs em `build_logs/` quando executado pelo `build.sh`

Variáveis de ambiente usadas pelo `build.sh`
- `ADMIN_EMAIL` — Email do administrador a ser criado (padrão: `admin@advocaciasaas.com`).
- `ADMIN_PASSWORD` — Senha para o admin (opcional). Se omitida, o `init_admin.py` gera uma senha forte.
- `ADMIN_FORCE` — Quando definido para `1`, `true` ou `yes` (case-insensitive), o `build.sh` passa `--force` para `init_admin.py` e força a recriação/atualização do admin. Caso contrário, o script só criará o admin se ele não existir.

Como funciona `init_admin.py`
- `init_admin.py --email <email> [--password <pw>] [--force]`
- Sem `--force`: se o admin já existir, nenhuma alteração é feita.
- Com `--force`: o script tenta deletar o usuário existente e criar um novo; se a remoção falhar por restrições de FK, ele faz rollback e atualiza a senha do usuário existente.
- Se `--password` for omitido, uma senha forte será gerada e impressa no stdout (e nos logs quando executado pelo `build.sh`).

Uso local (desenvolvimento)
1. Ative seu virtualenv e posicione-se na pasta do projeto.
2. Para recriar o admin (force) com senha gerada:
```cmd
python init_admin.py --force
```
3. Para criar o admin com senha específica (sem forçar remoção):
```cmd
python init_admin.py --email "admin@advocaciasaas.com" --password "MinhaSenhaSegura123"
```

Uso em Render (ou pipeline CI)
- Defina variáveis de ambiente no painel do provedor quando necessário:
  - `ADMIN_EMAIL` — (opcional)
  - `ADMIN_PASSWORD` — **recomendado** se não quiser que a senha seja gerada e exibida nos logs
  - `ADMIN_FORCE` — defina para `true` apenas se você quiser recriar o admin no deploy
- O `build.sh` chama `init_admin.py` e grava a saída em `build_logs/init_admin-YYYYMMDD-HHMMSS.log`.

Exemplos de configuração no Render
- Sem sobrescrever admin existente (recomendado):
  - Não defina `ADMIN_FORCE` (ou defina `ADMIN_FORCE=false`).
  - O build criará o admin apenas se não existir.
- Forçar recriação no deploy:
  - Defina `ADMIN_FORCE=true` (ou `1`) e, opcionalmente, `ADMIN_PASSWORD`.

Segurança e recomendações
- Evite imprimir senhas em logs em produção. Se possível, defina `ADMIN_PASSWORD` como secret/env var no provedor.
- Use `ADMIN_FORCE=true` com cautela — pode sobrescrever um admin legítimo.
- Se quiser mais segurança, posso adaptar o script para:
  - Gravar a senha gerada em um arquivo com permissões restritas (e não imprimir em logs), ou
  - Enviar a senha gerada para um secret manager do provedor (ex.: Render Secrets, AWS Secrets Manager).

Onde os logs ficam
- `build.sh` cria logs em `build_logs/` no diretório do projeto. Procure `build_logs/init_admin-YYYYMMDD-HHMMSS.log` após o deploy.

Perguntas frequentes
- Posso remover `--force` do `build.sh`?
  - Sim — atualmente `build.sh` só passa `--force` quando a variável `ADMIN_FORCE` está definida para `true`.
- A senha gerada é persistida em algum lugar?
  - Não por padrão; ela é apenas impressa no stdout (e capturada no log). Posso alterar o comportamento para salvar em arquivo seguro ou enviar a um secret manager.

Se quiser que eu adicione instruções ao `README.md` do projeto, diga e eu adiciono uma seção resumida com estes passos.

***
Arquivo gerado automaticamente. Mantenha este documento no repositório para referência de deploy.
