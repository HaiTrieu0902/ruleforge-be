"""
Simple database table creation script
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_tables():
    """Create the required tables in PostgreSQL."""
    
    # SQL statements to create tables
    create_documents_table = """
    CREATE TABLE IF NOT EXISTS documents (
        id VARCHAR PRIMARY KEY,
        filename VARCHAR NOT NULL,
        file_path VARCHAR NOT NULL,
        document_type VARCHAR NOT NULL,
        content TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_summaries_table = """
    CREATE TABLE IF NOT EXISTS summaries (
        id VARCHAR PRIMARY KEY,
        document_id VARCHAR NOT NULL,
        summary_text TEXT NOT NULL,
        model_used VARCHAR NOT NULL,
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_rules_table = """
    CREATE TABLE IF NOT EXISTS rules (
        id VARCHAR PRIMARY KEY,
        document_id VARCHAR NOT NULL,
        rules_json JSONB NOT NULL,
        ai_provider VARCHAR NOT NULL,
        is_deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create indexes
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_documents_id ON documents(id);",
        "CREATE INDEX IF NOT EXISTS idx_summaries_document_id ON summaries(document_id);",
        "CREATE INDEX IF NOT EXISTS idx_rules_document_id ON rules(document_id);",
    ]
    
    try:
        # Connect to database
        connection = psycopg2.connect(
            host="localhost",
            port=5432,
            database="ruleforge",
            user="postgres",
            password="040202005173"
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        print("🗄️  Creating database tables...")
        
        # Create tables
        cursor.execute(create_documents_table)
        print("✅ Documents table created/verified")
        
        cursor.execute(create_summaries_table)
        print("✅ Summaries table created/verified")
        
        cursor.execute(create_rules_table)
        print("✅ Rules table created/verified")
        
        # Create indexes
        for index_sql in create_indexes:
            cursor.execute(index_sql)
        print("✅ Database indexes created/verified")
        
        cursor.close()
        connection.close()
        
        print("🎉 Database tables created successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_tables()