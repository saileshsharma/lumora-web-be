"""
Simple script to test OpenAI API key configuration
"""
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

def test_api_key():
    """Test if OpenAI API key is configured and working"""
    
    # Check if API key exists
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in .env file")
        return False
    
    print(f"✓ API key found: {api_key[:20]}...")
    
    # Configure OpenAI
    openai.api_key = api_key
    
    # Test with a simple API call
    print("\n🔄 Testing API connection...")
    
    try:
        # Simple completion test
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'API key works!' in exactly 3 words."}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ SUCCESS! API Response: {result}")
        print("\n✓ OpenAI API key is valid and working!")
        print("✓ You can now start the Flask backend and use the application.")
        return True
        
    except openai.AuthenticationError:
        print("❌ ERROR: Invalid API key")
        print("Please check your API key at: https://platform.openai.com/api-keys")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI API Key Test")
    print("=" * 60)
    
    success = test_api_key()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Ready to run the application.")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Open frontend/index.html in your browser")
    else:
        print("❌ API key test failed. Please fix the issues above.")
    print("=" * 60)
