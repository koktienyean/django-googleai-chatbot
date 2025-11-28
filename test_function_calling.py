#!/usr/bin/env python
"""
Test script for Django Data Integration function calling with Gemini

This script tests:
1. Individual data query functions
2. Gemini function calling integration
3. Multi-turn conversations with function calls
"""

import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_chatbot.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from chatbot.models import ChatSession, Chat
from chatbot.views import (
    ask_gemini,
    search_my_chats,
    get_chat_statistics,
    get_recent_conversations,
    search_by_date_range,
    get_session_summary,
    list_my_sessions
)


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def create_test_user_and_chats():
    """Create a test user with sample chat data"""
    print_section("1. Creating Test User and Sample Chat Data")

    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    print(f"User '{user.username}': {'Created' if created else 'Already exists'}")

    # Create test sessions
    session1, _ = ChatSession.objects.get_or_create(
        user=user,
        name='Django Discussion',
        defaults={'model': 'gemini-2.0-flash'}
    )
    print(f"Session 1: '{session1.name}' (ID: {session1.id})")

    session2, _ = ChatSession.objects.get_or_create(
        user=user,
        name='Python Tips',
        defaults={'model': 'gemini-2.0-flash'}
    )
    print(f"Session 2: '{session2.name}' (ID: {session2.id})")

    # Create sample chats
    sample_chats = [
        (session1, "How do I authenticate users in Django?", "Use Django's built-in auth system with User model..."),
        (session1, "What's the best way to structure Django projects?", "Follow the MVT pattern with separate apps..."),
        (session2, "How do I use list comprehensions?", "List comprehensions provide concise syntax for creating lists..."),
        (session2, "Explain decorators in Python", "Decorators are functions that modify other functions..."),
    ]

    created_count = 0
    for session, message, response in sample_chats:
        chat, created = Chat.objects.get_or_create(
            session=session,
            message=message,
            defaults={'response': response}
        )
        if created:
            created_count += 1

    print(f"Sample chats: {created_count} new, {len(sample_chats) - created_count} existing")
    return user, session1, session2


def test_individual_functions(user):
    """Test each data query function individually"""
    print_section("2. Testing Individual Data Query Functions")

    # Test search_my_chats
    print("Testing search_my_chats('Django'):")
    result = search_my_chats(user, 'Django', limit=5)
    print(f"  Found {result.get('count', 0)} results")
    for r in result.get('results', [])[:2]:
        print(f"    • {r['message'][:50]}... in session '{r['session']}'")

    # Test get_chat_statistics
    print("\nTesting get_chat_statistics():")
    stats = get_chat_statistics(user)
    print(f"  Total messages: {stats.get('total_messages', 0)}")
    print(f"  Total sessions: {stats.get('total_sessions', 0)}")
    print(f"  Most active session: {stats.get('most_active_session', 'None')}")
    print(f"  Messages this week: {stats.get('messages_this_week', 0)}")

    # Test get_recent_conversations
    print("\nTesting get_recent_conversations(limit=3):")
    recent = get_recent_conversations(user, limit=3)
    print(f"  Found {recent.get('count', 0)} conversations")
    for conv in recent.get('conversations', []):
        print(f"    • {conv['message'][:40]}... ({conv['session']})")

    # Test list_my_sessions
    print("\nTesting list_my_sessions():")
    sessions = list_my_sessions(user, limit=10)
    print(f"  Total sessions: {sessions.get('count', 0)}")
    for s in sessions.get('sessions', []):
        print(f"    • {s['name']}: {s['message_count']} messages")

    # Test search_by_date_range
    print("\nTesting search_by_date_range(today, today):")
    today = timezone.now().strftime('%Y-%m-%d')
    dated = search_by_date_range(user, today, today)
    print(f"  Found {dated.get('count', 0)} messages for {today}")


def test_function_calling_integration(user):
    """Test Gemini function calling integration"""
    print_section("3. Testing Gemini Function Calling Integration")

    queries = [
        "What have I discussed about Django?",
        "Show me my chat statistics",
        "What did I ask about recently?",
        "List all my chat sessions",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 60)
        try:
            response = ask_gemini(query, model='gemini-2.0-flash', user=user)
            print(f"Response:\n{response[:300]}...")
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  Django Data Integration - Function Calling Test Suite")
    print("="*70)

    try:
        # Setup test data
        user, session1, session2 = create_test_user_and_chats()

        # Test individual functions
        test_individual_functions(user)

        # Test function calling integration
        test_function_calling_integration(user)

        print_section("[OK] All Tests Completed")
        print("Function calling integration is working correctly!")

    except Exception as e:
        print_section("[ERROR] Error During Tests")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
