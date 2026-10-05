import os
from sqlalchemy import create_engine, text
from config.settings import DB_CONN, SQL_DIR

def get_engine():
    """Initialises a SQLAlchemy engine instance for data processing and loading.

    Returns:
        sqlalchemy.engine.Engine: A configured database engine instance.
    """
    return create_engine(DB_CONN)

def initialize_database():
    """Reads the schema definition file and executes SQL commands to initialise tables.

    This function locates the 'schema.sql' file, parses the individual SQL 
    statements, and executes them within a single transaction to ensure 
    the Gold layer structure is correctly established.

    Raises:
        FileNotFoundError: If the schema.sql file cannot be located in the 
            specified SQL directory.
    """
    engine = get_engine()
    schema_path = os.path.join(SQL_DIR, 'schema.sql')
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
        
    with open(schema_path, 'r') as file:
        sql_commands = file.read()
        
    with engine.begin() as conn:
        print("Initialising database schema...")
        for command in sql_commands.split(';'):
            if command.strip():
                conn.execute(text(command))
        print("Database initialisation complete.")