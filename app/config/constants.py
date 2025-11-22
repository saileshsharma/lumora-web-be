"""
Application Constants
"""

# Occasions
OCCASIONS = [
    'Casual',
    'Formal',
    'Business',
    'Party',
    'Wedding',
    'Date Night',
    'Gym',
    'Beach',
    'Travel',
    'Job Interview',
    'Casual Outing',
    'Formal Event',
    'Business Meeting',
    'Professional/Formal',
    'Wedding Guest',
    'Garden Party',
    'Beach/Resort',
    'Gym/Athletic',
    'Party/Club',
    'Halloween',
]

# Budget Ranges
BUDGET_RANGES = [
    'Under $50',
    '$50-$100',
    '$100-$200',
    '$200-$500',
    'Above $500',
    'No budget limit',
]

# Background Map for Image Generation
BACKGROUND_MAP = {
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

# Default background
DEFAULT_BACKGROUND = 'elegant neutral backdrop with natural lighting'

# Error Messages
ERROR_MESSAGES = {
    'NO_IMAGE': 'No image provided',
    'INVALID_IMAGE': 'Invalid image format',
    'IMAGE_TOO_LARGE': 'Image size exceeds maximum allowed size',
    'NO_OCCASION': 'No occasion specified',
    'INVALID_OCCASION': 'Invalid occasion',
    'MISSING_API_KEY': 'API key not configured',
    'OPENAI_ERROR': 'OpenAI API error',
    'FAL_ERROR': 'FAL API error',
    'NANOBANANA_ERROR': 'NanoBanana API error',
    'INTERNAL_ERROR': 'Internal server error',
}

# Success Messages
SUCCESS_MESSAGES = {
    'OUTFIT_RATED': 'Outfit rated successfully',
    'OUTFIT_GENERATED': 'Outfit generated successfully',
    'SUBMISSION_CREATED': 'Submission created successfully',
}
