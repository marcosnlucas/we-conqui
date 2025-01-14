#!/bin/bash

# Configurações
VPS_IP="137.184.112.131"
VPS_USER="root"
PROJECT_NAME="matriz-we-conqui"

echo "Copiando arquivos para o VPS..."
scp -r ../matriz-we-conqui $VPS_USER@$VPS_IP:/root/

echo "Conectando ao VPS e configurando..."
ssh $VPS_USER@$VPS_IP << 'EOF'
    cd /root/matriz-we-conqui

    # Construir e iniciar o container
    docker build -t matriz-we-conqui .
    docker stop matriz-we-conqui 2>/dev/null || true
    docker rm matriz-we-conqui 2>/dev/null || true
    docker run -d \
        --name matriz-we-conqui \
        -p 5001:5001 \
        -v $(pwd)/instance:/app/instance \
        -v $(pwd)/logs:/app/logs \
        --restart unless-stopped \
        matriz-we-conqui

    # Configurar Nginx
    echo "Adicionando configuração do Nginx..."
    cat nginx-config >> /etc/nginx/sites-available/tools.seoz.com.br
    
    # Testar e recarregar Nginx
    nginx -t && systemctl reload nginx

    echo "Verificando status do container..."
    docker ps | grep matriz-we-conqui
EOF

echo "Deploy concluído!"
echo "A aplicação estará disponível em: https://tools.seoz.com.br/matriz-we-conqui"
