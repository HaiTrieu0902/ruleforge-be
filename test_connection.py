"""
Simple PostgreSQL connection test
"""
import psycopg2

def test_postgres_connection():
    try:
        # Test connection with the provided credentials
        connection = psycopg2.connect(
            host="localhost",
            port=5432,
            database="ruleforge",
            user="postgres",
            password="040202005173"
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL connection successful!")
        print(f"Server version: {version[0]}")
        
        cursor.close()
        connection.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

if __name__ == "__main__":
    test_postgres_connection()