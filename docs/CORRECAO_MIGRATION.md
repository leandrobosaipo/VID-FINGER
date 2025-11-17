# Correção de Migration - Dependência Circular

## Problema Identificado

A migration `a34cb10e4c93_initial_schema.py` tinha uma **dependência circular**:
- `analyses` precisa de `files` (FKs: original_file_id, report_file_id, clean_video_id)
- `files` precisa de `analyses` (FK: analysis_id)

A migration tentava criar `analyses` primeiro, mas falhava porque `files` não existia ainda.

## Solução Aplicada

A migration foi corrigida para criar as tabelas **sem foreign keys primeiro**, e depois adicionar as FKs após todas as tabelas existirem.

### Ordem de Criação Corrigida

1. Criar tabela `files` (sem FK para analyses)
2. Criar tabela `analyses` (sem FKs para files)
3. Criar tabela `analysis_steps` (sem FK para analyses)
4. Adicionar FK de `files.analysis_id` → `analyses.id`
5. Adicionar FKs de `analyses` → `files.id` (original_file_id, report_file_id, clean_video_id)
6. Adicionar FK de `analysis_steps.analysis_id` → `analyses.id`

## Instruções para EasyPanel

### Se a Migration Já Foi Parcialmente Executada

Se você já tentou executar a migration anterior e ela falhou, você precisa **limpar o banco de dados** antes de tentar novamente.

#### Passo 1: Limpar Banco de Dados

1. No EasyPanel, vá para o serviço **PostgreSQL**
2. Clique em **"Console SQL"** ou **"SQL Editor"**
3. Execute os seguintes comandos:

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

**⚠️ ATENÇÃO**: Isso vai **apagar todos os dados** do banco. Use apenas se não houver dados importantes.

#### Passo 2: Fazer Novo Deploy

1. A migration corrigida será executada automaticamente no próximo deploy
2. Aguarde o deploy completar
3. Verifique os logs para confirmar que a migration foi executada com sucesso

### Verificar se a Migration Funcionou

Após o deploy, você pode verificar se as tabelas foram criadas corretamente:

1. No EasyPanel → PostgreSQL → Console SQL
2. Execute:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

Você deve ver:
- `analyses`
- `analysis_steps`
- `files`

### Verificar Foreign Keys

Para verificar se as FKs foram criadas corretamente:

```sql
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
```

## Corrigir Warning de Collation (Opcional)

Se você ver o warning:

```
WARNING: database "criadordigital" has a collation version mismatch
```

Isso não impede a migration de funcionar, mas você pode corrigir executando:

```sql
ALTER DATABASE criadordigital REFRESH COLLATION VERSION;
```

No Console SQL do PostgreSQL no EasyPanel.

## Troubleshooting

### Erro: "relation already exists"

Se você ver este erro, significa que algumas tabelas já foram criadas. Execute:

```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

E faça um novo deploy.

### Erro: "foreign key constraint violation"

Se você ver este erro ao tentar dropar tabelas, remova as FKs primeiro:

```sql
-- Remover todas as FKs manualmente (se necessário)
ALTER TABLE files DROP CONSTRAINT IF EXISTS fk_files_analysis_id;
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS fk_analyses_original_file_id;
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS fk_analyses_report_file_id;
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS fk_analyses_clean_video_id;
ALTER TABLE analysis_steps DROP CONSTRAINT IF EXISTS fk_analysis_steps_analysis_id;
```

Depois execute `DROP SCHEMA public CASCADE;` novamente.

## Status da Correção

✅ Migration corrigida e commitada
✅ Ordem de criação de tabelas corrigida
✅ Foreign keys adicionadas após criação das tabelas
✅ Função downgrade() atualizada para remover FKs antes de dropar tabelas

