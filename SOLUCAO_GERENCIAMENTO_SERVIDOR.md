# Solução: Gerenciamento do Servidor - Problema de Porta em Uso

## Problema Identificado
- Múltiplos processos tentando usar a porta 8000 simultaneamente
- Processos órfãos não sendo parados antes de iniciar novos servidores
- Falta de script de gerenciamento (start/stop/restart)
- Servidor conseguia carregar aplicação mas falhava ao fazer bind na porta

## Solução Implementada

### Scripts Criados

1. **scripts/manage_server.sh**
   - Script completo de gerenciamento do servidor
   - Funções: start, stop, restart, status, logs
   - Verificações automáticas de dependências
   - Limpeza automática de processos antigos

2. **scripts/start_server.sh**
   - Wrapper simples que chama manage_server.sh start

### Funcionalidades

#### `start`
- Para processos antigos na porta 8000
- Verifica dependências (Python, FFmpeg, Redis, DB)
- Verifica se aplicação carrega sem erros
- Inicia servidor em background
- Testa health check após iniciar
- Cria arquivo `.server.pid` para rastreamento

#### `stop`
- Para todos os processos na porta 8000
- Tenta parar graciosamente primeiro (SIGTERM)
- Se necessário, força parada (SIGKILL)
- Limpa arquivo `.server.pid`

#### `restart`
- Para servidor atual
- Inicia novo servidor

#### `status`
- Verifica se servidor está rodando
- Mostra PIDs dos processos
- Testa health check
- Mostra informações do servidor

#### `logs`
- Mostra últimas 50 linhas do arquivo `server.log`

### Verificações Implementadas

1. **Dependências**
   - Python3 instalado
   - FFmpeg disponível
   - Redis rodando (opcional)
   - Aplicação carrega sem erros

2. **Porta**
   - Verifica se porta está livre antes de iniciar
   - Para processos antigos automaticamente
   - Valida que servidor iniciou corretamente

3. **Health Check**
   - Testa endpoint `/health` após iniciar
   - Valida resposta do servidor

## Uso

### Iniciar Servidor
```bash
./scripts/manage_server.sh start
# ou
./scripts/start_server.sh
```

### Parar Servidor
```bash
./scripts/manage_server.sh stop
```

### Reiniciar Servidor
```bash
./scripts/manage_server.sh restart
```

### Verificar Status
```bash
./scripts/manage_server.sh status
```

### Ver Logs
```bash
./scripts/manage_server.sh logs
```

## Testes Realizados

✅ **stop**: Para processos corretamente
✅ **start**: Inicia servidor com verificações
✅ **restart**: Para e reinicia corretamente
✅ **status**: Verifica status e health check
✅ **logs**: Mostra logs corretamente
✅ **Health check**: Servidor responde corretamente
✅ **Sem processos duplicados**: Apenas um processo na porta 8000

## Status Final

✅ **PROBLEMA RESOLVIDO**

O servidor agora pode ser gerenciado facilmente usando o script `manage_server.sh`. O problema de múltiplos processos na porta 8000 foi resolvido com limpeza automática antes de iniciar.

## Arquivos Criados

- `scripts/manage_server.sh` - Script principal de gerenciamento
- `scripts/start_server.sh` - Wrapper simples
- `.server.pid` - Arquivo de rastreamento do PID (criado automaticamente)
- `server.log` - Logs do servidor (criado automaticamente)

