"""Middleware de logging de requisições HTTP."""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.utils.context import set_correlation_id, get_correlation_id, format_log_with_context

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logar todas as requisições HTTP."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processa requisição e loga entrada/saída."""
        # Gerar Correlation ID
        correlation_id = set_correlation_id()
        start_time = time.time()
        
        # Logar requisição recebida
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Sanitizar headers sensíveis
        headers_dict = dict(request.headers)
        sensitive_headers = ['authorization', 'cookie', 'x-api-key', 'x-access-token']
        for header in sensitive_headers:
            if header in headers_dict:
                headers_dict[header] = "***"
        
        self.logger.info(
            format_log_with_context(
                "REQUEST",
                f"→ {request.method} {request.url.path} | IP: {client_ip} | User-Agent: {user_agent[:50]}",
                **({"query": str(request.query_params)} if request.query_params else {})
            )
        )
        
        # Logar body se for pequeno (máx 1KB) e não for binário
        # Não logar body para uploads de arquivo (pode ser muito grande)
        if request.method in ["POST", "PUT", "PATCH"] and "/upload/" not in str(request.url.path):
            try:
                # Verificar se já foi lido
                if hasattr(request, '_body') and request._body:
                    body = request._body
                else:
                    body = await request.body()
                    # Restaurar body para processamento (fastapi precisa)
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
                
                if len(body) < 1024:  # Apenas se menor que 1KB
                    body_str = body.decode('utf-8', errors='ignore')[:200]  # Primeiros 200 chars
                    if body_str:
                        self.logger.debug(
                            format_log_with_context(
                                "REQUEST",
                                f"Body: {body_str}"
                            )
                        )
            except Exception as e:
                self.logger.debug(
                    format_log_with_context(
                        "REQUEST",
                        f"Não foi possível ler body: {e}"
                    )
                )
        
        # Processar requisição
        try:
            response = await call_next(request)
        except Exception as e:
            # Logar erro
            duration = time.time() - start_time
            self.logger.error(
                format_log_with_context(
                    "REQUEST",
                    f"❌ Erro ao processar requisição: {type(e).__name__}: {str(e)}",
                ),
                exc_info=True
            )
            raise
        
        # Calcular duração
        duration = time.time() - start_time
        
        # Logar resposta
        status_code = response.status_code
        status_emoji = "✅" if 200 <= status_code < 300 else "⚠️" if 300 <= status_code < 400 else "❌"
        
        # Tentar obter tamanho da resposta
        response_size = None
        if hasattr(response, 'body'):
            try:
                response_size = len(response.body)
            except:
                pass
        
        size_info = f" | Size: {response_size} bytes" if response_size else ""
        
        self.logger.info(
            format_log_with_context(
                "REQUEST",
                f"{status_emoji} ← {status_code} {response.status_text} | Duration: {duration:.3f}s{size_info}"
            )
        )
        
        # Adicionar Correlation ID no header da resposta (opcional, útil para debug)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response

