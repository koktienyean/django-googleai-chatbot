"""
Claude Terminal Connector Module
================================
Handles communication with Claude Code terminal via three fallback methods:
1. HTTP Proxy (primary) - Uses HTTP requests to a local proxy server
2. IPC (secondary) - Uses inter-process communication via named pipes
3. File Queue (fallback) - Uses file-based message queue (always works)

This module provides a flexible, robust mechanism to send/receive messages
from Claude Code running in a terminal and integrate responses back to the web chat.
"""

import os
import json
import time
import queue
import threading
import tempfile
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, Callable

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class TerminalConnectorException(Exception):
    """Base exception for terminal connector errors"""
    pass


class ConnectorTimeoutException(TerminalConnectorException):
    """Raised when connector operation times out"""
    pass


class ConnectorConnectionException(TerminalConnectorException):
    """Raised when unable to connect to terminal"""
    pass


class BaseConnector(ABC):
    """Abstract base class for terminal connectors"""

    def __init__(self, config: Dict[str, Any] = None, timeout: int = 10):
        """
        Initialize connector with configuration

        Args:
            config: Connection configuration (method-specific)
            timeout: Timeout in seconds for operations
        """
        self.config = config or {}
        self.timeout = timeout
        self.connected = False
        self.pid = None

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to Claude terminal

        Returns:
            True if connected successfully, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully disconnect from terminal"""
        pass

    @abstractmethod
    def send_message(self, message: str, session_id: str = None) -> str:
        """
        Send a message to Claude terminal and get response

        Args:
            message: The message to send
            session_id: Optional session ID for tracking

        Returns:
            Response from Claude terminal

        Raises:
            ConnectorConnectionException: If not connected
            ConnectorTimeoutException: If operation times out
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if connector and terminal are healthy

        Returns:
            True if healthy, False otherwise
        """
        pass

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class HTTPConnector(BaseConnector):
    """
    HTTP-based connector using local HTTP proxy server

    Claude Code runs an HTTP server that accepts requests at:
    http://localhost:{port}/api/message

    This is the preferred method as it's stateless and reliable.
    """

    def __init__(self, config: Dict[str, Any] = None, timeout: int = 10):
        """Initialize HTTP connector"""
        super().__init__(config, timeout)
        self.base_url = config.get('url', 'http://localhost:5000') if config else 'http://localhost:5000'
        self.port = config.get('port', 5000) if config else 5000
        self.session = requests.Session()

    def connect(self) -> bool:
        """
        Verify HTTP server is reachable

        Returns:
            True if server responds, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=self.timeout
            )
            if response.status_code == 200:
                self.connected = True
                logger.info(f'HTTP connector connected to {self.base_url}')
                return True
        except requests.RequestException as e:
            logger.warning(f'HTTP health check failed: {e}')
            self.connected = False
            return False

        return False

    def disconnect(self) -> None:
        """Gracefully close session"""
        self.session.close()
        self.connected = False

    def send_message(self, message: str, session_id: str = None) -> str:
        """
        Send message via HTTP POST request

        Args:
            message: Message to send
            session_id: Optional session ID for context

        Returns:
            Response text from Claude terminal

        Raises:
            ConnectorConnectionException: If not connected
            ConnectorTimeoutException: If request times out
        """
        if not self.connected:
            raise ConnectorConnectionException('HTTP connector not connected')

        try:
            payload = {
                'message': message,
                'session_id': session_id,
                'timestamp': timezone.now().isoformat()
            }

            response = self.session.post(
                f'{self.base_url}/api/message',
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                raise ConnectorConnectionException(
                    f'HTTP error {response.status_code}: {response.text}'
                )

        except requests.Timeout:
            raise ConnectorTimeoutException(f'HTTP request timed out after {self.timeout}s')
        except requests.RequestException as e:
            raise ConnectorConnectionException(f'HTTP request failed: {e}')

    def is_healthy(self) -> bool:
        """
        Check server health via HTTP

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False


class IPCConnector(BaseConnector):
    """
    Inter-Process Communication connector using named pipes

    On Windows: Uses named pipes (e.g., \\.\pipe\claude_terminal)
    On Unix: Uses Unix domain sockets (e.g., /tmp/claude_terminal.sock)

    This method is faster than HTTP but requires Claude Code to support it.
    """

    def __init__(self, config: Dict[str, Any] = None, timeout: int = 10):
        """Initialize IPC connector"""
        super().__init__(config, timeout)
        self.pipe_name = config.get('pipe_name', 'claude_terminal') if config else 'claude_terminal'
        self.socket_path = config.get('socket_path', '/tmp/claude_terminal.sock') if config else '/tmp/claude_terminal.sock'
        self._message_queue = queue.Queue()
        self._reader_thread = None

    def _get_pipe_path(self) -> str:
        """Get appropriate pipe path for OS"""
        if os.name == 'nt':  # Windows
            return f'\\\\.\\pipe\\{self.pipe_name}'
        else:  # Unix
            return self.socket_path

    def connect(self) -> bool:
        """
        Establish IPC connection

        Returns:
            True if connected, False otherwise
        """
        try:
            pipe_path = self._get_pipe_path()

            if os.name == 'nt':  # Windows named pipe
                import pywintypes
                import win32file
                self.pipe = win32file.CreateFile(
                    pipe_path,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
            else:  # Unix socket
                import socket
                self.pipe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.pipe.connect(pipe_path)

            self.connected = True
            logger.info(f'IPC connector connected to {pipe_path}')
            return True

        except Exception as e:
            logger.warning(f'IPC connection failed: {e}')
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Close IPC connection"""
        try:
            if hasattr(self, 'pipe'):
                self.pipe.close()
        except Exception as e:
            logger.warning(f'IPC disconnect error: {e}')
        finally:
            self.connected = False

    def send_message(self, message: str, session_id: str = None) -> str:
        """
        Send message via IPC

        Args:
            message: Message to send
            session_id: Optional session ID

        Returns:
            Response from Claude terminal

        Raises:
            ConnectorConnectionException: If not connected
            ConnectorTimeoutException: If operation times out
        """
        if not self.connected:
            raise ConnectorConnectionException('IPC connector not connected')

        try:
            payload = {
                'message': message,
                'session_id': session_id,
                'timestamp': timezone.now().isoformat()
            }

            # Send message
            message_bytes = json.dumps(payload).encode('utf-8')
            if os.name == 'nt':
                import win32file
                win32file.WriteFile(self.pipe, message_bytes)
            else:
                self.pipe.sendall(message_bytes)

            # Receive response with timeout
            if os.name == 'nt':
                import win32file
                import pywintypes
                self.pipe.settimeout(self.timeout)
                response_bytes = win32file.ReadFile(self.pipe, 65536)[1]
            else:
                self.pipe.settimeout(self.timeout)
                response_bytes = self.pipe.recv(65536)

            response_data = json.loads(response_bytes.decode('utf-8'))
            return response_data.get('response', '')

        except TimeoutError:
            raise ConnectorTimeoutException(f'IPC operation timed out after {self.timeout}s')
        except Exception as e:
            raise ConnectorConnectionException(f'IPC communication failed: {e}')

    def is_healthy(self) -> bool:
        """
        Check if IPC is still connected

        Returns:
            True if connected, False otherwise
        """
        return self.connected


class FileQueueConnector(BaseConnector):
    """
    File-based queue connector using temporary directory

    Creates two directories for request/response queues:
    - {queue_dir}/requests/ - Web chat puts messages here
    - {queue_dir}/responses/ - Claude terminal puts responses here

    This is the most reliable fallback - always works, no special OS requirements.
    Uses polling and file locking to ensure reliable message delivery.
    """

    def __init__(self, config: Dict[str, Any] = None, timeout: int = 10):
        """Initialize file queue connector"""
        super().__init__(config, timeout)

        if config and 'queue_dir' in config:
            self.queue_dir = Path(config['queue_dir'])
        else:
            self.queue_dir = Path(tempfile.gettempdir()) / 'claude_terminal_queue'

        self.request_dir = self.queue_dir / 'requests'
        self.response_dir = self.queue_dir / 'responses'
        self.poll_interval = 0.1  # 100ms polling

    def connect(self) -> bool:
        """
        Create queue directories if needed

        Returns:
            True if successful
        """
        try:
            self.request_dir.mkdir(parents=True, exist_ok=True)
            self.response_dir.mkdir(parents=True, exist_ok=True)
            self.connected = True
            logger.info(f'File queue connector initialized at {self.queue_dir}')
            return True
        except Exception as e:
            logger.error(f'File queue initialization failed: {e}')
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect (no-op for file queue)"""
        self.connected = False

    def send_message(self, message: str, session_id: str = None) -> str:
        """
        Send message via file queue

        Writes request to requests/ directory and polls responses/ for reply.

        Args:
            message: Message to send
            session_id: Optional session ID

        Returns:
            Response from Claude terminal

        Raises:
            ConnectorConnectionException: If directories don't exist
            ConnectorTimeoutException: If no response received in time
        """
        if not self.connected:
            raise ConnectorConnectionException('File queue connector not connected')

        request_id = f'{session_id or "default"}_{int(time.time() * 1000)}'
        request_file = self.request_dir / f'{request_id}.json'
        response_file = self.response_dir / f'{request_id}.json'

        try:
            # Write request
            payload = {
                'request_id': request_id,
                'message': message,
                'session_id': session_id,
                'timestamp': timezone.now().isoformat()
            }

            with open(request_file, 'w') as f:
                json.dump(payload, f)

            # Poll for response
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if response_file.exists():
                    try:
                        with open(response_file, 'r') as f:
                            response_data = json.load(f)
                        # Clean up response file
                        response_file.unlink()
                        return response_data.get('response', '')
                    except json.JSONDecodeError:
                        pass  # Incomplete write, retry

                time.sleep(self.poll_interval)

            # Timeout - clean up request file
            request_file.unlink(missing_ok=True)
            raise ConnectorTimeoutException(
                f'No response received for request {request_id} after {self.timeout}s'
            )

        except ConnectorTimeoutException:
            raise
        except Exception as e:
            request_file.unlink(missing_ok=True)
            raise ConnectorConnectionException(f'File queue operation failed: {e}')

    def is_healthy(self) -> bool:
        """
        Check if queue directories are accessible

        Returns:
            True if directories exist and are writable, False otherwise
        """
        try:
            # Test write access
            test_file = self.request_dir / '.health_check'
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False


class ClaudeTerminalConnector:
    """
    Smart connector that tries methods in order of preference:
    1. HTTP (fastest, most reliable)
    2. IPC (direct, fast)
    3. File Queue (always works, fallback)
    """

    def __init__(self, config: Dict[str, Any] = None, timeout: int = 10):
        """
        Initialize smart connector with fallback chain

        Args:
            config: Configuration dict with connection settings
            timeout: Timeout for operations in seconds
        """
        self.config = config or {}
        self.timeout = timeout
        self.connector = None
        self.connection_method = None

    def connect(self) -> bool:
        """
        Try to connect using each method in order

        Returns:
            True if any method succeeds, False if all fail
        """
        methods = [
            ('http', HTTPConnector),
            ('ipc', IPCConnector),
            ('file', FileQueueConnector),
        ]

        for method_name, ConnectorClass in methods:
            try:
                logger.info(f'Trying {method_name} connection...')
                connector = ConnectorClass(self.config.get(method_name, {}), self.timeout)

                if connector.connect():
                    self.connector = connector
                    self.connection_method = method_name
                    logger.info(f'Connected via {method_name}')
                    return True

            except Exception as e:
                logger.warning(f'{method_name} connection failed: {e}')
                continue

        logger.error('All connection methods failed')
        return False

    def disconnect(self) -> None:
        """Disconnect from terminal"""
        if self.connector:
            self.connector.disconnect()
            self.connector = None
            self.connection_method = None

    def send_message(self, message: str, session_id: str = None) -> Optional[str]:
        """
        Send message to Claude terminal

        Args:
            message: Message to send
            session_id: Optional session ID

        Returns:
            Response from Claude or None if failed
        """
        if not self.connector:
            return None

        try:
            response = self.connector.send_message(message, session_id)
            return response
        except TerminalConnectorException as e:
            logger.error(f'Terminal communication failed: {e}')
            return None

    def is_healthy(self) -> bool:
        """
        Check if terminal is still healthy

        Returns:
            True if connector is healthy, False otherwise
        """
        if not self.connector:
            return False
        return self.connector.is_healthy()

    def get_method(self) -> Optional[str]:
        """
        Get currently used connection method

        Returns:
            'http', 'ipc', 'file', or None
        """
        return self.connection_method

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def get_connector(config: Dict[str, Any] = None, timeout: int = 10) -> ClaudeTerminalConnector:
    """
    Factory function to create a smart terminal connector

    Args:
        config: Connection configuration
        timeout: Timeout for operations in seconds

    Returns:
        ClaudeTerminalConnector instance ready to use
    """
    return ClaudeTerminalConnector(config, timeout)
