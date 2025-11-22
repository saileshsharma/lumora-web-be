#!/usr/bin/env python3
"""
Quick script to verify environment variables are loaded correctly
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("ENVIRONMENT VARIABLES CHECK")
print("=" * 60)

# Check which .env file is being loaded
env_file = os.path.join(os.getcwd(), '.env')
env_dev_file = os.path.join(os.getcwd(), '.env.dev')

print(f"\nChecking for .env files:")
print(f"  .env exists: {os.path.exists(env_file)}")
print(f"  .env.dev exists: {os.path.exists(env_dev_file)}")
print(f"\nload_dotenv() loads .env by default\n")

# Check required environment variables
required_vars = {
    'OPENAI_API_KEY': 'OpenAI API Key',
    'FAL_API_KEY': 'FAL API Key',
    'NANOBANANA_API_KEY': 'NanoBanana API Key',
}

optional_vars = {
    'FLASK_ENV': 'Flask Environment',
    'FLASK_DEBUG': 'Flask Debug Mode',
    'PORT': 'Server Port',
}

print("Required Variables:")
print("-" * 60)
all_present = True
for var_name, var_desc in required_vars.items():
    value = os.getenv(var_name)
    if value:
        # Show only first 20 chars for security
        masked_value = value[:20] + "..." if len(value) > 20 else value
        print(f"  ✅ {var_desc:25} : {masked_value}")
    else:
        print(f"  ❌ {var_desc:25} : NOT SET")
        all_present = False

print("\nOptional Variables:")
print("-" * 60)
for var_name, var_desc in optional_vars.items():
    value = os.getenv(var_name)
    if value:
        print(f"  ✅ {var_desc:25} : {value}")
    else:
        print(f"  ⚠️  {var_desc:25} : Not set (using defaults)")

print("\n" + "=" * 60)
if all_present:
    print("✅ ALL REQUIRED ENVIRONMENT VARIABLES ARE SET")
else:
    print("❌ SOME REQUIRED ENVIRONMENT VARIABLES ARE MISSING")
print("=" * 60)
