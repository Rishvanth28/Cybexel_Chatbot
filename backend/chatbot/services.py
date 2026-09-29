import json
import re
from groq import Groq
from django.conf import settings

# Category synonyms mapping for fallback and validation
CATEGORY_SYNONYMS = {
    'hotel': 'Hotel',
    'hotels': 'Hotel',
    'restaurant': 'Restaurant',
    'restaurants': 'Restaurant',
    'hospital': 'Hospital',
    'hospitals': 'Hospital',
    'dentist': 'Hospital',
    'clinic': 'Hospital',
    'beauty salon': 'Beauty Salon',
    'salon': 'Beauty Salon',
    'salons': 'Beauty Salon',
    'supermarket': 'Supermarket',
    'supermarkets': 'Supermarket',
    'textile': 'Textiles',
    'textiles': 'Textiles',
    'saree': 'Textiles',
    'saree shop': 'Textiles',
    'automobile': 'Automobile Service',
    'automobile service': 'Automobile Service',
    'car service': 'Automobile Service',
    'bike service': 'Automobile Service',
    'car service center': 'Automobile Service',
    'gym': 'Gym',
    'gyms': 'Gym',
    'electronics': 'Electronics',
    'electronics store': 'Electronics',
    'education': 'Education',
    'computer institute': 'Education',
    'training centre': 'Education',
    'training center': 'Education',
    'real estate': 'Real Estate',
    'property consultant': 'Real Estate',
    'property': 'Real Estate',
    # Extended synonyms for better natural language understanding
    'cafe': 'Restaurant',
    'coffee shop': 'Restaurant',
    'coffee': 'Restaurant',
    'eatery': 'Restaurant',
    'dining': 'Restaurant',
    'food': 'Restaurant',
    'eat': 'Restaurant',
    'meal': 'Restaurant',
    'accommodation': 'Hotel',
    'stay': 'Hotel',
    'lodging': 'Hotel',
    'resort': 'Hotel',
    'inn': 'Hotel',
    'motel': 'Hotel',
    'guest house': 'Hotel',
    'spa': 'Beauty Salon',
    'parlor': 'Beauty Salon',
    'parlour': 'Beauty Salon',
    'barber': 'Beauty Salon',
    'salon': 'Beauty Salon',
    'grocery': 'Supermarket',
    'provision': 'Supermarket',
    'mart': 'Supermarket',
    'departmental store': 'Supermarket',
    'saree shop': 'Textiles',
    'silk': 'Textiles',
    'cloth': 'Textiles',
    'fabric': 'Textiles',
    'boutique': 'Textiles',
    'garage': 'Automobile Service',
    'mechanic': 'Automobile Service',
    'fitness': 'Gym',
    'fitness center': 'Gym',
    'health club': 'Gym',
    'workout': 'Gym',
    'mobile': 'Electronics',
    'phone': 'Electronics',
    'computer': 'Electronics',
    'laptop': 'Electronics',
    'school': 'Education',
    'college': 'Education',
    'academy': 'Education',
    'coaching': 'Education',
    'tution': 'Education',
    'tuition': 'Education',
    'flat': 'Real Estate',
    'apartment': 'Real Estate',
    'house': 'Real Estate',
    'villa': 'Real Estate',
    'plot': 'Real Estate',
    'land': 'Real Estate',
    'pharmacy': 'Hospital',
    'medical': 'Hospital',
    'doctor': 'Hospital',
    'nursing home': 'Hospital',
}

VALID_CATEGORIES = [
    'Hotel', 'Restaurant', 'Hospital', 'Beauty Salon', 'Supermarket',
    'Textiles', 'Automobile Service', 'Gym', 'Electronics', 'Education', 'Real Estate'
]

# Known Coimbatore areas with approximate coordinates
COIMBATORE_AREAS = {
    'gandhipuram': (11.0168, 76.9558),
    'rs puram': (11.0098, 76.9464),
    'peelamedu': (11.0230, 77.0050),
    'saravanampatti': (11.0750, 76.9750),
    'town hall': (10.9935, 76.9592),
    'ukkadam': (10.9936, 76.9592),
    'kuniyamuthur': (10.9635, 76.9507),
    'saibaba colony': (11.0080, 76.9650),
    'vellalore': (11.0100, 76.9700),
    'coimbatore': (11.0168, 76.9558),
    'chennai airport': (12.9941, 80.1709),
    'airport': (12.9941, 80.1709),
    'chennai': (13.0827, 80.2707),
}

# Default result count when user doesn't specify
DEFAULT_RESULT_COUNT = 5
MAX_RESULT_COUNT = 20


def extract_intent_with_groq(query, conversation_context=None):
    """
    Use Groq LLM to understand user intent and extract structured search parameters.
    
    Returns a dict with:
    - intent: business_search | general_question | follow_up | greeting | help
    - business_type: category name or None
    - location: area name or None
    - nearby: bool
    - result_count: int or None
    - filters: dict of additional filters
    - sort_by: relevance | distance | rating | price
    - original_query: the user's original query
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    # Build conversation context string
    context_str = ""
    if conversation_context and len(conversation_context) > 0:
        context_str = "\n\nConversation context (previous messages):\n"
        for msg in conversation_context[-6:]:  # Last 6 messages for context
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            context_str += f"{role}: {content}\n"

    prompt = f"""You are an intelligent search intent analyzer for a local business discovery chatbot focused on Coimbatore, India.

Given the user query: "{query}"
{context_str}
Analyze the user's intent and extract the following information. Respond with ONLY valid JSON (no markdown, no explanation):

{{
    "intent": "<one of: business_search, general_question, follow_up, greeting, help>",
    "business_type": "<one of: Hotel, Restaurant, Hospital, Beauty Salon, Supermarket, Textiles, Automobile Service, Gym, Electronics, Education, Real Estate, or null>",
    "location": "<the area/location name, or 'current_location' if user says 'near me'/'nearby', or null>",
    "nearby": <true if user wants proximity-based results>,
    "result_count": <number of results requested: 1, 2, 3, 5, 10, or null for default>,
    "filters": {{}},
    "sort_by": "<one of: relevance, distance, rating, price>",
    "explanation": "<brief explanation of your understanding>"
}}

IMPORTANT RULES:
1. Intent classification:
   - "business_search": User wants to find businesses (hotels, restaurants, etc.)
   - "general_question": User asks a general knowledge question (weather, capital of France, etc.)
   - "follow_up": User refers to previous results ("show me only one", "which one is closest", "tell me more about it")
   - "greeting": User says hello, hi, hey, etc.
   - "help": User asks what the bot can do

2. Business type mapping (be flexible with natural language):
   - "somewhere to stay", "accommodation", "lodging" → Hotel
   - "places to eat", "food", "dining", "coffee", "cafe" → Restaurant
   - "doctor", "medical", "pharmacy", "clinic" → Hospital
   - "salon", "spa", "parlor", "barber" → Beauty Salon
   - "grocery", "provision store", "mart" → Supermarket
   - "saree shop", "silk", "cloth store", "boutique" → Textiles
   - "garage", "mechanic", "car service" → Automobile Service
   - "fitness", "workout", "health club" → Gym
   - "mobile shop", "computer store", "electronics" → Electronics
   - "school", "college", "coaching", "tuition" → Education
   - "flat", "apartment", "property", "plot" → Real Estate

3. Location extraction:
   - "near me", "nearby", "close to me", "around here" → "current_location"
   - Specific areas: Gandhipuram, RS Puram, Peelamedu, Saravanampatti, Town Hall, Ukkadam, etc.
   - "Chennai airport", "airport" → "Chennai Airport"
   - If no location mentioned, set to null

4. Result count extraction:
   - "one", "just one", "only one", "1" → 1
   - "two", "2" → 2
   - "three", "3" → 3
   - "a few", "some" → 5 (default)
   - "all", "every" → 20 (max)
   - If not specified, set to null (use default)

5. Follow-up detection:
   - "show me only one", "just one", "which one is closest" → follow_up
   - "tell me about it", "more details" → follow_up
   - Use conversation context to understand what "it" or "one" refers to

6. General questions (NOT business searches):
   - "What is the capital of France?" → general_question
   - "What's the weather?" → general_question
   - "Tell me about Chennai" → general_question
   - "Tell me something about Chennai" → general_question
   - "Who are you?" → general_question
   - "What is the population of India?" → general_question
   - Any question that does NOT contain business-related keywords → general_question

7. Result count extraction:
   - "one", "just one", "only one", "1", "a", "an", "single" → 1
   - "two", "2" → 2
   - "three", "3" → 3
   - "four", "4" → 4
   - "five", "5" → 5
   - "ten", "10" → 10
   - "a few", "some" → 5 (default)
   - "all", "every" → 20 (max)
   - If not specified, set to null (use default)

8. Sorting:
   - "closest", "nearest" → distance
   - "best", "top rated", "highest rated" → rating
   - "cheap", "affordable", "budget" → price
   - Default → relevance

Respond with ONLY the JSON object, nothing else."""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        result = response.choices[0].message.content.strip()

        # Clean up the response - remove markdown code blocks if present
        result = re.sub(r'^```json\s*', '', result)
        result = re.sub(r'^```\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
        result = result.strip()

        parsed = json.loads(result)

        # Validate and normalize
        business_type = parsed.get('business_type', None)
        if business_type and business_type not in VALID_CATEGORIES:
            # Try to match with synonyms
            bt_lower = business_type.lower()
            business_type = CATEGORY_SYNONYMS.get(bt_lower, None)

        location = parsed.get('location', None)
        if location:
            location = location.strip()
            if location.lower() in ['null', 'none', '']:
                location = None

        nearby = parsed.get('nearby', False)
        if not isinstance(nearby, bool):
            nearby = bool(nearby)

        result_count = parsed.get('result_count', None)
        if result_count is not None:
            try:
                result_count = int(result_count)
                if result_count < 1:
                    result_count = 1
                elif result_count > MAX_RESULT_COUNT:
                    result_count = MAX_RESULT_COUNT
            except (ValueError, TypeError):
                result_count = None

        intent = parsed.get('intent', 'business_search')
        if intent not in ['business_search', 'general_question', 'follow_up', 'greeting', 'help']:
            intent = 'business_search'

        sort_by = parsed.get('sort_by', 'relevance')
        if sort_by not in ['relevance', 'distance', 'rating', 'price']:
            sort_by = 'relevance'

        filters = parsed.get('filters', {})
        if not isinstance(filters, dict):
            filters = {}

        return {
            'intent': intent,
            'business_type': business_type,
            'location': location,
            'nearby': nearby,
            'result_count': result_count,
            'filters': filters,
            'sort_by': sort_by,
            'explanation': parsed.get('explanation', ''),
            'original_query': query,
        }
    except Exception as e:
        print(f"Groq API error in extract_intent_with_groq: {e}")
        return None


def extract_intent_fallback(query, conversation_context=None):
    """
    Fallback intent extraction when Groq API fails.
    Uses keyword matching and heuristics.
    """
    query_lower = query.lower().strip()

    # Check for greetings
    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
    if any(g in query_lower for g in greetings) and len(query_lower) < 30:
        return {
            'intent': 'greeting',
            'business_type': None,
            'location': None,
            'nearby': False,
            'result_count': None,
            'filters': {},
            'sort_by': 'relevance',
            'explanation': 'Greeting detected',
            'original_query': query,
        }

    # Check for help
    help_queries = ['what can you do', 'help', 'how do you work', 'what do you do']
    if any(h in query_lower for h in help_queries):
        return {
            'intent': 'help',
            'business_type': None,
            'location': None,
            'nearby': False,
            'result_count': None,
            'filters': {},
            'sort_by': 'relevance',
            'explanation': 'Help query detected',
            'original_query': query,
        }

    # Check for follow-up queries
    follow_up_patterns = [
        'only one', 'just one', 'show me one', 'which one', 'closest',
        'tell me more', 'more details', 'about it', 'the first one',
        'the second one', 'the last one', 'closest one', 'nearest'
    ]
    if any(fp in query_lower for fp in follow_up_patterns):
        # Try to determine business type from context
        business_type = None
        if conversation_context:
            for msg in reversed(conversation_context):
                content = msg.get('content', '').lower()
                for key, val in CATEGORY_SYNONYMS.items():
                    if key in content:
                        business_type = val
                        break
                if business_type:
                    break

        return {
            'intent': 'follow_up',
            'business_type': business_type,
            'location': None,
            'nearby': False,
            'result_count': 1,
            'filters': {},
            'sort_by': 'distance',
            'explanation': 'Follow-up query detected',
            'original_query': query,
        }

    # Check for general questions (non-business)
    general_patterns = [
        'capital of', 'weather', 'who are you', 'what are you',
        'tell me about', 'tell me something about', 'what is', 'how does', 'why is',
        'meaning of', 'history of', 'population of', 'founder of', 'president of'
    ]
    # Only treat as general if no business keywords found
    has_business_keyword = any(key in query_lower for key in CATEGORY_SYNONYMS)
    if not has_business_keyword and any(gp in query_lower for gp in general_patterns):
        return {
            'intent': 'general_question',
            'business_type': None,
            'location': None,
            'nearby': False,
            'result_count': None,
            'filters': {},
            'sort_by': 'relevance',
            'explanation': 'General question detected',
            'original_query': query,
        }

    # Extract business type
    business_type = None
    for key, val in CATEGORY_SYNONYMS.items():
        if key in query_lower:
            business_type = val
            break

    # Extract location
    location = None
    for area in COIMBATORE_AREAS:
        if area in query_lower:
            location = area.title()
            break

    # Check for nearby
    nearby = any(term in query_lower for term in ['near me', 'nearby', 'close to me', 'around here', 'near the'])

    # Extract result count
    result_count = None
    count_patterns = {
        'one': 1, '1': 1, 'single': 1, 'a': 1, 'an': 1,
        'two': 2, '2': 2, 'couple': 2,
        'three': 3, '3': 3,
        'four': 4, '4': 4,
        'five': 5, '5': 5,
        'ten': 10, '10': 10,
    }
    for pattern, count in count_patterns.items():
        if re.search(r'\b' + pattern + r'\b', query_lower):
            result_count = count
            break

    # Check for "all"
    if 'all' in query_lower or 'every' in query_lower:
        result_count = MAX_RESULT_COUNT

    # Determine sort_by
    sort_by = 'relevance'
    if any(term in query_lower for term in ['closest', 'nearest', 'nearby']):
        sort_by = 'distance'
    elif any(term in query_lower for term in ['best', 'top', 'highest rated']):
        sort_by = 'rating'
    elif any(term in query_lower for term in ['cheap', 'affordable', 'budget']):
        sort_by = 'price'

    return {
        'intent': 'business_search',
        'business_type': business_type,
        'location': location,
        'nearby': nearby,
        'result_count': result_count,
        'filters': {},
        'sort_by': sort_by,
        'explanation': 'Fallback extraction',
        'original_query': query,
    }


def extract_intent(query, conversation_context=None):
    """
    Main entry point for intent extraction.
    Uses Groq LLM with fallback to keyword-based extraction.
    """
    result = extract_intent_with_groq(query, conversation_context)
    if result and result['intent'] != 'business_search' or (result and result.get('business_type')):
        return result
    return extract_intent_fallback(query, conversation_context)


def generate_response_with_groq(intent_data, businesses, user_lat=None, user_lon=None):
    """
    Use Groq LLM to generate a natural language response based on intent and results.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)

    intent = intent_data.get('intent', 'business_search')
    business_type = intent_data.get('business_type')
    location = intent_data.get('location')
    result_count = intent_data.get('result_count')
    sort_by = intent_data.get('sort_by', 'relevance')
    original_query = intent_data.get('original_query', '')

    # Build business data string for the prompt
    businesses_str = ""
    if businesses:
        businesses_str = "\n\nRetrieved business data:\n"
        for i, biz in enumerate(businesses):
            businesses_str += f"""
--- Business {i+1} ---
Name: {biz.get('name', 'N/A')}
Category: {biz.get('category', 'N/A')}
Subcategory: {biz.get('subcategory', 'N/A')}
Rating: {biz.get('rating', 'N/A')} ({biz.get('review_count', 0)} reviews)
Address: {biz.get('address', 'N/A')}
Area: {biz.get('area', 'N/A')}
Phone: {biz.get('phone', 'N/A')}
Price Range: {biz.get('price_range', 'N/A')}
Distance: {biz.get('distance_km', 'N/A')} km
Description: {biz.get('description', 'N/A')}
"""
    else:
        businesses_str = "\n\nNo businesses were found matching the criteria."

    # Build location context
    location_str = "the user's current location" if location == 'current_location' else (location or 'the specified area')

    prompt = f"""You are a helpful local business discovery assistant for Coimbatore, India.

User's original query: "{original_query}"

Intent analysis:
- Intent: {intent}
- Business type: {business_type or 'N/A'}
- Location: {location or 'N/A'}
- Result count requested: {result_count or 'default'}
- Sort preference: {sort_by}
{businesses_str}
Generate a natural, conversational response that:
1. Directly answers the user's query
2. Mentions the number of results found
3. Highlights key details (ratings, distance, price range)
4. Is concise but informative (2-4 sentences)
5. Uses a friendly, helpful tone
6. If no results were found, suggest alternatives or ask for clarification
7. If the intent is a follow-up, reference the previous context
8. Do NOT fabricate any business information - only use the data provided above
9. If the query is a general question (not business-related), answer it using your general knowledge
10. Format the response as plain text (no markdown)

Response:"""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API error in generate_response_with_groq: {e}")
        return None


def generate_response_fallback(intent_data, businesses, user_lat=None, user_lon=None):
    """
    Fallback response generation when Groq API fails.
    """
    intent = intent_data.get('intent', 'business_search')
    business_type = intent_data.get('business_type')
    location = intent_data.get('location')
    result_count = intent_data.get('result_count')
    original_query = intent_data.get('original_query', '')

    if intent == 'greeting':
        return "Hello! I'm your AI business discovery assistant. I can help you find hotels, restaurants, hospitals, salons, supermarkets, textiles, automobile services, gyms, electronics, education, and real estate in Coimbatore. What are you looking for?"

    if intent == 'help':
        return "I can help you discover local businesses in Coimbatore using natural language. Just tell me what you're looking for! For example:\n- 'Find hotels near me'\n- 'Show me 3 restaurants in Gandhipuram'\n- 'I need somewhere to stay close to the airport'\n- 'What's the weather today?' (I can answer general questions too!)"

    if intent == 'general_question':
        return f"I'd be happy to help with that! However, my specialty is finding local businesses in Coimbatore. For general questions like '{original_query}', I may not have the most accurate information. Try asking me about hotels, restaurants, hospitals, or other local businesses!"

    if intent == 'follow_up':
        if businesses:
            biz = businesses[0]
            # Ensure ASCII-safe output for Windows console compatibility
            name = biz.get('name', 'the business').encode('ascii', errors='replace').decode('ascii')
            address = biz.get('address', 'N/A').encode('ascii', errors='replace').decode('ascii')
            phone = biz.get('phone', 'N/A').encode('ascii', errors='replace').decode('ascii')
            price = biz.get('price_range', 'N/A').encode('ascii', errors='replace').decode('ascii')
            return f"Here's the details for {name}:\n- Category: {biz.get('category', 'N/A')}\n- Rating: {biz.get('rating', 'N/A')} ({biz.get('review_count', 0)} reviews)\n- Address: {address}\n- Phone: {phone}\n- Price Range: {price}\n- Distance: {biz.get('distance_km', 'N/A')} km"
        else:
            return "I don't have any previous results to reference. Could you please search for something first?"

    # Business search
    if businesses:
        count = len(businesses)
        biz_type = business_type or 'business'
        loc_text = f" in {location.title()}" if location and location != 'current_location' else " near you"

        if count == 1:
            biz = businesses[0]
            # Ensure ASCII-safe output for Windows console compatibility
            name = biz.get('name', 'N/A').encode('ascii', errors='replace').decode('ascii')
            address = biz.get('address', 'N/A').encode('ascii', errors='replace').decode('ascii')
            phone = biz.get('phone', 'N/A').encode('ascii', errors='replace').decode('ascii')
            price = biz.get('price_range', 'N/A').encode('ascii', errors='replace').decode('ascii')
            return f"I found 1 {biz_type.lower()}{loc_text}:\n\n{name} - Rating: {biz.get('rating', 'N/A')} ({biz.get('review_count', 0)} reviews)\nAddress: {address}\nPhone: {phone}\nPrice: {price}\nDistance: {biz.get('distance_km', 'N/A')} km"
        else:
            return f"I found {count} {biz_type.lower()}s{loc_text}. Here are the top results with their ratings, addresses, and distances. Let me know if you'd like more details about any of them!"
    else:
        biz_type = business_type or 'business'
        loc_text = f" in {location.title()}" if location and location != 'current_location' else " near you"
        return f"Sorry, I couldn't find any {biz_type.lower()}s{loc_text}. Try increasing the search radius, using a different area, or checking a different category."


def generate_response(intent_data, businesses, user_lat=None, user_lon=None):
    """
    Main entry point for response generation.
    Uses Groq LLM with fallback to template-based generation.
    """
    result = generate_response_with_groq(intent_data, businesses, user_lat, user_lon)
    if result:
        return result
    return generate_response_fallback(intent_data, businesses, user_lat, user_lon)


# Keep backward compatibility
def extract_with_groq(query):
    """Backward compatibility wrapper."""
    result = extract_intent(query)
    if result:
        return {
            'category': result.get('business_type', ''),
            'location': result.get('location', 'current_location'),
            'radius_km': 5,
            'intent': result.get('intent', 'business_search'),
        }
    return None


def extract_with_fallback(query):
    """Backward compatibility wrapper."""
    result = extract_intent_fallback(query)
    return {
        'category': result.get('business_type', ''),
        'location': result.get('location', 'current_location') or 'current_location',
        'radius_km': 5,
        'intent': result.get('intent', 'business_search'),
    }


def extract_search_params(query):
    """Backward compatibility wrapper."""
    result = extract_intent(query)
    if result and result.get('business_type'):
        return result
    return extract_intent_fallback(query)
