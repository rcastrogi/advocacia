import sqlite3

conn = sqlite3.connect("instance/advocacia_saas.db")
cursor = conn.cursor()

# Criar tabela roadmap_categories
cursor.execute("""
CREATE TABLE IF NOT EXISTS roadmap_categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL
)
""")

# Criar tabela roadmap_items
cursor.execute("""
CREATE TABLE IF NOT EXISTS roadmap_items (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    detailed_description TEXT,
    status VARCHAR(20) DEFAULT 'planned',
    priority VARCHAR(20) DEFAULT 'medium',
    estimated_effort VARCHAR(20) DEFAULT 'medium',
    visible_to_users BOOLEAN DEFAULT 0,
    internal_only BOOLEAN DEFAULT 0,
    show_new_badge BOOLEAN DEFAULT 0,
    planned_start_date DATE,
    planned_completion_date DATE,
    actual_start_date DATE,
    actual_completion_date DATE,
    implemented_at DATETIME,
    business_value TEXT,
    technical_complexity VARCHAR(20) DEFAULT 'medium',
    user_impact VARCHAR(20) DEFAULT 'medium',
    impact_score INTEGER DEFAULT 3,
    effort_score INTEGER DEFAULT 3,
    dependencies TEXT,
    blockers TEXT,
    tags VARCHAR(500),
    notes TEXT,
    created_by INTEGER,
    assigned_to INTEGER,
    last_updated_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES roadmap_categories(id)
)
""")

# Inserir categoria
cursor.execute("INSERT OR IGNORE INTO roadmap_categories (id, name) VALUES (1, 'Core Features')")

# Inserir items
cursor.execute("""
INSERT OR IGNORE INTO roadmap_items 
(id, category_id, title, slug, description) 
VALUES
(1, 1, 'Authentication System', 'auth-system', 'Implement secure authentication'),
(2, 1, 'Petition Management', 'petition-management', 'Manage legal petitions')
""")

conn.commit()
print("[OK] Tabelas e dados criados com sucesso!")
conn.close()
