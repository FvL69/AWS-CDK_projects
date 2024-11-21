#!/bin/bash

# Update the system
dnf update -y

# Install Apache web server
dnf install -y httpd

# Start and enable Apache
systemctl start httpd
systemctl enable httpd

# Create a simple web page
echo "<html><body><h1>Hello from AWS EC2!</h1></body></html>" > /var/www/html/index.html

# Set appropriate permissions
chown -R apache:apache /var/www/html
