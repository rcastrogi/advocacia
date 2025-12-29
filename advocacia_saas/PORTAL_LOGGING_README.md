# Sistema de Logging do Portal do Cliente

## Visão Geral

Foi implementado um sistema completo de logging para o Portal do Cliente com o objetivo de facilitar a identificação e resolução de problemas que possam ocorrer na tela de usuário.

## Arquivos Criados/Modificados

### 1. `app/portal/routes.py`
- Adicionado sistema de logging específico para o portal
- Logging detalhado em todas as rotas principais
- Captura de erros com traceback completo
- Logs de debug para operações importantes

### 2. `app/templates/portal/logs.html`
- Interface web para visualização dos logs
- Exibição colorida por tipo de log (erro, aviso, info, debug)
- Auto-refresh automático a cada 30 segundos

### 3. `monitor_portal_logs.py`
- Script para monitoramento em tempo real dos logs
- Visualização das últimas N linhas dos logs
- Cores diferenciadas para cada tipo de log

### 4. `test_portal_logging.py`
- Script de teste para validar o funcionamento do logging
- Exemplos de diferentes tipos de logs

## Como Usar

### 1. Visualização Web
Acesse: `http://seudominio.com/portal/logs`
- Requer login como cliente
- Mostra logs em tempo real com atualização automática

### 2. Monitoramento em Tempo Real
```bash
python monitor_portal_logs.py
```
- Monitora logs em tempo real
- Cores diferenciadas para cada tipo de log
- Ctrl+C para parar

### 3. Visualizar Últimas Linhas
```bash
python monitor_portal_logs.py --recent 50
```
- Mostra as últimas 50 linhas (ou número especificado)

### 4. Arquivo de Log
- Localização: `logs/portal.log`
- Formato: timestamp - logger - nível - função:linha - mensagem
- Codificação UTF-8

## Tipos de Logs Implementados

### INFO
- Acessos às páginas principais
- Operações bem-sucedidas (login, upload, envio de mensagens)
- Estatísticas de carregamento

### DEBUG
- Detalhes técnicos de operações
- IDs de clientes e objetos
- Tamanhos de arquivos e caminhos

### WARNING
- Tentativas de acesso inválido
- Dados ausentes ou inválidos
- Operações que podem indicar problemas

### ERROR
- Exceções não tratadas
- Falhas de banco de dados
- Erros de API
- Tracebacks completos

## Rotas com Logging

- `/` (Dashboard) - Estatísticas e carregamento
- `/login` - Tentativas de login e validações
- `/documents` - Listagem de documentos
- `/upload` - Processo completo de upload
- `/chat` - Acesso ao chat e mensagens
- `/api/chat/send` - API de envio de mensagens
- `/logs` - Acesso à visualização de logs

## Exemplo de Log

```
2025-12-29 09:15:31,756 - portal - INFO - index:45 - Usuário cliente@email.com acessando dashboard do portal
2025-12-29 09:15:31,757 - portal - DEBUG - index:47 - Cliente encontrado: 123 - João Silva
2025-12-29 09:15:31,758 - portal - INFO - index:62 - Dashboard carregado com sucesso para cliente@email.com: 5 docs, 2 prazos, 1 mensagens
2025-12-29 09:15:31,759 - portal - ERROR - upload:180 - Erro no upload para cliente@email.com: Permission denied
2025-12-29 09:15:31,760 - portal - ERROR - upload:181 - Traceback: PermissionError: [Errno 13] Permission denied: 'uploads/portal/123'
```

## Troubleshooting

### Logs não Aparecem
1. Verificar se o arquivo `logs/portal.log` existe
2. Verificar permissões de escrita na pasta `logs/`
3. Verificar se o logger foi inicializado corretamente

### Erro de Codificação
- O arquivo usa codificação UTF-8
- Problemas de encoding podem indicar configuração incorreta do sistema

### Logs Muito Grandes
- O arquivo cresce indefinidamente
- Considere implementar rotação de logs em produção
- Use `monitor_portal_logs.py --recent N` para ver apenas logs recentes

## Segurança

- A rota `/logs` está protegida pelo decorator `@client_required`
- Apenas usuários logados como clientes podem acessar
- Logs não contêm informações sensíveis (senhas, tokens)
- Em produção, considere restringir ainda mais o acesso

## Próximos Passos

1. Implementar rotação automática de logs
2. Adicionar filtros por data/usuário na interface web
3. Integrar com sistemas de monitoramento externos
4. Adicionar métricas de performance nos logs