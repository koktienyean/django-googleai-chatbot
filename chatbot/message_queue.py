"""
Async message queue system for processing Gemini API requests without blocking.
Uses threading for background processing of chat messages.
"""

import threading
import queue
import uuid
from datetime import datetime
import logging
import google.generativeai as genai
import os
from django.core.cache import cache

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Background worker that processes messages asynchronously"""

    def __init__(self):
        self.message_queue = queue.Queue()
        self.responses = {}  # request_id -> {status, response/error, timestamp}
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("MessageProcessor started")

    def _worker(self):
        """Background thread that processes queued messages"""
        while True:
            try:
                request_id, session_id, message = self.message_queue.get(timeout=1)

                try:
                    # Import here to avoid circular imports
                    from .models import ChatSession, Chat

                    # Get session and its model
                    session = ChatSession.objects.get(id=session_id)

                    # Call Gemini API
                    response_text = self._ask_gemini(message, session.model)

                    # Store response
                    self.responses[request_id] = {
                        'status': 'completed',
                        'response': response_text,
                        'timestamp': datetime.now().isoformat()
                    }

                    # Save to database
                    Chat.objects.create(
                        session=session,
                        message=message,
                        response=response_text
                    )

                    logger.info(f"Message processed: {request_id}")

                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    logger.error(error_msg)
                    self.responses[request_id] = {
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker thread error: {str(e)}")

    def _ask_gemini(self, message, model='gemini-1.5-flash'):
        """Call Gemini API and return response text"""
        try:
            API_SECRET_KEY = os.getenv('API_SECRET_KEY')
            genai.configure(api_key=API_SECRET_KEY)

            model_obj = genai.GenerativeModel(model)
            chat = model_obj.start_chat()
            response = chat.send_message(message)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    def queue_message(self, session_id, message):
        """Queue a message for async processing"""
        request_id = str(uuid.uuid4())
        self.message_queue.put((request_id, session_id, message))
        logger.info(f"Message queued: {request_id}")
        return request_id

    def get_response(self, request_id):
        """Get response status or result"""
        if request_id in self.responses:
            response = self.responses[request_id]
            # Keep response for 5 minutes (300 seconds) for client polling
            # Cleanup happens via TTL
            return response
        return {'status': 'pending'}

    def cleanup_old_responses(self, max_age_seconds=300):
        """Remove responses older than max_age_seconds"""
        now = datetime.now()
        expired_ids = []

        for request_id, response in self.responses.items():
            try:
                response_time = datetime.fromisoformat(response['timestamp'])
                age = (now - response_time).total_seconds()
                if age > max_age_seconds:
                    expired_ids.append(request_id)
            except (KeyError, ValueError):
                expired_ids.append(request_id)

        for request_id in expired_ids:
            del self.responses[request_id]
            logger.info(f"Cleaned up response: {request_id}")


# Global message processor instance
message_processor = MessageProcessor()
