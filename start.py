#!/usr/bin/env python3
"""
RuleForge Backend Startup Script
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def check_virtual_environment():
    """Check if virtual environment is activated."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
        return True
    else:
        print("⚠️  Virtual environment not detected")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

def setup_environment():
    """Setup environment variables."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from .env.example...")
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✅ .env file created. Please edit it with your API keys.")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  No .env.example file found")

def initialize_database():
    """Initialize the database."""
    print("🗄️  Initializing database...")
    try:
        # First test the connection
        import subprocess
        result = subprocess.run([sys.executable, "test_connection.py"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Database connection test passed")
            
            # Create tables using simple script
            result = subprocess.run([sys.executable, "create_tables.py"], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Database tables created successfully")
                return True
            else:
                print(f"❌ Error creating tables: {result.stderr}")
                return False
        else:
            print(f"❌ Database connection test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

def start_server():
    """Start the FastAPI server."""
    print("🚀 Starting RuleForge Backend server...")
    try:
        import uvicorn
        from app.core.config import settings
        
        uvicorn.run(
            "main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=settings.debug
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

def main():
    """Main startup function."""
    print("🔧 RuleForge Backend Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Check virtual environment
    venv_active = check_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Setup environment
    setup_environment()
    
    # Initialize database
    if not initialize_database():
        print("  Database initialization failed, but continuing...")
        print("You can manually run: python create_tables.py")
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\n📚 API Documentation:")
    print("   - Swagger UI: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")
    print("\n🔧 Next steps:")
    print("   1. Edit .env file with your API keys")
    print("   2. The server will start automatically")
    print("=" * 50)
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()