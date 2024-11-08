#!/bin/bash

# Update the system
dnf update -y

# Install Apache web server
dnf install -y httpd

# Start and enable Apache
systemctl start httpd
systemctl enable httpd

# Create a simple web page
echo echo "<h1>Hello World from $(hostname -f)</h1>" > /var/www/html/index.html

# Set appropriate permissions
chown -R apache:apache /var/www/html

