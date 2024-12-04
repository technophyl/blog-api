#!/bin/bash

# Exit on error
set -e

# Check if required environment variables are set
required_vars=("DB_USER" "DB_PASSWORD" "DB_NAME" "IP_ADDRESS")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set. Please export $var before running this script."
        exit 1
    fi
done

echo "Starting Blog Platform API deployment..."

# Check Python version
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ is required"' || {
    echo "Python 3.11+ is required but not installed. Installing..."
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3-pip
}

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is required but not installed. Installing..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
fi

# Check if Redis is installed
if ! command -v redis-cli &> /dev/null; then
    echo "Redis is required but not installed. Installing..."
    sudo apt update
    sudo apt install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
fi


# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo "git is required but not installed. Installing..."
    sudo apt update
    sudo apt install -y git
fi

# Clone the repository, and navigate to the project directory
git clone https://github.com/technophyl/blog-api.git
cd blog-api

# Backup existing virtual environment if it exists
if [ -d "venv" ]; then
    echo "Backing up existing virtual environment..."
    mv venv venv_backup_$(date +%Y%m%d_%H%M%S)
fi

# Create and activate virtual environment
echo "Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies with error handling
echo "Installing dependencies..."
pip install --upgrade pip
if ! pip install -r requirements.txt; then
    echo "Error installing dependencies. Rolling back..."
    rm -rf venv
    if [ -d "venv_backup_*" ]; then
        mv venv_backup_* venv
    fi
    exit 1
fi

# Setup PostgreSQL database with error handling
echo "Setting up PostgreSQL database..."
sudo bash -c "cat > /home/ubuntu/init.sql << EOF
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
ALTER USER ${DB_USER} WITH SUPERUSER;
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
EOF"

sudo chmod 644 /home/ubuntu/init.sql
sudo chown postgres:postgres /home/ubuntu/init.sql
sudo mv /home/ubuntu/init.sql /tmp/init.sql
sudo -iu postgres psql -f /tmp/init.sql



# Create .env file
echo "Creating .env file..."
cat > .env << EOF
API_V1_STR="/api/v1"
PROJECT_NAME="Blog Platform API"
BACKEND_CORS_ORIGINS=["*"]

# PostgreSQL Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}

# JWT Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_EXPIRE_IN_SECONDS=300
EOF

# Secure .env file permissions
chmod 600 .env

# Configure Redis with proper bind address
echo "Configuring Redis..."
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
sudo sed -i 's/bind 127.0.0.1/bind 127.0.0.1/g' /etc/redis/redis.conf
sudo systemctl restart redis-server

# Create systemd service with proper permissions
echo "Creating systemd service..."
sudo bash -c "cat > /etc/systemd/system/blog-platform.service << EOF
[Unit]
Description=Blog Platform API
After=network.target postgresql.service redis-server.service

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PWD
Environment=PATH=$PWD/venv/bin
ExecStart=$PWD/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd and start service
echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable blog-platform
sudo systemctl start blog-platform

# Setup Nginx as reverse proxy with SSL
echo "Setting up Nginx..."
if ! command -v nginx &> /dev/null; then
    sudo apt update
    sudo apt install -y nginx certbot python3-certbot-nginx
fi

# Create Nginx configuration with security headers
sudo bash -c "cat > /etc/nginx/sites-available/blog-platform << EOF
server {
    listen 80;
    server_name ${IP_ADDRESS};
EOF"


sudo bash -c 'cat >> /etc/nginx/sites-available/blog-platform << "EOF"

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src '\''self'\'' http: https: data: blob: '\''unsafe-inline'\''" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF'




# Remove default nginx site if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Enable site and restart Nginx
sudo ln -sf /etc/nginx/sites-available/blog-platform /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Configure firewall
# echo "Configuring firewall..."
# sudo ufw allow 'Nginx Full'
# sudo ufw allow 8000
# sudo ufw enable

echo "Deployment completed successfully!"
echo "API is now running at http://${IP_ADDRESS}"
echo "
Next steps:
1. Set up SSL certificate:
   sudo certbot --nginx -d ${IP_ADDRESS}
2. Monitor the application:
   sudo journalctl -u blog-platform -f
3. Check the application status:
   sudo systemctl status blog-platform
"

# Export required environment variables
export DB_USER=blog_user
export DB_PASSWORD=EPSl95rYyDhT1xWX1cEgGF7tYmJT3GwR
export DB_NAME=blog_db_tx0r
export IP_ADDRESS=5.34.206.190

# Make the script executable
chmod +x deploy.sh

# Run the script
./deploy.sh