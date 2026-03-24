#!/bin/bash
set -e

echo "========================================="
echo "  TrafficGoat Installer"
echo "========================================="
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run as root (sudo ./install.sh)"
    exit 1
fi

echo "[*] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv python3-dev

echo "[*] Installing Python dependencies..."
pip3 install -r requirements.txt

echo "[*] Installing TrafficGoat..."
pip3 install -e .

echo ""
echo "========================================="
echo "  TrafficGoat installed successfully!"
echo "========================================="
echo ""
echo "Usage:"
echo "  sudo trafficgoat stress -t <target> -d 60"
echo "  sudo trafficgoat web --web-port 8080"
echo "  sudo trafficgoat --help"
