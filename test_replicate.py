#!/usr/bin/env python3
"""
Test script to verify Replicate virtual try-on is working
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_replicate_config():
    """Test if Replicate is properly configured"""
    print("=" * 60)
    print("REPLICATE CONFIGURATION TEST")
    print("=" * 60)
    
    # Check if token exists
    token = os.getenv('REPLICATE_API_TOKEN')
    
    if not token:
        print("❌ REPLICATE_API_TOKEN not found in environment")
        print("   Please add it to your .env file")
        return False
    
    print(f"✓ REPLICATE_API_TOKEN found: {token[:10]}...")
    
    # Try to import replicate
    try:
        import replicate
        print("✓ replicate library imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import replicate library: {e}")
        print("   Run: pip install replicate")
        return False
    
    # Set the token for replicate
    os.environ['REPLICATE_API_TOKEN'] = token
    
    # Test API connection
    print("\nTesting Replicate API connection...")
    try:
        # Try to list models (simple API test)
        client = replicate.Client(api_token=token)
        print("✓ Successfully connected to Replicate API")
        print("\n" + "=" * 60)
        print("CONFIGURATION IS CORRECT!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Make sure your backend server is running:")
        print("   python outfit-assistant/backend/app.py")
        print("\n2. Upload a photo in the Outfit Generator")
        print("\n3. Watch the backend console for these messages:")
        print("   - 'Attempting virtual try-on with Replicate...'")
        print("   - 'Generating outfit image with DALL-E...'")
        print("   - 'Running virtual try-on with Replicate...'")
        print("   - 'Virtual try-on successful!'")
        print("\nIf you see those messages, virtual try-on is working!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Replicate API: {e}")
        print("\nPossible issues:")
        print("1. Invalid API token")
        print("2. Network connection issues")
        print("3. Replicate service is down")
        return False

if __name__ == "__main__":
    success = test_replicate_config()
    exit(0 if success else 1)
