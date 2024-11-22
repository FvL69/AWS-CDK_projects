#!/bin/bash

# Update the system
dnf update -y

# Install Apache web server
dnf install -y httpd

# Create directory if it doesn't exist
mkdir -p /var/www/html

# Create a simple web page
echo "<html><body><h1>Hello from AWS EC2!</h1></body></html>" > /var/www/html/index.html

# Set appropriate permissions
chown -R apache:apache /var/www/html
chmod -R 755 /var/www/html

# Start and enable Apache
systemctl start httpd
systemctl enable httpd
