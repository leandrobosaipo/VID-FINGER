# Instruções para Teste Local - VID-FINGER API

## Pré-requisitos

- Python 3.11+ instalado
- FFmpeg instalado (verificado: `/opt/homebrew/bin/ffmpeg`)
- Ambiente virtual criado e ativado

## Configuração Inicial

### 1. Ativar Ambiente Virtual

```bash
source venv/bin/activate
```

### 2. Verificar Instalação

```bash
# Verificar Python
python --version  # Deve ser 3.11+

# Verificar FFmpeg
ffmpeg -version

# Verificar dependências principais
python -c "import fastapi, sqlalchemy, uvicorn; print('OK')"
```

### 3. Configurar Variáveis de Ambiente

O arquivo `.env` já foi criado com as configurações necessárias:
- SQLite para banco de dados local
- Credenciais do DigitalOcean Spaces configuradas
- OUTPUT_PREFIX=vid-finger

### 4. Inicializar Banco de Dados

```bash
# As migrações já foram aplicadas, mas se precisar:
alembic upgrade head
```

## Executar Servidor

### Modo Desenvolvimento (com reload)

```bash
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O servidor estará disponível em:
- API: http://localhost:8000
- Documentação Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testes Automatizados

### Teste Completo com Arquivo Real

```bash
source venv/bin/activate
python scripts/test_api_local.py
```

Este script testa:
1. Health check
2. Upload init
3. Upload de chunks
4. Complete upload
5. Get analysis status

### Teste Manual via cURL

#### 1. Health Check
```bash
curl http://localhost:8000/health
```

#### 2. Iniciar Upload
```bash
curl -X POST http://localhost:8000/api/v1/upload/init \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "andando-pela-cua.mp4",
    "file_size": 1234567,
    "mime_type": "video/mp4"
  }'
```

#### 3. Upload de Chunk
```bash
# Substituir {upload_id} pelo ID retornado no passo anterior
curl -X POST http://localhost:8000/api/v1/upload/chunk/{upload_id} \
  -F "chunk_number=0" \
  -F "chunk=@/Users/leandrobosaipo/Downloads/andando-pela-cua.mp4"
```

#### 4. Completar Upload
```bash
curl -X POST http://localhost:8000/api/v1/upload/complete/{upload_id}
```

#### 5. Verificar Status da Análise
```bash
# Substituir {analysis_id} pelo ID retornado no passo anterior
curl http://localhost:8000/api/v1/analysis/{analysis_id}
```

## Teste via Swagger UI

1. Acesse http://localhost:8000/docs
2. Expanda o endpoint `/api/v1/upload/init`
3. Clique em "Try it out"
4. Preencha os dados:
   ```json
   {
     "filename": "andando-pela-cua.mp4",
     "file_size": 1234567,
     "mime_type": "video/mp4"
   }
   ```
5. Clique em "Execute"
6. Copie o `upload_id` retornado
7. Use nos próximos endpoints

## Estrutura de Arquivos Gerados

Após upload completo, os arquivos são salvos em:

```
storage/
├── uploads/          # Chunks temporários durante upload
├── original/         # Arquivos originais copiados
│   └── {analysis_id}/
│       └── {filename}
├── reports/          # Relatórios JSON (quando gerados)
│   └── {analysis_id}/
└── clean/            # Vídeos limpos (quando gerados)
    └── {analysis_id}/
```

## Banco de Dados

O banco SQLite está em: `vidfinger.db`

Para inspecionar:
```bash
sqlite3 vidfinger.db
.tables
SELECT * FROM analyses;
SELECT * FROM files;
SELECT * FROM analysis_steps;
```

## Problemas Comuns

### Erro: "ModuleNotFoundError"
```bash
source venv/bin/activate
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements-api.txt
```

### Erro: "Database locked"
- Certifique-se de que apenas uma instância do servidor está rodando
- Feche conexões antigas

### Erro: "FFmpeg not found"
- Verifique se FFmpeg está instalado: `which ffmpeg`
- Atualize `FFMPEG_PATH` no `.env` se necessário

### Erro ao conectar ao Spaces
- Verifique as credenciais no `.env`
- O erro de SSL pode ser ignorado em desenvolvimento local
- A lifecycle policy pode ser configurada manualmente no painel do Spaces

## Próximos Passos

1. **Implementar Tasks Celery**: As tasks de análise precisam ser implementadas para processar os vídeos
2. **Testar com arquivo real**: Use o script `test_api_local.py` com o arquivo `andando-pela-cua.mp4`
3. **Configurar Lifecycle Policy**: Execute `python scripts/setup_spaces_lifecycle.py` (pode falhar por SSL, mas pode ser configurado manualmente)
4. **Implementar endpoints de download**: Completar endpoints de reports e files

## Arquivo de Teste

O arquivo de teste está em:
```
/Users/leandrobosaipo/Downloads/andando-pela-cua.mp4
```

Este arquivo será usado automaticamente pelo script `test_api_local.py`.

## Verificação Final

Execute este comando para verificar se tudo está funcionando:

```bash
source venv/bin/activate && \
python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
print('Health:', client.get('/health').json())
print('Root:', client.get('/').json())
print('✓ API funcionando!')
"
```

Se tudo estiver OK, você verá:
```
Health: {'status': 'healthy', 'version': '1.0.0'}
Root: {'name': 'VID-FINGER API', 'version': '1.0.0', 'status': 'running'}
✓ API funcionando!
```

