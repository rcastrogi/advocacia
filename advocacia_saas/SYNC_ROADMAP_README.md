# 📊 Sistema de Sincronização do Roadmap

Sistema automático para comparar, evoluir e sincronizar o roadmap entre Render (produção) e local, mostrando evolução real aos clientes.

## 🎯 O Que Faz

✅ **Sincroniza dados** do Render (via DATABASE_URL do .env)
✅ **Compara com histórico anterior** (snapshots)
✅ **Mostra itens que evoluíram** (mudanças de status)
✅ **Atualiza automaticamente** status baseado em datas planejadas
✅ **Gera relatórios** para clientes verem progresso
✅ **Cria histórico** de todas as sincronizações

## 📋 Scripts

### 1. **sync_roadmap.py** - Sincroniza e Compara
Compara estado anterior com estado atual, mostra evolução.

```bash
python sync_roadmap.py
```

**O que faz:**
- 📂 Carrega último snapshot
- 📥 Exporta dados atuais
- 📊 Compara ambos
- 📈 Mostra itens que mudaram
- 📍 Cria novo snapshot em `roadmap_snapshots/`

**Saída:**
- ANÁLISE DE EVOLUÇÃO: mudanças de status
- RELATÓRIO PARA CLIENTES: progresso visual
- Snapshots salvos para próxima comparação

---

### 2. **update_roadmap.py** - Evolui Itens Automaticamente
Atualiza status dos itens com base em datas planejadas.

```bash
python update_roadmap.py
```

**O que faz:**
- ✅ planned → in_progress (quando passa data planejada)
- ✅ in_progress → completed (quando passa data de conclusão)
- 📝 Registra datas reais
- 💾 Salva no banco

**Use antes de sync_roadmap.py** para evoluir itens primeiro.

---

### 3. **demo_roadmap.py** - Prepara Dados de Demo
Configura datas de teste para demonstração.

```bash
python demo_roadmap.py
```

**O que faz:**
- Divide itens em 3 cenários:
  - 1/3: planned → in_progress (hoje)
  - 1/3: in_progress → completed (hoje)
  - 1/3: planned para futuro
- Útil para **testar fluxo de evolução**

---

## 🚀 Fluxo Completo

### Primeira Execução

```bash
# 1. Gerar primeiro snapshot
python sync_roadmap.py

# Resultado: Sem comparação (primeiro snapshot)
```

### Demo/Teste

```bash
# 1. Preparar dados
python demo_roadmap.py

# 2. Evoluir itens
python update_roadmap.py

# 3. Ver mudanças
python sync_roadmap.py

# Resultado: Mostra ANÁLISE DE EVOLUÇÃO com todas as mudanças
```

### Produção (Automático)

```bash
# Executar diariamente (via cron/task scheduler)
python update_roadmap.py && python sync_roadmap.py
```

---

## 📊 Exemplo de Saída

### ANÁLISE DE EVOLUÇÃO
```
Data anterior: 2026-01-03T00:08:12
Data atual:    2026-01-03T00:09:45

Total de itens: 39

STATUS ANTERIOR:
  ✅ Concluído: 26 (66.7%)
  📋 Planejado: 13 (33.3%)

STATUS ATUAL:
  ✅ Concluído: 13 (33.3%)
  🔄 Em Andamento: 13 (33.3%)
  📋 Planejado: 13 (33.3%)

Progresso anterior: 66.67%
Progresso atual: 33.33%
⚠️ Redução: -33.34%

ITENS QUE EVOLUÍRAM:
  📌 Dashboard de Analytics Avançado
     Status: Concluído → Em Andamento
  
  ✅ Integração com Google Drive
     Concluído em: 2026-01-03
```

### RELATÓRIO PARA CLIENTES
```
Evolução do Roadmap da Petitio

Progresso Geral: ██████░░░░░░░░░░░░░░ 33.33%

Status Atual dos Itens:
  ✅ Concluído: 13 itens (33.3%)
  🔄 Em Andamento: 13 itens (33.3%)
  📋 Planejado: 13 itens (33.3%)

Por Categoria:
  • Funcionalidades: 20 itens
  • Segurança: 6 itens
  • Integração: 5 itens
  • Performance: 3 itens
  • ...
```

---

## 📁 Arquivos Gerados

```
roadmap_snapshots/
  ├─ snapshot_20260102_210802.json
  ├─ snapshot_20260102_210812.json
  ├─ snapshot_20260102_210945.json
  └─ ...
```

Cada snapshot contém:
- Timestamp
- Ambiente (local/render)
- Total de itens
- Status de todos os itens
- Estatísticas

---

## ⏰ Agendamento Automático

### Linux/Mac (crontab)

```bash
# Executar diariamente às 8 da manhã
0 8 * * * cd /path/to/advocacia_saas && python update_roadmap.py && python sync_roadmap.py >> logs/roadmap.log 2>&1
```

### Windows (Task Scheduler)

1. Crie tarefa com:
   - Trigger: Diário às 08:00
   - Action: `python update_roadmap.py && python sync_roadmap.py`
   - Working Directory: `C:\path\to\advocacia_saas`

### Render (render.yaml)

```yaml
services:
  - type: cron
    name: roadmap-sync
    runtime: python-3.13
    buildCommand: pip install -r requirements.txt
    startCommand: python update_roadmap.py && python sync_roadmap.py
    schedule: "0 8 * * *"
```

---

## 🌐 Visualizar para Clientes

Clientes veem a evolução em:
```
http://localhost:5000/roadmap
https://petitio.onrender.com/roadmap
```

Status é atualizado automaticamente após cada sync.

---

## 🔍 Checando Status

```bash
# Ver último snapshot
ls -la roadmap_snapshots/

# Ver logs de evolução
python update_roadmap.py

# Ver comparação
python sync_roadmap.py

# Ver dados em JSON
cat roadmap_snapshots/snapshot_LATEST.json | python -m json.tool
```

---

## 💡 Tips

### Resetar para Estado Anterior
```bash
# Remover últimos snapshots e voltar ao anterior
rm roadmap_snapshots/snapshot_*.json

# Reexecutar sync
python sync_roadmap.py
```

### Testar Manualmente
```bash
# 1. Preparar demo
python demo_roadmap.py

# 2. Evoluir
python update_roadmap.py

# 3. Ver resultado
python sync_roadmap.py

# 4. Repetir conforme necessário
```

### Ver Dados Brutos
```bash
# Exportar último snapshot para análise
cat roadmap_snapshots/snapshot_*.json | tail -1 | python -m json.tool
```

---

## 🐛 Troubleshooting

**"Nenhum item para evoluir"**
→ Executar `demo_roadmap.py` primeiro para configurar datas

**"Banco não conecta"**
→ Verificar: `echo $DATABASE_URL` (deve estar no .env)

**Snapshots não criados**
→ Verificar pasta `roadmap_snapshots/` tem permissão de escrita

---

## 📞 Fluxo Recomendado

```
DESENVOLVIMENTO:
  python demo_roadmap.py           (preparar dados)
  python update_roadmap.py         (evoluir)
  python sync_roadmap.py           (comparar)
  
PRODUÇÃO:
  0 8 * * * (rodar ambos diariamente)
  
MONITORAMENTO:
  Verificar snapshots em roadmap_snapshots/
  Clientes veem em /roadmap
```

---

**Criado:** 2026-01-02
**Status:** ✅ Pronto para Render
**Progresso:** Sincronização completa
