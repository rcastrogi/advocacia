#!/usr/bin/env python
"""Verifica se a tabela ai_credit_config foi criada corretamente."""
import os
import sys

# Adiciona o diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import AICreditConfig

app = create_app()

output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_config_result.txt")

with app.app_context():
    try:
        configs = AICreditConfig.query.all()
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"=== AI Credit Config - Verificacao ===\n\n")
            f.write(f"Total de configuracoes: {len(configs)}\n\n")
            
            for c in configs:
                f.write(f"- {c.operation_key}: {c.credit_cost} creditos (premium={c.is_premium}, ativo={c.is_active})\n")
            
            f.write(f"\n=== SUCESSO! Tabela existe e tem dados. ===\n")
        
        print(f"Resultado salvo em: {output_file}")
        
    except Exception as e:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"ERRO: {e}\n")
        print(f"Erro: {e}")
