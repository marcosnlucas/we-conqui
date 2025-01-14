#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Iniciando deploy da Matriz WE Conqui...${NC}"

# Criar diretório de logs
echo -e "${GREEN}Criando diretório de logs...${NC}"
mkdir -p logs

# Construir a imagem Docker
echo -e "${GREEN}Construindo imagem Docker...${NC}"
docker build -t matriz-we-conqui .

# Parar container existente se houver
echo -e "${GREEN}Verificando containers existentes...${NC}"
docker stop matriz-we-conqui 2>/dev/null || true
docker rm matriz-we-conqui 2>/dev/null || true

# Iniciar novo container
echo -e "${GREEN}Iniciando novo container...${NC}"
docker run -d \
    --name matriz-we-conqui \
    -p 5001:5001 \
    -v $(pwd)/instance:/app/instance \
    -v $(pwd)/logs:/app/logs \
    --restart unless-stopped \
    matriz-we-conqui

echo -e "${GREEN}Verificando status do container...${NC}"
sleep 3
docker ps | grep matriz-we-conqui

echo -e "${BLUE}Deploy concluído!${NC}"
echo -e "${BLUE}A aplicação está rodando em: http://localhost:5001${NC}"
