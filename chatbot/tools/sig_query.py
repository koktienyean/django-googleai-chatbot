"""
SIG_Chart external API client for AI-driven database queries.
Provides schema discovery, sample data, and raw SQL execution
against the external PostgreSQL reporting database.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SIG_BASE_URL = os.getenv('SIG_BASE_URL', 'http://localhost:8000')

# In-memory schema cache (refreshes every 30 minutes)
_schema_cache = {
    'data': None,
    'timestamp': 0,
}
SCHEMA_CACHE_TTL = 1800  # 30 minutes


def get_schema():
    """Fetch full database schema from SIG_Chart API.

    Returns tables, columns with descriptions, join relationships,
    module groupings, and naming conventions. Cached in memory.
    """
    now = time.time()
    if _schema_cache['data'] and (now - _schema_cache['timestamp']) < SCHEMA_CACHE_TTL:
        return _schema_cache['data']

    try:
        url = f"{SIG_BASE_URL}/SIG_Chart/api/schema/"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        _schema_cache['data'] = data
        _schema_cache['timestamp'] = now
        return data
    except requests.exceptions.ConnectionError:
        return {'error': f'Cannot connect to SIG_Chart API at {SIG_BASE_URL}. Check SIG_BASE_URL in .env'}
    except requests.exceptions.Timeout:
        return {'error': 'SIG_Chart schema request timed out (15s)'}
    except Exception as e:
        return {'error': f'Failed to fetch schema: {str(e)}'}


def get_sample_data(table, limit=5):
    """Fetch sample rows from a table to understand data patterns.

    Args:
        table: Table name (e.g., PTS_PlanningHeader)
        limit: Number of rows (max 20)
    """
    if not table:
        return {'error': 'Table name is required'}

    limit = min(int(limit), 20)

    try:
        url = f"{SIG_BASE_URL}/SIG_Chart/api/schema/sample/"
        resp = requests.get(url, params={'table': table, 'limit': limit}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {'error': f'Cannot connect to SIG_Chart API at {SIG_BASE_URL}'}
    except requests.exceptions.Timeout:
        return {'error': 'Sample data request timed out (10s)'}
    except Exception as e:
        return {'error': f'Failed to fetch sample data: {str(e)}'}


def execute_sql(sql, limit=100):
    """Execute a raw SELECT SQL query against the external database.

    Args:
        sql: SELECT query (PostgreSQL syntax, double-quote identifiers)
        limit: Max rows to return (max 1000)

    Safety: The SIG_Chart API enforces SELECT-only, 10s timeout, max 1000 rows.
    """
    if not sql:
        return {'error': 'SQL query is required'}

    limit = min(int(limit), 1000)

    try:
        url = f"{SIG_BASE_URL}/SIG_Chart/api/query/"
        resp = requests.post(
            url,
            json={'sql': sql, 'limit': limit},
            headers={'Content-Type': 'application/json'},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {'error': f'Cannot connect to SIG_Chart API at {SIG_BASE_URL}'}
    except requests.exceptions.Timeout:
        return {'error': 'SQL query timed out (15s)'}
    except Exception as e:
        return {'error': f'Failed to execute query: {str(e)}'}
