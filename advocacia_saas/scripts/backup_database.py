#!/usr/bin/env python3
"""
Script de backup automático do banco de dados PostgreSQL.
Faz dump do banco e envia para cloud storage (opcional).

Uso:
    python scripts/backup_database.py
    
Variáveis de ambiente:
    DATABASE_URL: URL do PostgreSQL (obrigatório)
    BACKUP_STORAGE: 's3', 'b2', 'local' (padrão: 'local')
    S3_BUCKET: Nome do bucket S3 (se BACKUP_STORAGE=s3)
    S3_ACCESS_KEY: Access key do S3
    S3_SECRET_KEY: Secret key do S3
    BACKUP_RETENTION_DAYS: Dias para manter backups (padrão: 30)
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse


def get_database_credentials():
    """Extrai credenciais do DATABASE_URL"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL não configurada")
        sys.exit(1)
    
    # Parse URL
    parsed = urlparse(database_url)
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'username': parsed.username,
        'password': parsed.password
    }


def create_backup(backup_dir='backups'):
    """Cria backup do PostgreSQL"""
    print(f"🔄 Iniciando backup do banco de dados...")
    
    # Criar diretório de backup
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    # Nome do arquivo com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'petitio_backup_{timestamp}.sql'
    filepath = backup_path / filename
    
    # Obter credenciais
    creds = get_database_credentials()
    
    # Comando pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = creds['password']
    
    cmd = [
        'pg_dump',
        '-h', creds['host'],
        '-p', str(creds['port']),
        '-U', creds['username'],
        '-d', creds['database'],
        '-F', 'c',  # Custom format (compressed)
        '-f', str(filepath)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        file_size = filepath.stat().st_size / (1024 * 1024)  # MB
        print(f"✅ Backup criado: {filename} ({file_size:.2f} MB)")
        return str(filepath)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao criar backup: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ ERROR: pg_dump não encontrado. Instale PostgreSQL client tools.")
        sys.exit(1)


def upload_to_s3(filepath):
    """Upload do backup para Amazon S3"""
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("⚠️  boto3 não instalado. Pulando upload para S3.")
        print("   Instale com: pip install boto3")
        return False
    
    bucket = os.getenv('S3_BUCKET')
    access_key = os.getenv('S3_ACCESS_KEY')
    secret_key = os.getenv('S3_SECRET_KEY')
    
    if not all([bucket, access_key, secret_key]):
        print("⚠️  Credenciais S3 incompletas. Pulando upload.")
        return False
    
    print(f"☁️  Enviando para S3 bucket: {bucket}...")
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        filename = Path(filepath).name
        s3_client.upload_file(filepath, bucket, f'backups/{filename}')
        
        print(f"✅ Upload concluído: s3://{bucket}/backups/{filename}")
        return True
        
    except ClientError as e:
        print(f"❌ Erro no upload S3: {e}")
        return False


def cleanup_old_backups(backup_dir='backups', retention_days=30):
    """Remove backups antigos"""
    print(f"🧹 Limpando backups com mais de {retention_days} dias...")
    
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    
    for backup_file in backup_path.glob('petitio_backup_*.sql'):
        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        
        if file_time < cutoff_date:
            backup_file.unlink()
            removed_count += 1
            print(f"   🗑️  Removido: {backup_file.name}")
    
    if removed_count > 0:
        print(f"✅ {removed_count} backup(s) antigo(s) removido(s)")
    else:
        print("✅ Nenhum backup antigo para remover")


def main():
    print("=" * 60)
    print("🔐 PETITIO - Backup do Banco de Dados")
    print("=" * 60)
    print()
    
    # Criar backup
    backup_file = create_backup()
    
    # Upload para cloud (se configurado)
    storage_type = os.getenv('BACKUP_STORAGE', 'local').lower()
    
    if storage_type == 's3':
        upload_to_s3(backup_file)
    elif storage_type == 'b2':
        print("⚠️  Backblaze B2 ainda não implementado")
    else:
        print("📁 Backup armazenado localmente")
    
    # Limpar backups antigos
    retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    cleanup_old_backups(retention_days=retention_days)
    
    print()
    print("=" * 60)
    print("✅ Backup concluído com sucesso!")
    print("=" * 60)


if __name__ == '__main__':
    main()
