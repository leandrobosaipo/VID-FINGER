"""Configuração centralizada de logging."""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from app.config import settings

# Referência global para o listener (para evitar garbage collection)
_log_listener = None


def sanitize_sensitive_data(message: str) -> str:
    """
    Sanitiza dados sensíveis em mensagens de log.
    
    Remove ou mascarar:
    - Senhas (password, pwd, secret)
    - Tokens (token, api_key, access_key, secret_key)
    - URLs com credenciais
    """
    import re
    
    # Padrões para remover/mascarar
    patterns = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'password="***"'),
        (r'pwd["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'pwd="***"'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'secret="***"'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'token="***"'),
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'api_key="***"'),
        (r'access_key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'access_key="***"'),
        (r'secret_key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', r'secret_key="***"'),
        # URLs com credenciais: http://user:pass@host
        (r'(https?://)([^:]+):([^@]+)@', r'\1***:***@'),
    ]
    
    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


class SanitizedFormatter(logging.Formatter):
    """Formatter que sanitiza dados sensíveis."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Formatar normalmente
        formatted = super().format(record)
        # Sanitizar
        return sanitize_sensitive_data(formatted)


def setup_logging():
    """
    Configura logging centralizado da aplicação.
    
    Suporta:
    - Logs assíncronos (via QueueHandler)
    - Output em console e/ou arquivo
    - Formato estruturado com timestamps
    - Sanitização de dados sensíveis
    """
    # Determinar nível de log
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Formato estruturado
    if settings.LOG_FORMAT == "structured":
        log_format = '[%(asctime)s.%(msecs)03d] [%(levelname)-7s] [%(name)s] %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
    else:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
    
    # Criar formatter com sanitização
    formatter = SanitizedFormatter(log_format, datefmt=date_format)
    
    # Criar handlers
    handlers = []
    
    # Handler para console (sempre)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)
    
    # Handler para arquivo (se configurado)
    if settings.LOG_FILE:
        log_file_path = Path(settings.LOG_FILE)
        # Criar diretório se não existir
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []  # Limpar handlers existentes
    
        # Se LOG_FILE está configurado, usar QueueHandler para logs assíncronos
    global _log_listener
    if settings.LOG_FILE:
        # Criar queue para logs assíncronos
        log_queue = Queue(-1)  # Queue ilimitada
        
        # QueueHandler para root logger (logs assíncronos)
        queue_handler = QueueHandler(log_queue)
        queue_handler.setFormatter(formatter)
        root_logger.addHandler(queue_handler)
        
        # QueueListener processa logs em background
        _log_listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
        _log_listener.start()
    else:
        # Logs síncronos (só console)
        for handler in handlers:
            root_logger.addHandler(handler)
    
    # Configurar nível de logs de bibliotecas externas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtém logger configurado com nome do módulo."""
    return logging.getLogger(name)

