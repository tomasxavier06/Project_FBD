# Funções de conexão à base de dados
import pyodbc
from contextlib import contextmanager
from config import DB_CONFIG


def get_db_connection():
    """Obtém uma conexão com a base de dados SQL Server."""
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']}"
    return pyodbc.connect(conn_str)


@contextmanager
def get_db():
    """Context manager que garante fecho da conexão mesmo com exceções."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def generate_id(table_name, id_column):
    """Gera um ID único para qualquer tabela."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = f"SELECT ISNULL(MAX({id_column}), 0) + 1 FROM {table_name}"
        cursor.execute(query)
        new_id = cursor.fetchone()[0]
    return new_id

