# Problema Identificado: Relatório não sendo salvo no banco

## Status
- ✅ Relatório é criado no filesystem corretamente
- ❌ Relatório não é vinculado à análise no banco de dados (report_file_id permanece NULL)
- ✅ Arquivo File não é criado no banco para o relatório

## Análise
O código está tentando salvar o relatório, mas o commit não está persistindo o `report_file_id` na tabela `analyses`.

## Possíveis Causas
1. Problema de sessão de banco de dados - objeto `analysis` pode não estar na sessão correta
2. Commit pode estar sendo revertido por algum motivo
3. Exceção silenciosa durante o commit

## Próximos Passos
1. Verificar logs do servidor para erros
2. Adicionar mais validações e logs detalhados
3. Testar commit isoladamente
4. Verificar se há constraints ou triggers no banco que possam estar bloqueando

