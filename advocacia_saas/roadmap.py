#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atalho para rodar os scripts de roadmap com cores
"""
import sys
import os
import subprocess

if len(sys.argv) < 2:
    print("""
╔════════════════════════════════════════════════════════════════╗
║            ROADMAP SCRIPTS - CORES E BADGES                   ║
╚════════════════════════════════════════════════════════════════╝

Uso: python roadmap.py [comando]

Comandos:
  validate    - Atualizar roadmap com status real do projeto
  summary     - Ver resumo visual completo
  all         - Rodar ambos (validate + summary)

Exemplos:
  python roadmap.py validate
  python roadmap.py summary
  python roadmap.py all

""")
    sys.exit(1)

cmd = sys.argv[1].lower()

os.environ['PYTHONIOENCODING'] = 'utf-8'

if cmd in ['validate', 'v']:
    os.system('python validate_and_update_roadmap.py')
elif cmd in ['summary', 's']:
    os.system('python roadmap_summary.py')
elif cmd in ['all', 'a']:
    print("\n" + "="*80)
    print("Etapa 1: VALIDAR E ATUALIZAR")
    print("="*80)
    os.system('python validate_and_update_roadmap.py')
    print("\n\n")
    print("="*80)
    print("Etapa 2: RESUMO VISUAL")
    print("="*80)
    os.system('python roadmap_summary.py')
else:
    print(f"Comando inválido: {cmd}")
    print("Use: validate, summary, ou all")
