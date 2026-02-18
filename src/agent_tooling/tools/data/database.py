"""
Database Tools - Query databases using SQL.

Supports multiple database backends through connection strings.
"""

from typing import Any, Dict, List, Optional

from agent_tooling.tools.decorator import tool
from agent_tooling.tools.base import ToolError


SAMPLES = {
    "query_database": [
        {
            "name": "mock_select",
            "description": "Run a mock SELECT query (no DB connection needed)",
            "input": {"sql": "SELECT * FROM users LIMIT 5"},
        },
    ],
}


# Connection registry for database connections
_connections: Dict[str, Any] = {}


def register_connection(name: str, connection: Any) -> None:
    """Register a database connection for use by the query tool."""
    _connections[name] = connection


def get_connection(name: str) -> Optional[Any]:
    """Get a registered database connection."""
    return _connections.get(name)


@tool(name="query_database", category="data", mcp_enabled=True)
def query_database(
    sql: str,
    connection: str = "default",
    parameters: Optional[Dict[str, Any]] = None,
) -> dict:
    """Execute a SQL query against a database.

    Args:
        sql: SQL query to execute
        connection: Name of the database connection to use (default: "default")
        parameters: Query parameters for parameterized queries (optional)

    Returns:
        Dictionary with query results and metadata
    """
    conn = get_connection(connection)

    if conn is None:
        # Return mock data for demonstration
        return {
            "success": True,
            "message": f"Mock query executed (no '{connection}' connection registered)",
            "sql": sql,
            "rows": [
                {"id": 1, "name": "Example Row 1"},
                {"id": 2, "name": "Example Row 2"},
            ],
            "row_count": 2,
            "note": "Register a real connection using register_connection() for actual queries",
        }

    try:
        cursor = conn.cursor()

        if parameters:
            cursor.execute(sql, parameters)
        else:
            cursor.execute(sql)

        # Check if this is a SELECT query
        if sql.strip().upper().startswith("SELECT"):
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            return {
                "success": True,
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows),
            }
        else:
            conn.commit()
            return {
                "success": True,
                "rows_affected": cursor.rowcount,
            }

    except Exception as e:
        raise ToolError(str(e), tool_name="query_database")
    finally:
        if "cursor" in locals():
            cursor.close()
