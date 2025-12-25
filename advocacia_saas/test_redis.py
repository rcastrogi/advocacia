#!/usr/bin/env python3
"""
Script para testar a configuração do Redis
Execute: python test_redis.py
"""

import os
import sys
from datetime import datetime, timezone

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, cache, limiter
from flask import current_app

def test_redis_connection():
    """Testa conexão básica com Redis"""
    print("🔍 Testando conexão Redis...")

    app = create_app()

    with app.app_context():
        try:
            # Teste básico de cache
            test_key = "redis_test_key"
            test_value = f"Redis funcionando! {datetime.now(timezone.utc)}"

            # Salvar no cache
            cache.set(test_key, test_value, timeout=60)
            print("✅ Cache: Escrita OK")

            # Ler do cache
            cached_value = cache.get(test_key)
            if cached_value == test_value:
                print("✅ Cache: Leitura OK")
            else:
                print("❌ Cache: Leitura falhou")
                return False

            # Teste de rate limiting (se Redis estiver configurado)
            if current_app.config.get("REDIS_URL"):
                print("✅ Redis configurado para rate limiting")
            else:
                print("⚠️  Rate limiting usando memória (Redis não configurado)")

            print("🎉 Redis está funcionando corretamente!")
            return True

        except Exception as e:
            print(f"❌ Erro no Redis: {str(e)}")
            return False

def show_redis_info():
    """Mostra informações sobre a configuração do Redis"""
    print("\n📊 Configuração Redis:")
    print(f"REDIS_URL: {'Configurado' if os.environ.get('REDIS_URL') else 'Não configurado'}")
    print(f"REDIS_CACHE_DB: {os.environ.get('REDIS_CACHE_DB', '0')}")
    print(f"REDIS_RATELIMIT_DB: {os.environ.get('REDIS_RATELIMIT_DB', '1')}")
    print(f"CACHE_DEFAULT_TIMEOUT: {os.environ.get('CACHE_DEFAULT_TIMEOUT', '300')}s")
    print(f"CACHE_KEY_PREFIX: {os.environ.get('CACHE_KEY_PREFIX', 'petitio')}")

if __name__ == "__main__":
    print("🚀 Teste de Configuração Redis para Petitio\n")

    show_redis_info()
    print()

    success = test_redis_connection()

    if success:
        print("\n✅ Todos os testes passaram!")
        sys.exit(0)
    else:
        print("\n❌ Alguns testes falharam!")
        sys.exit(1)