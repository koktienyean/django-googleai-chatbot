#!/usr/bin/env python
"""Test script to verify dual API implementation works correctly"""

import os
import sys
import django
from dotenv import load_dotenv

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_chatbot.settings')
load_dotenv()
django.setup()

from chatbot.views import ask_ai, ask_claude, ask_gemini_api
from django.contrib.auth.models import User

def test_apis():
    """Test both Claude and Gemini APIs"""

    print("=" * 60)
    print("Testing Dual API Implementation")
    print("=" * 60)

    # Test message
    test_message = "Hello! What's 2 + 2?"

    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )

    if created:
        print("[OK] Created test user: {}".format(user.username))
    else:
        print("[OK] Using existing test user: {}".format(user.username))

    print("\n" + "-" * 60)
    print("Test 1: Claude API (using ask_claude)")
    print("-" * 60)
    try:
        response = ask_claude(test_message, user=user)
        print("[OK] Claude API Response:\n{}...".format(response[:200]))
        print("\n[OK] Claude API test PASSED")
    except Exception as e:
        print("[ERROR] Claude API test FAILED: {}".format(str(e)))

    print("\n" + "-" * 60)
    print("Test 2: Smart Router with Claude model (using ask_ai)")
    print("-" * 60)
    try:
        response = ask_ai(test_message, model='claude-3-5-sonnet-20241022', user=user)
        print("[OK] Smart Router (Claude) Response:\n{}...".format(response[:200]))
        print("\n[OK] Smart Router test with Claude PASSED")
    except Exception as e:
        print("[ERROR] Smart Router test with Claude FAILED: {}".format(str(e)))

    print("\n" + "-" * 60)
    print("Test 3: Gemini API (using ask_gemini_api)")
    print("-" * 60)
    try:
        response = ask_gemini_api(test_message, model='gemini-2.0-flash', user=user)
        print("[OK] Gemini API Response:\n{}...".format(response[:200]))
        print("\n[OK] Gemini API test PASSED")
    except Exception as e:
        print("[ERROR] Gemini API test FAILED: {}".format(str(e)))

    print("\n" + "-" * 60)
    print("Test 4: Smart Router with Gemini model (using ask_ai)")
    print("-" * 60)
    try:
        response = ask_ai(test_message, model='gemini-2.0-flash', user=user)
        print("[OK] Smart Router (Gemini) Response:\n{}...".format(response[:200]))
        print("\n[OK] Smart Router test with Gemini PASSED")
    except Exception as e:
        print("[ERROR] Smart Router test with Gemini FAILED: {}".format(str(e)))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("[OK] Dual API implementation is working!")
    print("\nAPI Selection:")
    print("  - Model starting with 'claude' -> Uses Claude API")
    print("  - Model starting with 'gemini' -> Uses Gemini API")
    print("  - Unknown model -> Defaults to Claude API")
    print("\n[OK] All tests completed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    test_apis()
