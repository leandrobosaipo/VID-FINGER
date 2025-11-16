#!/bin/bash
# Script de gerenciamento do servidor VID-FINGER
# Uso: ./scripts/manage_server.sh [start|stop|restart|status|logs]

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
PORT=8000
HOST="0.0.0.0"
APP_MODULE="app.main:app"
PID_FILE=".server.pid"
LOG_FILE="server.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Função para imprimir mensagens coloridas
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Função para verificar se porta está em uso
check_port_in_use() {
    local pids=$(lsof -ti:$PORT 2>/dev/null || echo "")
    if [ -n "$pids" ]; then
        echo "$pids"
        return 0
    else
        return 1
    fi
}

# Função para parar servidor
stop_server() {
    print_info "Parando servidor na porta $PORT..."
    
    local pids=$(check_port_in_use)
    if [ -z "$pids" ]; then
        print_warning "Nenhum processo encontrado na porta $PORT"
        # Limpar PID file se existir
        [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
        return 0
    fi
    
    # Tentar parar graciosamente primeiro
    for pid in $pids; do
        if ps -p $pid > /dev/null 2>&1; then
            print_info "Parando processo $pid..."
            kill $pid 2>/dev/null || true
        fi
    done
    
    # Aguardar um pouco
    sleep 2
    
    # Verificar se ainda há processos
    local remaining_pids=$(check_port_in_use)
    if [ -n "$remaining_pids" ]; then
        print_warning "Alguns processos não pararam, forçando..."
        for pid in $remaining_pids; do
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
        done
        sleep 1
    fi
    
    # Limpar PID file
    [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
    
    # Verificar se parou
    if check_port_in_use > /dev/null 2>&1; then
        print_error "Falha ao parar todos os processos na porta $PORT"
        return 1
    else
        print_success "Servidor parado com sucesso"
        return 0
    fi
}

# Função para verificar dependências
check_dependencies() {
    print_info "Verificando dependências..."
    
    local errors=0
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 não encontrado"
        errors=$((errors + 1))
    else
        print_success "Python3 encontrado: $(python3 --version)"
    fi
    
    # Verificar FFmpeg
    if ! command -v ffmpeg &> /dev/null; then
        print_warning "FFmpeg não encontrado (opcional para algumas funcionalidades)"
    else
        print_success "FFmpeg encontrado: $(ffmpeg -version | head -1)"
    fi
    
    # Verificar Redis (opcional)
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping > /dev/null 2>&1; then
            print_success "Redis está rodando"
        else
            print_warning "Redis não está rodando (opcional, usado para Celery)"
        fi
    else
        print_warning "redis-cli não encontrado (opcional)"
    fi
    
    # Verificar se aplicação importa sem erros
    print_info "Verificando se aplicação carrega sem erros..."
    if python3 -c "from app.config import settings; print('OK')" 2>/dev/null; then
        print_success "Aplicação carrega corretamente"
    else
        print_error "Erro ao carregar aplicação"
        print_info "Tentando importar para ver erro detalhado..."
        python3 -c "from app.config import settings" 2>&1 | head -10
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        print_error "Algumas dependências críticas estão faltando"
        return 1
    fi
    
    return 0
}

# Função para iniciar servidor
start_server() {
    print_info "Iniciando servidor na porta $PORT..."
    
    # Parar processos antigos primeiro
    stop_server
    
    # Verificar dependências
    if ! check_dependencies; then
        print_error "Dependências não satisfeitas. Corrija os problemas antes de continuar."
        return 1
    fi
    
    # Verificar se porta está livre
    if check_port_in_use > /dev/null 2>&1; then
        print_error "Porta $PORT ainda está em uso após tentativa de parar processos"
        return 1
    fi
    
    # Iniciar servidor em background
    print_info "Iniciando uvicorn..."
    nohup python3 -m uvicorn "$APP_MODULE" \
        --host "$HOST" \
        --port "$PORT" \
        --log-level info \
        > "$LOG_FILE" 2>&1 &
    
    local server_pid=$!
    echo $server_pid > "$PID_FILE"
    
    # Aguardar servidor iniciar
    print_info "Aguardando servidor iniciar..."
    sleep 3
    
    # Verificar se processo ainda está rodando
    if ! ps -p $server_pid > /dev/null 2>&1; then
        print_error "Servidor não iniciou. Verifique os logs:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
    
    # Verificar se porta está em uso (servidor iniciou)
    if ! check_port_in_use > /dev/null 2>&1; then
        print_error "Servidor iniciou mas porta não está em uso"
        tail -20 "$LOG_FILE"
        return 1
    fi
    
    # Testar health check
    print_info "Testando health check..."
    sleep 2
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        print_success "Servidor iniciado com sucesso!"
        print_info "PID: $server_pid"
        print_info "Porta: $PORT"
        print_info "Logs: $LOG_FILE"
        print_info "API: http://localhost:$PORT"
        print_info "Docs: http://localhost:$PORT/docs"
        return 0
    else
        print_warning "Servidor iniciou mas health check falhou"
        print_info "Verificando logs..."
        tail -30 "$LOG_FILE"
        return 1
    fi
}

# Função para verificar status
status_server() {
    print_info "Verificando status do servidor..."
    
    local pids=$(check_port_in_use)
    if [ -z "$pids" ]; then
        print_warning "Servidor não está rodando na porta $PORT"
        return 1
    fi
    
    print_success "Servidor está rodando"
    print_info "PIDs: $pids"
    
    # Verificar PID file
    if [ -f "$PID_FILE" ]; then
        local saved_pid=$(cat "$PID_FILE")
        print_info "PID salvo: $saved_pid"
    fi
    
    # Testar health check
    print_info "Testando health check..."
    local health_response=$(curl -s "http://localhost:$PORT/health" 2>/dev/null || echo "")
    if [ -n "$health_response" ]; then
        print_success "Health check OK: $health_response"
        return 0
    else
        print_warning "Health check falhou"
        return 1
    fi
}

# Função para mostrar logs
show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_warning "Arquivo de log não encontrado: $LOG_FILE"
        return 1
    fi
    
    print_info "Mostrando últimas 50 linhas do log..."
    echo ""
    tail -50 "$LOG_FILE"
}

# Função para reiniciar servidor
restart_server() {
    print_info "Reiniciando servidor..."
    stop_server
    sleep 1
    start_server
}

# Função principal
main() {
    local command="${1:-start}"
    
    case "$command" in
        start)
            start_server
            ;;
        stop)
            stop_server
            ;;
        restart)
            restart_server
            ;;
        status)
            status_server
            ;;
        logs)
            show_logs
            ;;
        *)
            echo "Uso: $0 [start|stop|restart|status|logs]"
            echo ""
            echo "Comandos:"
            echo "  start   - Inicia o servidor (para processos antigos primeiro)"
            echo "  stop    - Para o servidor na porta $PORT"
            echo "  restart - Para e reinicia o servidor"
            echo "  status  - Verifica se servidor está rodando"
            echo "  logs    - Mostra logs do servidor"
            exit 1
            ;;
    esac
}

# Executar função principal
main "$@"

