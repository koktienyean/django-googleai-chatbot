"""
Shared AI tool definitions, executors, and format converters.
Used by Claude, Gemini, and Ollama backends.
"""
from .definitions import get_tool_definitions, SYSTEM_INSTRUCTION
from .executors import execute_tool
from .formatters import format_tools_for_claude, format_tools_for_gemini, format_tools_for_ollama
from .query_engine import execute_query
from .report_builder import ReportBuilder
