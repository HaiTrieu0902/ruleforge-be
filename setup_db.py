"""
Database setup script for PostgreSQL
This script creates the database if it doesn't exist and sets up the tables.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from app.core.config import settings

def create_database_if_not_exists():
    """Create the ruleforge database if it doesn't exist."""
    try:
        # Connect to PostgreSQL server (default database)
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database='postgres'  # Connect to default database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (settings.db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            # Create the database
            cursor.execute(f'CREATE DATABASE "{settings.db_name}"')
            print(f"✅ Database '{settings.db_name}' created successfully")
        else:
            print(f"✅ Database '{settings.db_name}' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        print("Please check your PostgreSQL connection settings:")
        print(f"  Host: {settings.db_host}")
        print(f"  Port: {settings.db_port}")
        print(f"  User: {settings.db_user}")
        print("  Make sure PostgreSQL is running and the user has permissions to create databases")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def setup_database():
    """Complete database setup process."""
    print("🗄️  Setting up PostgreSQL database...")
    
    # Step 1: Create database if needed
    if not create_database_if_not_exists():
        return False
    
    # Step 2: Create tables
    try:
        from app.models.database import init_db, create_test_data
        
        if init_db():
            print("✅ Database tables created successfully")
            
            # Step 3: Create test data (optional)
            create_test_data()
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error setting up database tables: {e}")
        return False

if __name__ == "__main__":
    if setup_database():
        print("🎉 Database setup completed successfully!")
    else:
        print("❌ Database setup failed!")
        sys.exit(1)