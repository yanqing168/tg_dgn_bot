"""
Debug parser test
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.premium.recipient_parser import RecipientParser

# Test 33 character username
long_username = "@" + "a" * 33
print(f"Testing: {long_username}")
print(f"Length: {len(long_username)}")

result = RecipientParser.parse(long_username)
print(f"Parse result: {result}")
print(f"Result is empty: {len(result) == 0}")

# Test 32 character username  
max_username = "@" + "a" * 32
print(f"\nTesting: {max_username[:20]}...")
print(f"Length: {len(max_username)}")

result2 = RecipientParser.parse(max_username)
print(f"Parse result: {result2}")
print(f"Result is empty: {len(result2) == 0}")

# Test 31 character username
username_31 = "@" + "a" * 31
print(f"\nTesting: {username_31[:20]}...")
print(f"Length: {len(username_31)}")

result3 = RecipientParser.parse(username_31)
print(f"Parse result: {result3}")
print(f"Result is empty: {len(result3) == 0}")
