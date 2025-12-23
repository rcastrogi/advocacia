#!/usr/bin/env python3
"""
Script para executar manualmente no Render via shell
"""

import os
import sys

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_examples():
    print("🚀 Executando exemplos manualmente...")

    try:
        # Importar e executar create_real_case_examples.py
        print("📝 Executando create_real_case_examples.py...")
        exec(open("create_real_case_examples.py").read())
        print("✅ create_real_case_examples.py executado!")

        # Importar e executar create_real_case_templates.py
        print("📝 Executando create_real_case_templates.py...")
        exec(open("create_real_case_templates.py").read())
        print("✅ create_real_case_templates.py executado!")

        print("🎉 Todos os exemplos criados com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_examples()
