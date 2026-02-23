# Docker Setup Guide for AI Agent Orchestration Platform

This guide will help you properly install and verify Docker Desktop for the AI Agent Orchestration Platform project.

## Prerequisites

- Windows 11 Pro (as mentioned in your system info)
- At least 8GB RAM (16GB recommended for development)
- 20GB free disk space
- Virtualization enabled in BIOS

## Installation Steps

### 1. Download Docker Desktop
1. Go to: https://www.docker.com/products/docker-desktop
2. Click "Download for Windows"
3. Run the downloaded installer (.exe file)

### 2. Install Docker Desktop
1. Run the installer and follow the prompts
2. **IMPORTANT:** Make sure to enable WSL 2 support during installation
3. Restart your computer when prompted

### 3. Verify Installation
1. After restarting, open Docker Desktop
2. Look for the whale icon in your system tray
3. Click the icon - it should say "Docker Desktop is running"
4. Wait for the "Docker Desktop is running" message

## Verification Script

Use this Python script to verify your Docker installation:

```bash
python docker_setup_check.py
```

## Troubleshooting

### Common Issues

#### 1. "Docker is not installed"
- Make sure Docker Desktop was installed properly
- Restart your computer and try again
- Check if Docker Desktop is running

#### 2. "Docker daemon is not running"
- Open Docker Desktop
- Wait for the whale icon to show in system tray
- Ensure it says "Docker Desktop is running"

#### 3. "Docker Compose is not installed"
- Docker Compose comes with Docker Desktop
- Restart Docker Desktop
- If still not working, try reinstalling Docker Desktop

#### 4. WSL 2 Issues
- Make sure WSL 2 is enabled in Windows Features
- Run PowerShell as Administrator and execute:
  ```powershell
  wsl --install
  ```

#### 5. Virtualization Disabled
- Check if virtualization is enabled in BIOS
- Restart your computer and enter BIOS setup
- Look for "Virtualization Technology" or "VT-x/AMD-V"
- Enable it and save settings

### Error Messages

#### "Error checking Docker installation: [Errno 2] No such file or directory"
- Docker is not in your PATH
- Try restarting your computer
- Or reinstall Docker Desktop

#### "Error checking Docker daemon: [Errno 111] Connection refused"
- Docker daemon is not running
- Open Docker Desktop and wait for it to start

#### "Error checking Docker Compose: [Errno 2] No such file or directory"
- Docker Compose not installed
- Restart Docker Desktop
- If still not working, reinstall Docker Desktop

## Project Docker Requirements

Based on the CLAUDE.md file, this project requires:

- Docker Desktop for Windows
- Docker Compose (included with Docker Desktop)
- WSL 2 enabled
- At least 8GB RAM

## Next Steps After Installation

1. Clone this repository if you haven't already
2. Run the verification script: `python docker_setup_check.py`
3. Once verified, you can use Docker Compose to start the project:
   ```bash
   docker-compose up -d
   ```
4. The project will be available at the specified ports

## Alternative: Docker for Linux Users

If you're using WSL2 or a Linux distribution:

```bash
# Update package index
sudo apt-get update

# Install Docker
sudo apt-get install docker.io docker-compose

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

## Support

If you continue to have issues:
1. Check the Docker Desktop logs in the application
2. Search Docker's official documentation
3. Check the project's GitHub issues
4. Contact support with specific error messages

---

**Note:** This project requires Docker for proper development environment setup. Without Docker, you'll need to manually configure all dependencies which can be complex and time-consuming.