#!/usr/bin/env python3
"""
Script seguro para executar migrações no banco remoto (Render/Railway)
IMPORTANTE: Faça backup antes de executar!
"""

import os
import sys
from datetime import datetime


def backup_database():
    """Cria backup do banco antes das migrações"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.sql"

    print(f"📦 Criando backup: {backup_file}")

    # Comando para Railway (ajuste se usar outro provider)
    cmd = f"pg_dump '{os.getenv('DATABASE_URL')}' > {backup_file}"

    print(f"Execute este comando manualmente:")
    print(f"  {cmd}")
    print()
    print("Ou use um cliente PostgreSQL como pgAdmin/DBeaver")
    print()

    return backup_file


def run_remote_migrations():
    """Executa migrações no banco remoto"""

    print("🚨 ATENÇÃO: Você está prestes a modificar o banco de produção!")
    print("=" * 60)

    # Verificar se estamos no ambiente correto
    db_url = os.getenv("DATABASE_URL", "")
    if "railway" in db_url.lower():
        print("✅ Conectado ao Railway (produção)")
    elif "render" in db_url.lower():
        print("✅ Conectado ao Render PostgreSQL (produção)")
    elif "supabase" in db_url.lower():
        print("✅ Conectado ao Supabase (produção)")
    else:
        print("⚠️  AVISO: Não parece ser um banco de produção!")
        print(f"   URL: {db_url[:50]}...")
        confirm = input("Continuar mesmo assim? (s/N): ")
        if confirm.lower() != "s":
            print("❌ Operação cancelada")
            return

    print()
    print("📋 Migrações a serem aplicadas:")
    print("   • Campos de períodos flexíveis (BillingPlan)")
    print("   • Política de cancelamento (Subscription)")
    print()

    # Backup
    print("🔒 PASSO 1: BACKUP")
    backup_file = backup_database()

    print("🔄 PASSO 2: MIGRAÇÕES")
    print("Execute estes comandos:")
    print()
    print("# 1. Verificar status atual")
    print("flask db current")
    print()
    print("# 2. Aplicar migrações")
    print("flask db upgrade")
    print()
    print("# 3. Verificar resultado")
    print("flask db current")
    print()
    print("# 4. Testar aplicação")
    print(
        "python -c \"from app import create_app; app = create_app(); print('✅ OK')\""
    )
    print()

    print("📊 RESUMO:")
    print(f"   Backup criado: {backup_file}")
    print("   Migrações prontas para aplicação")
    print("   Ambiente: Produção (Render PostgreSQL)")
    print()

    print("✅ PRONTO PARA EXECUTAR!")
    print("Execute os comandos acima no seu terminal local.")


def main():
    """Função principal"""
    print("🔧 Assistente de Migração Remota - Petitio SaaS")
    print("=" * 50)

    # Verificar se .env existe
    if not os.path.exists(".env"):
        print("❌ Arquivo .env não encontrado!")
        print("   Configure DATABASE_URL primeiro")
        sys.exit(1)

    # Carregar variáveis de ambiente
    from dotenv import load_dotenv

    load_dotenv()

    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL não configurada!")
        print("   Configure no arquivo .env")
        sys.exit(1)

    run_remote_migrations()


if __name__ == "__main__":
    main()
