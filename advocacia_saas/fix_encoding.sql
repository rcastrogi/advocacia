UPDATE petition_types SET name = 'Acao de Cobranca' WHERE slug = 'acao-de-cobranca';
UPDATE petition_types SET name = 'Acao de Alimentos' WHERE slug = 'acao-de-alimentos';
UPDATE petition_types SET name = 'Acao de Divorcio' WHERE slug = 'acao-de-divorcio';
UPDATE petition_types SET name = 'Acao de Reintegracao de Posse' WHERE slug = 'acao-de-reintegracao';
SELECT slug, name FROM petition_types WHERE slug LIKE 'acao%';
