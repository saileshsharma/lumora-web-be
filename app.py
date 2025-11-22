from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError
import os
import json
import base64
import traceback
from io import BytesIO
from PIL import Image
import openai
import requests
from dotenv import load_dotenv
import fal_client
import logging
from datetime import datetime
import fashion_arena
import style_squad
import auth_system
from auth_endpoints import auth_bp

# Import Keycloak authentication
try:
    import keycloak_auth
    KEYCLOAK_AVAILABLE = True
except ImportError:
    KEYCLOAK_AVAILABLE = False
    app_logger.warning("Keycloak authentication module not available")

# Import security modules
from app.security_config import (
    configure_rate_limiter,
    configure_security_headers,
    validate_request_data,
    validate_admin_password,
    validate_image_data,
    RATE_LIMITS,
    OutfitRatingSchema,
    OutfitGenerationSchema,
    VirtualTryOnSchema,
    ArenaSubmissionSchema,
    ArenaVoteSchema,
    SquadCreateSchema,
    SquadJoinSchema,
    SquadOutfitSchema,
    SquadVoteSchema,
    SquadMessageSchema,
)

# Load environment variables
load_dotenv()

# Configure logging with separate log files
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Create log filenames with timestamp
date_str = datetime.now().strftime('%Y%m%d')
app_log = os.path.join(log_dir, f"application_{date_str}.log")
api_log = os.path.join(log_dir, f"api_calls_{date_str}.log")
error_log = os.path.join(log_dir, f"errors_{date_str}.log")

# Common log format
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Application Logger - General app flow, requests, responses
app_logger = logging.getLogger('application')
app_logger.setLevel(logging.INFO)
app_handler = logging.FileHandler(app_log)
app_handler.setFormatter(log_format)
app_logger.addHandler(app_handler)
# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
app_logger.addHandler(console_handler)

# API Logger - External API calls (OpenAI, NanobananaAPI, FAL)
api_logger = logging.getLogger('api')
api_logger.setLevel(logging.INFO)
api_handler = logging.FileHandler(api_log)
api_handler.setFormatter(log_format)
api_logger.addHandler(api_handler)

# Error Logger - Errors and exceptions
error_logger = logging.getLogger('errors')
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler(error_log)
error_handler.setFormatter(log_format)
error_logger.addHandler(error_handler)

# Default logger (for backward compatibility)
logger = app_logger

app = Flask(__name__)

# Configure CORS to allow requests from various origins
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://ai-outfit-assistant.vercel.app",
            "https://lumora.aihack.workers.dev",  # CloudFlare Workers deployment
            "http://localhost:5173",  # Vite dev server
            "http://localhost:5174",  # Vite dev server (new port)
            "http://localhost:3000",  # Alternative port
            "http://localhost:5001",  # Local backend
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5001",
            "https://lumora-web-production.up.railway.app",  # Production frontend
            "https://web-production-c70ba.up.railway.app",  # New backend URL
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

app_logger.info("="*60)
app_logger.info("OUTFIT ASSISTANT APPLICATION STARTED")
app_logger.info("="*60)
app_logger.info(f"Application Log: {app_log}")
app_logger.info(f"API Calls Log: {api_log}")
app_logger.info(f"Errors Log: {error_log}")
app_logger.info("="*60)

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.urandom(32).hex())
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 900  # 15 minutes
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 604800  # 7 days
jwt = JWTManager(app)

# JWT token blacklist checker
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return auth_system.is_token_blacklisted(jti)

# Helper function to get current user ID (optional authentication)
def get_current_user_id():
    """
    Get current user ID from JWT token if present
    Returns None if not authenticated (allows optional auth)
    """
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except:
        return None

app_logger.info("✓ JWT authentication configured")

# Initialize Keycloak if enabled
USE_KEYCLOAK = os.getenv('USE_KEYCLOAK', 'false').lower() == 'true'
if USE_KEYCLOAK and KEYCLOAK_AVAILABLE:
    keycloak_auth.init_keycloak()
    app_logger.info("✓ Keycloak authentication enabled")
else:
    app_logger.info("ℹ Using legacy JWT authentication")

# Configure rate limiting
limiter = configure_rate_limiter(app)
app_logger.info("✓ Rate limiting configured")

# Configure security headers
talisman = configure_security_headers(app)
app_logger.info("✓ Security headers configured")

# Register authentication blueprint
app.register_blueprint(auth_bp)
app_logger.info("✓ Authentication endpoints registered")

app_logger.info("="*60)
app_logger.info("SECURITY FEATURES ENABLED")
app_logger.info("="*60)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configure Fal AI
fal_key = os.getenv('FAL_API_KEY')
if fal_key:
    os.environ['FAL_KEY'] = fal_key


def encode_image_to_base64(image_data):
    """Convert image to base64 string for OpenAI API"""
    try:
        # If image_data is already base64, return it
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            return image_data
        
        # Otherwise, encode it
        image = Image.open(BytesIO(image_data))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def save_base64_to_temp_file(base64_data):
    """Save base64 image data to a temporary file and return the path"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_data)
        
        # Create temp file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_file.write(image_data)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        print(f"Error saving base64 to file: {e}")
        return None

def generate_outfit_image_with_replicate(person_image_base64, outfit_description, occasion, background_description):
    """
    Use NanobananaAPI to generate outfit visualization with face preservation
    """
    try:
        api_logger.info("="*60)
        api_logger.info("NANOBANANA API IMAGE GENERATION STARTED")
        api_logger.info("="*60)
        api_logger.info(f"Occasion: {occasion}")
        api_logger.info(f"Outfit: {outfit_description[:200]}...")
        api_logger.info(f"Background: {background_description}")
        
        nanobanana_api_key = os.getenv('NANOBANANA_API_KEY')
        if not nanobanana_api_key:
            raise Exception("NANOBANANA_API_KEY not configured")
        
        print("=" * 60)
        print("GENERATING IMAGE WITH NANOBANANA API")
        print("=" * 60)
        
        # Step 1: Upload person image to get public URL (using Fal CDN)
        person_image_path = save_base64_to_temp_file(person_image_base64)
        if not person_image_path:
            raise Exception("Failed to process person image")
        
        print(f"✓ Person image saved: {person_image_path}")
        api_logger.info(f"Person image saved: {person_image_path}")

        # Upload image to Fal CDN to get a public URL
        image_url = fal_client.upload_file(person_image_path)
        print(f"✓ Image uploaded to CDN: {image_url}")
        api_logger.info(f"Image uploaded to CDN: {image_url}")
        
        # Step 2: Create prompt for NanobananaAPI
        prompt = f"""Transform this person wearing {outfit_description}. 
Setting: {background_description}. 
Occasion: {occasion}. 
Keep the same person's face and features exactly as in the original image. Natural pose appropriate for {occasion}, facial expression matching the formality. 
Photorealistic, professional fashion photography, magazine quality, 3/4 body shot with professional studio lighting."""
        
        api_logger.info("-" * 60)
        api_logger.info("NANOBANANA API PROMPT:")
        api_logger.info(prompt)
        api_logger.info("-" * 60)

        # Step 3: Submit task to NanobananaAPI
        print(f"✓ Calling NanobananaAPI...")
        api_logger.info("Calling NanobananaAPI...")
        
        headers = {
            "Authorization": f"Bearer {nanobanana_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "type": "IMAGETOIAMGE",  # Image to Image editing
            "imageUrls": [image_url],
            "numImages": 1,
            "image_size": "3:4",  # Portrait format for fashion
            "callBackUrl": "https://webhook.site/dummy"  # Dummy callback, we'll poll instead
        }
        
        api_logger.info(f"Request payload: {payload}")
        
        try:
            response = requests.post(
                "https://api.nanobananaapi.ai/api/v1/nanobanana/generate",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                api_logger.error(f"❌ NanobananaAPI request FAILED: {response.status_code} - {response.text}")
                error_logger.error(f"NanobananaAPI request failed: {response.status_code} - {response.text}")
                raise Exception(f"NanobananaAPI request failed: {response.text}")

            api_logger.info("✅ NanobananaAPI request SUCCESSFUL")
        except requests.exceptions.RequestException as e:
            api_logger.error(f"❌ NanobananaAPI connection FAILED: {str(e)}")
            error_logger.error(f"NanobananaAPI connection error: {str(e)}")
            raise

        task_data = response.json()
        api_logger.info(f"Task submitted: {task_data}")
        
        if task_data.get('code') != 200:
            raise Exception(f"NanobananaAPI error: {task_data.get('msg')}")
        
        task_id = task_data['data']['taskId']
        print(f"✓ Task submitted: {task_id}")
        api_logger.info(f"Task ID: {task_id}")

        # Step 4: Poll for task completion
        print(f"✓ Waiting for image generation...")
        api_logger.info("Polling for task completion...")
        
        import time
        max_attempts = 60  # 60 attempts * 2 seconds = 2 minutes max
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(2)  # Wait 2 seconds between polls
            attempt += 1
            
            # Check task status
            status_response = requests.get(
                f"https://api.nanobananaapi.ai/api/v1/nanobanana/record-info?taskId={task_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                api_logger.warning(f"Status check failed: {status_response.status_code}")
                continue

            status_data = status_response.json()
            api_logger.info(f"Attempt {attempt}: Full response = {status_data}")

            if status_data.get('code') == 200:
                task_info = status_data.get('data', {})
                success_flag = task_info.get('successFlag')

                api_logger.info(f"Attempt {attempt}: successFlag = {success_flag}")

                if success_flag == 1:
                    # Task completed successfully
                    response_data = task_info.get('response', {})
                    generated_image_url = response_data.get('resultImageUrl')

                    if generated_image_url:
                        print(f"✓ Image generated successfully!")
                        api_logger.info(f"Generated image URL: {generated_image_url}")
                        break
                    else:
                        api_logger.warning(f"Success flag is 1 but no resultImageUrl found")
                elif success_flag is not None and success_flag != 0:
                    # If successFlag exists and is not 0 or 1, treat as error
                    error_msg = task_info.get('errorMessage', 'Unknown error')
                    raise Exception(f"Task failed: {error_msg}")
        else:
            raise Exception("Task timeout - image generation took too long")
        
        # Step 5: Download and optimize the generated image
        response = requests.get(generated_image_url)
        img = Image.open(BytesIO(response.content))
        api_logger.info(f"Image downloaded: {len(response.content)} bytes")
        
        # Resize if needed
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            print(f"✓ Image resized to: {img.size}")
        
        # Convert to RGB for JPEG
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Save as JPEG
        optimized_buffer = BytesIO()
        img.save(optimized_buffer, format='JPEG', quality=85, optimize=True)
        optimized_data = optimized_buffer.getvalue()
        
        print(f"✓ Image optimized: {len(response.content)} -> {len(optimized_data)} bytes")
        
        # Convert to base64
        image_base64 = base64.b64encode(optimized_data).decode()
        result_url = f"data:image/jpeg;base64,{image_base64}"
        
        # Cleanup
        try:
            os.unlink(person_image_path)
        except Exception as e:
            print(f"Warning: Could not delete temp file: {e}")
        
        print(f"✓ Base64 length: {len(image_base64)} chars")
        print("=" * 60)
        print("IMAGE GENERATION SUCCESSFUL!")
        print("=" * 60)

        api_logger.info(f"Image size: {len(optimized_data)} bytes")
        api_logger.info("✅ NANOBANANA IMAGE GENERATION SUCCESSFUL")
        api_logger.info("="*60)
        api_logger.info("IMAGE GENERATION COMPLETE")
        api_logger.info("="*60)

        return result_url

    except Exception as e:
        api_logger.error(f"❌ Error in NanobananaAPI generation: {e}")
        error_logger.error(f"NanobananaAPI generation failed: {e}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"Error in NanobananaAPI generation: {e}")
        traceback.print_exc()
        return None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Outfit Assistant API is running"})

@app.route('/api/rate-outfit', methods=['POST'])
@limiter.limit(RATE_LIMITS["ai_rating"])
def rate_outfit():
    """
    Rate an outfit based on uploaded photo, occasion, and budget
    """
    try:
        app_logger.info("="*60)
        app_logger.info("RATE OUTFIT REQUEST RECEIVED")
        app_logger.info("="*60)

        data = request.json

        # Validate input data
        try:
            validated_data = validate_request_data(OutfitRatingSchema, {
                'photo': data.get('image'),
                'occasion': data.get('occasion', 'casual')
            })
        except ValidationError as e:
            error_logger.error(f"Validation error: {e.messages}")
            return jsonify({"error": "Invalid input data", "details": e.messages}), 400

        # Extract parameters
        image_base64 = validated_data['photo']
        occasion = validated_data['occasion']
        budget = data.get('budget', '')

        # Additional image validation
        if not validate_image_data(image_base64):
            error_logger.error("Invalid image data format")
            return jsonify({"error": "Invalid image data"}), 400

        app_logger.info(f"Parameters - Occasion: {occasion}, Budget: {budget}")

        if not image_base64:
            error_logger.error("No image provided in request")
            return jsonify({"error": "No image provided"}), 400
        
        # Build the prompt for GPT-4 Vision
        budget_text = f" with a budget of {budget}" if budget else ""
        
        prompt = f"""Analyze this outfit for a {occasion}{budget_text}.

Please provide:
1. Wow Factor Score (1-10): Rate the overall visual impact and style
2. Occasion Fitness Score (1-10): How appropriate is this for {occasion}?
3. Overall Rating (1-10): Combined assessment

Then provide detailed feedback including:
- Strengths of the outfit
- Areas for improvement
- Specific suggestions for colors, fit, accessories
- 3-5 shopping recommendations with descriptions
- A humorous "roast" - brutally honest, witty, and playful criticism about the outfit (2-3 sentences, make it funny but not mean-spirited)

Format your response as JSON with this structure:
{{
  "wow_factor": <number>,
  "occasion_fitness": <number>,
  "overall_rating": <number>,
  "wow_factor_explanation": "<brief explanation>",
  "occasion_fitness_explanation": "<brief explanation>",
  "overall_explanation": "<brief explanation>",
  "strengths": ["<strength1>", "<strength2>", ...],
  "improvements": ["<improvement1>", "<improvement2>", ...],
  "suggestions": ["<suggestion1>", "<suggestion2>", ...],
  "roast": "<humorous witty roast of the outfit>",
  "shopping_recommendations": [
    {{
      "item": "<item name>",
      "description": "<description>",
      "price": "<estimated price>",
      "reason": "<why this would enhance the outfit>"
    }}
  ]
}}"""
        
        # Call OpenAI GPT-4 Vision API
        api_logger.info("Calling GPT-4 Vision API for outfit rating...")
        api_logger.info(f"  Model: gpt-4o")
        api_logger.info(f"  Max tokens: 1500")

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_base64
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            api_logger.info("✅ GPT-4 Vision API call SUCCESSFUL")
            api_logger.info(f"  Tokens used: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")
        except Exception as e:
            api_logger.error(f"❌ GPT-4 Vision API call FAILED: {str(e)}")
            error_logger.error(f"GPT-4 Vision API Error in rate_outfit: {str(e)}")
            raise

        # Parse the response
        result = response.choices[0].message.content
        app_logger.info("Rating analysis completed successfully")

        return jsonify({"success": True, "data": result})

    except Exception as e:
        error_logger.error(f"Error in rate_outfit: {str(e)}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-outfit', methods=['POST'])
@limiter.limit(RATE_LIMITS["ai_generation"])
def generate_outfit():
    """
    Generate outfit suggestions based on user preferences with realistic person image
    """
    try:
        app_logger.info("="*60)
        app_logger.info("GENERATE OUTFIT REQUEST RECEIVED")
        app_logger.info("="*60)

        data = request.json

        # Validate input data
        try:
            validated_data = validate_request_data(OutfitGenerationSchema, {
                'occasion': data.get('occasion', 'casual'),
                'style': data.get('style', ''),
                'preferences': data.get('conditions', '')
            })
        except ValidationError as e:
            error_logger.error(f"Validation error: {e.messages}")
            return jsonify({"error": "Invalid input data", "details": e.messages}), 400

        # Extract parameters
        user_image = data.get('user_image', None)
        wow_factor = data.get('wow_factor', 5)
        brands = data.get('brands', [])
        budget = data.get('budget', '')
        occasion = validated_data['occasion']
        conditions = validated_data.get('preferences', '')

        app_logger.info(f"Parameters:")
        app_logger.info(f"  - Occasion: {occasion}")
        app_logger.info(f"  - Wow Factor: {wow_factor}")
        app_logger.info(f"  - Brands: {brands}")
        app_logger.info(f"  - Budget: {budget}")
        app_logger.info(f"  - Conditions: {conditions}")
        app_logger.info(f"  - User image provided: {user_image is not None}")
        
        # Build the style description based on wow factor
        if wow_factor <= 3:
            style_desc = "classic, safe, and timeless"
        elif wow_factor <= 6:
            style_desc = "balanced, stylish, and modern"
        else:
            style_desc = "bold, creative, and fashion-forward"
        
        # Build brand preference text
        brand_text = f" from brands like {', '.join(brands)}" if brands else ""
        budget_text = f" within a budget of {budget}" if budget else ""
        conditions_text = f" Additional requirements: {conditions}." if conditions else ""
        
        # Step 1: Generate outfit description using GPT-4
        description_prompt = f"""Create a detailed outfit recommendation for {occasion}.

Style level: {wow_factor}/10 ({style_desc})
Preferences:{brand_text}{budget_text}
{conditions_text}

Provide:
1. Complete outfit description (top, bottom, shoes, accessories)
2. Color palette and why it works
3. Style notes and occasion appropriateness
4. 5-8 specific product recommendations with:
   - Item type and description
   - Estimated price
   - Why it fits the outfit
   
Format as JSON:
{{
  "outfit_concept": "<overall concept and inspiration>",
  "items": [
    {{
      "type": "<item type>",
      "description": "<detailed description>",
      "color": "<color>",
      "style_notes": "<why this works>"
    }}
  ],
  "color_palette": "<description of colors and why they work>",
  "occasion_notes": "<why this works for the occasion>",
  "product_recommendations": [
    {{
      "item": "<item name>",
      "type": "<clothing type>",
      "brand": "<suggested brand>",
      "description": "<description>",
      "price": "<estimated price>",
      "reason": "<why recommended>"
    }}
  ]
}}"""
        
        app_logger.info("-" * 60)
        app_logger.info("GPT-4 OUTFIT DESCRIPTION PROMPT:")
        app_logger.info(description_prompt)
        app_logger.info("-" * 60)
        
        messages = [{"role": "user", "content": description_prompt}]
        
        # If user provided image, include it for context
        if user_image:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": description_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": user_image}
                        }
                    ]
                }
            ]
        
        api_logger.info("Calling GPT-4 API for outfit description...")
        api_logger.info(f"  Model: gpt-4o")
        api_logger.info(f"  Max tokens: 1500")

        try:
            description_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            api_logger.info("✅ GPT-4 API call SUCCESSFUL")
            api_logger.info(f"  Tokens used: {description_response.usage.total_tokens if hasattr(description_response, 'usage') else 'N/A'}")
        except Exception as e:
            api_logger.error(f"❌ GPT-4 API call FAILED: {str(e)}")
            error_logger.error(f"GPT-4 API Error in generate_outfit: {str(e)}")
            raise

        outfit_description = description_response.choices[0].message.content
        app_logger.info("GPT-4 Response received and extracted")
        app_logger.info(f"Outfit Description (first 500 chars): {outfit_description[:500]}...")

        # Parse JSON response safely
        try:
            outfit_data = json.loads(outfit_description)
        except json.JSONDecodeError as e:
            error_logger.error(f"Failed to parse GPT-4 JSON response: {e}")
            error_logger.error(f"Response content: {outfit_description}")
            raise ValueError(f"Invalid JSON response from GPT-4: {str(e)}")
        
        # Build detailed outfit description for image generation
        outfit_details = " ".join([f"{item['description']} in {item['color']}" for item in outfit_data.get('items', [])])
        
        # Step 3: Determine appropriate background based on occasion
        background_map = {
            'Job Interview': 'professional office lobby with modern corporate interior',
            'Casual Outing': 'trendy urban street with stylish storefronts and natural daylight',
            'Formal Event': 'elegant ballroom with chandeliers and sophisticated ambiance',
            'Date Night': 'upscale restaurant interior with romantic lighting',
            'Business Meeting': 'contemporary conference room with glass walls',
            'Professional/Formal': 'elegant professional setting with modern corporate interior or sophisticated ballroom ambiance',
            'Wedding Guest': 'beautiful outdoor garden venue with floral decorations',
            'Garden Party': 'elegant outdoor garden party setting with lush greenery, flowers, and natural daylight',
            'Beach/Resort': 'pristine sandy beach with turquoise ocean water and tropical scenery',
            'Gym/Athletic': 'modern fitness center or outdoor athletic track',
            'Party/Club': 'stylish nightclub interior with ambient lighting',
            'Halloween': 'festive Halloween party setting with atmospheric decorations',
            'Travel': 'airport terminal or scenic travel destination'
        }

        # Get background or use neutral elegant backdrop as fallback
        background = background_map.get(occasion, 'elegant neutral backdrop with natural lighting')
        
        app_logger.info(f"Background selected: {background}")
        app_logger.info(f"Outfit details for image: {outfit_details}")
        
        # Step 4: Generate realistic outfit image using NanobananaAPI
        # Verify prerequisites
        if not user_image:
            raise ValueError("No user image provided. Image generation requires a user photo.")
        
        nanobanana_api_key = os.getenv('NANOBANANA_API_KEY')
        if not nanobanana_api_key:
            raise ValueError("NANOBANANA_API_KEY not configured. Please add it to your .env file.")
        
        # Call NanobananaAPI image generation
        image_url = generate_outfit_image_with_replicate(
            user_image, 
            outfit_details,
            occasion,
            background
        )
        
        if not image_url:
            raise Exception("NanobananaAPI generation returned None. Check logs above for specific error.")

        # Format response to match frontend expectations
        result_data = json.dumps({
            "success": True,
            "outfit_description": outfit_description,
            "outfit_image_url": image_url
        })

        return jsonify({
            "success": True,
            "data": result_data
        })
        
    except Exception as e:
        error_logger.error(f"Error in generate_outfit: {str(e)}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/regenerate-outfit', methods=['POST'])
def regenerate_outfit():
    """
    Regenerate outfit with user feedback
    """
    try:
        data = request.json
        
        # Extract parameters including feedback
        feedback = data.get('feedback', {})
        previous_params = data.get('previous_params', {})
        
        # Call generate_outfit with adjusted parameters based on feedback
        # For MVP, we'll just call generate_outfit again
        return generate_outfit()
        
    except Exception as e:
        print(f"Error in regenerate_outfit: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# FASHION ARENA ENDPOINTS
# ============================================================================

@app.route('/api/arena/submit', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def submit_to_arena():
    """
    Submit a photo to Fashion Arena
    """
    try:
        app_logger.info("="*60)
        app_logger.info("FASHION ARENA SUBMISSION REQUEST")
        app_logger.info("="*60)
        
        data = request.json
        
        # Extract parameters
        photo = data.get('photo')
        title = data.get('title', 'Untitled')
        description = data.get('description', '')
        occasion = data.get('occasion', 'General')
        source_mode = data.get('source_mode', 'unknown')
        user_id = data.get('user_id')
        
        if not photo:
            return jsonify({"error": "No photo provided"}), 400

        # Validate photo data - reject local file paths
        if photo.startswith("file://"):
            app_logger.warning(f"Rejected submission with local file path")
            return jsonify({"error": "Invalid photo data. Please use base64-encoded image data."}), 400

        app_logger.info(f"Submission - Title: {title}, Occasion: {occasion}, Source: {source_mode}")

        # Submit to Fashion Arena
        submission = fashion_arena.submit_to_arena(
            photo_data=photo,
            title=title,
            description=description,
            occasion=occasion,
            source_mode=source_mode,
            user_id=user_id
        )
        
        app_logger.info(f"Submission successful - ID: {submission['id']}")
        
        return jsonify({
            "success": True,
            "submission": submission
        })
        
    except Exception as e:
        app_logger.error(f"Error in submit_to_arena: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/submissions', methods=['GET'])
@limiter.limit(RATE_LIMITS["api_read"])
def get_arena_submissions():
    """
    Get all Fashion Arena submissions
    """
    try:
        sort_by = request.args.get('sort_by', 'recent')
        submissions = fashion_arena.get_all_submissions(sort_by=sort_by)

        # Transform field names to match frontend expectations
        for sub in submissions:
            # Map average_rating to avg_rating
            if 'average_rating' in sub:
                sub['avg_rating'] = sub.pop('average_rating')
            # Map total_votes to votes (if needed)
            if 'total_votes' in sub:
                sub['votes'] = sub['total_votes']
            # Ensure likes field exists (default to total_votes if not present)
            if 'likes' not in sub:
                sub['likes'] = sub.get('votes', 0)

            if 'photo' in sub:
                # Keep only first 100 chars of base64 for preview indicator
                sub['has_photo'] = bool(sub['photo'])
                # Don't remove photo completely for now, client needs it
                # sub.pop('photo')

        return jsonify({
            "success": True,
            "submissions": submissions,
            "total": len(submissions)
        })

    except Exception as e:
        app_logger.error(f"Error in get_arena_submissions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/leaderboard', methods=['GET'])
def get_arena_leaderboard():
    """
    Get Fashion Arena leaderboard (top 10)
    """
    try:
        limit = int(request.args.get('limit', 10))
        leaderboard = fashion_arena.get_leaderboard(limit=limit)

        # Transform field names to match frontend expectations
        for entry in leaderboard:
            # Map average_rating to avg_rating
            if 'average_rating' in entry:
                entry['avg_rating'] = entry.pop('average_rating')
            # Map total_votes to votes
            if 'total_votes' in entry:
                entry['votes'] = entry['total_votes']
            # Ensure likes field exists
            if 'likes' not in entry:
                entry['likes'] = entry.get('votes', 0)

        return jsonify({
            "success": True,
            "leaderboard": leaderboard
        })

    except Exception as e:
        app_logger.error(f"Error in get_arena_leaderboard: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/vote', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def vote_on_submission():
    """
    Vote on a Fashion Arena submission
    """
    try:
        data = request.json
        
        submission_id = data.get('submission_id')
        vote_type = data.get('vote_type', 'upvote')  # 'upvote' or 'downvote'
        rating = data.get('rating', 5)  # 1-10
        voter_id = data.get('voter_id')
        
        if not submission_id:
            return jsonify({"error": "No submission_id provided"}), 400
        
        if vote_type not in ['upvote', 'downvote']:
            return jsonify({"error": "Invalid vote_type. Must be 'upvote' or 'downvote'"}), 400
        
        if not (1 <= rating <= 10):
            return jsonify({"error": "Rating must be between 1 and 10"}), 400
        
        app_logger.info(f"Vote received - Submission: {submission_id}, Type: {vote_type}, Rating: {rating}")
        
        # Submit vote
        updated_submission = fashion_arena.vote_submission(
            submission_id=submission_id,
            vote_type=vote_type,
            rating=rating,
            voter_id=voter_id
        )
        
        if not updated_submission:
            return jsonify({"error": "Submission not found"}), 404
        
        return jsonify({
            "success": True,
            "submission": updated_submission
        })
        
    except Exception as e:
        app_logger.error(f"Error in vote_on_submission: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/submission/<submission_id>', methods=['GET'])
def get_submission_details(submission_id):
    """
    Get details of a specific submission
    """
    try:
        submission = fashion_arena.get_submission_by_id(submission_id)
        
        if not submission:
            return jsonify({"error": "Submission not found"}), 404
        
        return jsonify({
            "success": True,
            "submission": submission
        })
        
    except Exception as e:
        app_logger.error(f"Error in get_submission_details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/stats', methods=['GET'])
def get_arena_stats():
    """
    Get Fashion Arena statistics
    """
    try:
        stats = fashion_arena.get_stats()

        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        app_logger.error(f"Error in get_arena_stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/restore', methods=['POST'])
def restore_arena_data():
    """
    Restore Fashion Arena data from backup
    """
    try:
        app_logger.info("="*60)
        app_logger.info("FASHION ARENA DATA RESTORE REQUEST")
        app_logger.info("="*60)

        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        app_logger.info(f"Restoring data...")

        # Restore data
        count = fashion_arena.restore_data(data)

        app_logger.info(f"Successfully restored {count} submissions")

        return jsonify({
            "success": True,
            "message": f"Successfully restored {count} submissions",
            "count": count
        })

    except Exception as e:
        app_logger.error(f"Error in restore_arena_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/like', methods=['POST'])
def like_submission():
    """
    Like a Fashion Arena submission (simple increment)
    """
    try:
        data = request.json

        submission_id = data.get('submission_id')

        if not submission_id:
            return jsonify({"error": "No submission_id provided"}), 400

        app_logger.info(f"Like received - Submission: {submission_id}")

        # Like submission
        updated_submission = fashion_arena.like_submission(submission_id)

        if not updated_submission:
            return jsonify({"error": "Submission not found"}), 404

        return jsonify({
            "success": True,
            "submission": updated_submission
        })

    except Exception as e:
        app_logger.error(f"Error in like_submission: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/cleanup', methods=['POST'])
def cleanup_invalid_submissions():
    """
    Clean up submissions with invalid photo data (local file paths)
    """
    try:
        app_logger.info("="*60)
        app_logger.info("FASHION ARENA CLEANUP REQUEST")
        app_logger.info("="*60)

        # Cleanup invalid submissions
        result = fashion_arena.cleanup_invalid_submissions()

        app_logger.info(f"Cleanup complete - Removed {result['removed_count']} invalid submissions")

        return jsonify({
            "success": True,
            "message": f"Removed {result['removed_count']} submissions with invalid photo data",
            "result": result
        })

    except Exception as e:
        app_logger.error(f"Error in cleanup_invalid_submissions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arena/submission/<submission_id>', methods=['DELETE'])
@limiter.limit(RATE_LIMITS["admin"])
def delete_submission(submission_id):
    """
    Delete a submission (admin password protected)
    """
    try:
        data = request.json
        password = data.get('password')

        # Validate admin password from environment variable
        try:
            if not validate_admin_password(password):
                error_logger.warning(f"Failed admin authentication attempt for deletion of {submission_id}")
                return jsonify({"error": "Incorrect password"}), 403
        except ValueError as e:
            error_logger.error(f"Admin password validation error: {e}")
            return jsonify({"error": "Server configuration error"}), 500

        app_logger.info(f"✓ Admin authenticated - Delete request for submission: {submission_id}")

        # Delete submission
        success = fashion_arena.delete_submission(submission_id)

        if not success:
            return jsonify({"error": "Submission not found"}), 404

        app_logger.info(f"✓ Submission {submission_id} deleted successfully")

        return jsonify({
            "success": True,
            "message": "Submission deleted successfully"
        })

    except Exception as e:
        app_logger.error(f"Error in delete_submission: {e}")
        return jsonify({"error": str(e)}), 500

# Serve React frontend static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the React frontend"""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')

    # If the path is a file that exists, serve it
    if path and os.path.exists(os.path.join(frontend_dir, path)):
        return send_from_directory(frontend_dir, path)

    # Otherwise, serve index.html (for client-side routing)
    return send_from_directory(frontend_dir, 'index.html')

# ============================================================================
# STYLE SQUAD API ENDPOINTS
# ============================================================================

@app.route('/api/squad/create', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def create_style_squad():
    """Create a new Style Squad"""
    try:
        data = request.json
        squad = style_squad.create_squad(
            name=data['name'],
            description=data.get('description'),
            user_id=data['userId'],
            user_name=data['userName'],
            max_members=data.get('maxMembers', 10)
        )
        return jsonify(squad), 201
    except Exception as e:
        api_logger.error(f"Error creating squad: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/join', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def join_style_squad():
    """Join a Squad using invite code"""
    try:
        data = request.json
        squad = style_squad.join_squad(
            invite_code=data['inviteCode'],
            user_id=data['userId'],
            user_name=data['userName']
        )

        if squad:
            return jsonify(squad), 200
        else:
            return jsonify({'error': 'Invalid invite code'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        api_logger.error(f"Error joining squad: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/<squad_id>', methods=['GET'])
def get_style_squad(squad_id):
    """Get squad details"""
    try:
        squad = style_squad.get_squad(squad_id)
        if squad:
            return jsonify(squad), 200
        else:
            return jsonify({'error': 'Squad not found'}), 404
    except Exception as e:
        api_logger.error(f"Error getting squad: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/user/<user_id>', methods=['GET'])
def get_user_style_squads(user_id):
    """Get all squads for a user"""
    try:
        squads = style_squad.get_user_squads(user_id)
        return jsonify(squads), 200
    except Exception as e:
        api_logger.error(f"Error getting user squads: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/<squad_id>/leave', methods=['POST'])
def leave_style_squad(squad_id):
    """Leave a squad"""
    try:
        data = request.json
        success = style_squad.leave_squad(squad_id, data['userId'])
        if success:
            return jsonify({'message': 'Left squad successfully'}), 200
        else:
            return jsonify({'error': 'Squad not found'}), 404
    except Exception as e:
        api_logger.error(f"Error leaving squad: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/<squad_id>/outfit', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def share_squad_outfit(squad_id):
    """Share an outfit to squad for feedback"""
    try:
        data = request.json
        outfit = style_squad.share_outfit(
            squad_id=squad_id,
            user_id=data['userId'],
            user_name=data['userName'],
            photo=data['photo'],
            occasion=data['occasion'],
            question=data.get('question')
        )

        if outfit:
            return jsonify(outfit), 201
        else:
            return jsonify({'error': 'Squad not found'}), 404
    except Exception as e:
        api_logger.error(f"Error sharing outfit: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/outfit/<outfit_id>/vote', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def vote_squad_outfit(outfit_id):
    """Vote on a squad outfit"""
    try:
        data = request.json
        success = style_squad.vote_on_outfit(
            outfit_id=outfit_id,
            user_id=data['userId'],
            user_name=data['userName'],
            vote_type=data['voteType'],
            comment=data.get('comment')
        )

        if success:
            return jsonify({'message': 'Vote recorded'}), 200
        else:
            return jsonify({'error': 'Outfit not found'}), 404
    except Exception as e:
        api_logger.error(f"Error voting on outfit: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/outfit/<outfit_id>/message', methods=['POST'])
@limiter.limit(RATE_LIMITS["user_action"])
def send_squad_message(outfit_id):
    """Send a message on squad outfit"""
    try:
        data = request.json
        success = style_squad.send_message(
            outfit_id=outfit_id,
            user_id=data['userId'],
            user_name=data['userName'],
            message=data['message']
        )

        if success:
            return jsonify({'message': 'Message sent'}), 200
        else:
            return jsonify({'error': 'Outfit not found'}), 404
    except Exception as e:
        api_logger.error(f"Error sending message: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/<squad_id>/outfits', methods=['GET'])
def get_squad_outfits_route(squad_id):
    """Get recent outfits from squad"""
    try:
        limit = request.args.get('limit', 20, type=int)
        outfits = style_squad.get_squad_outfits(squad_id, limit)
        return jsonify(outfits), 200
    except Exception as e:
        api_logger.error(f"Error getting squad outfits: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/squad/<squad_id>/delete', methods=['DELETE'])
def delete_style_squad(squad_id):
    """Delete a squad (creator only)"""
    try:
        data = request.json
        success = style_squad.delete_squad(squad_id, data['userId'])

        if success:
            return jsonify({'message': 'Squad deleted'}), 200
        else:
            return jsonify({'error': 'Squad not found or unauthorized'}), 404
    except Exception as e:
        api_logger.error(f"Error deleting squad: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check if API key is configured
    if not os.getenv('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with your OpenAI API key")

    # Use Railway's PORT environment variable, fallback to 5001 for local development
    # (5000 is often used by macOS AirPlay Receiver)
    port = int(os.getenv('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
