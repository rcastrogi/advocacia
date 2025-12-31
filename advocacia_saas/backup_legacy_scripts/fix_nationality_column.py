"""Script para padronizar colunas de endereço na tabela user"""

from app import create_app, db

app = create_app()

with app.app_context():
    # Remove coluna antiga 'address' se existir
    try:
        db.session.execute(db.text('ALTER TABLE "user" DROP COLUMN IF EXISTS address;'))
        print("🗑️  Removida coluna antiga 'address'")
    except Exception as e:
        print(f"⚠️  address: {e}")

    # Adiciona colunas padronizadas de endereço (igual ao modelo Client)
    columns_to_add = [
        (
            "nationality",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS nationality VARCHAR(50);',
        ),
        ("cep", 'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS cep VARCHAR(10);'),
        ("street", 'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS street VARCHAR(200);'),
        ("number", 'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS number VARCHAR(20);'),
        ("uf", 'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS uf VARCHAR(2);'),
        ("city", 'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS city VARCHAR(100);'),
        (
            "neighborhood",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS neighborhood VARCHAR(100);',
        ),
        (
            "complement",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS complement VARCHAR(200);',
        ),
        (
            "logo_filename",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(200);',
        ),
        (
            "billing_status",
            "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS billing_status VARCHAR(50) DEFAULT 'active';",
        ),
        (
            "quick_actions",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS quick_actions TEXT;',
        ),
        (
            "stripe_customer_id",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);',
        ),
        (
            "password_changed_at",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;',
        ),
        (
            "password_expires_at",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMP;',
        ),
        (
            "password_history",
            "ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS password_history TEXT DEFAULT '[]';",
        ),
        (
            "force_password_change",
            'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS force_password_change BOOLEAN DEFAULT FALSE;',
        ),
    ]

    print("\n📋 Adicionando colunas padronizadas:")
    for col_name, sql in columns_to_add:
        try:
            db.session.execute(db.text(sql))
            print(f"✅ {col_name}")
        except Exception as e:
            print(f"❌ {col_name}: {e}")

    try:
        db.session.commit()
        print("\n✅ Migração concluída! Endereços agora estão padronizados.")
        print("\n📦 Campos de endereço (padrão Client):")
        print("   • CEP - Busca automática via API")
        print("   • Logradouro (street)")
        print("   • Número")
        print("   • UF (estado)")
        print("   • Cidade")
        print("   • Bairro (neighborhood)")
        print("   • Complemento")
    except Exception as e:
        print(f"\n❌ Erro ao commit: {e}")
        db.session.rollback()
