#!/usr/bin/env python3
"""
Docker Setup Verification Script
Checks if Docker Desktop is properly installed and running
"""

import subprocess
import sys
import os

def check_docker_installed():
    """Check if Docker is installed"""
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Docker installed: {result.stdout.strip()}")
            return True
        return False
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"❌ Error checking Docker installation: {e}")
        return False

def check_docker_daemon():
    """Check if Docker daemon is running"""
    try:
        result = subprocess.run(['docker', 'ps'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker daemon is running")
            return True
        return False
    except Exception as e:
        print(f"❌ Error checking Docker daemon: {e}")
        return False

def check_docker_compose():
    """Check if Docker Compose is installed"""
    try:
        # Check docker-compose command
        result = subprocess.run(['docker-compose', '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Docker Compose installed: {result.stdout.strip()}")
            return True

        # Check docker compose (v2)
        result = subprocess.run(['docker', 'compose', '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Docker Compose v2 installed: {result.stdout.strip()}")
            return True

        return False
    except Exception as e:
        print(f"❌ Error checking Docker Compose: {e}")
        return False

def main():
    print("=== Docker Setup Verification ===\n")

    # Check Docker installation
    print("- Checking Docker installation...")
    if not check_docker_installed():
        print("❌ Docker is not installed")
        print("\n💡 Installation Instructions for Windows:")
        print("1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop")
        print("2. Run the installer and follow the prompts")
        print("3. Restart your computer when prompted")
        print("4. Make sure to enable WSL 2 support during installation")
        sys.exit(1)

    # Check Docker daemon
    print("- Checking Docker daemon...")
    if not check_docker_daemon():
        print("❌ Docker daemon is not running")
        print("\n💡 To start Docker daemon:")
        print("1. Open Docker Desktop")
        print("2. Make sure the whale icon appears in your system tray")
        print("3. Click the icon and ensure it says 'Docker Desktop is running'")
        sys.exit(1)

    # Check Docker Compose
    print("- Checking Docker Compose...")
    if not check_docker_compose():
        print("❌ Docker Compose is not installed")
        print("\n💡 Installation Instructions:")
        print("Docker Compose is included with Docker Desktop, so:")
        print("1. Make sure Docker Desktop is properly installed")
        print("2. Restart Docker Desktop")
        print("3. If still not working, try reinstalling Docker Desktop")
        sys.exit(1)

    print("\n✅ All Docker components are properly installed and running!")
    print("🚀 You're ready to use Docker for this project!")

if __name__ == "__main__":
    main()