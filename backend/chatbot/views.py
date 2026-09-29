import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import Business, ChatMessage
from .services import extract_intent, generate_response
from .utils import search_businesses, get_area_coordinates


def index(request):
    """Render the chat interface."""
    return render(request, 'chatbot/index.html')


@require_http_methods(["GET"])
def health(request):
    """Return a simple liveness response for monitoring and local checks."""
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    """Register a new user."""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not username or not email or not password:
            return JsonResponse({'success': False, 'message': 'Username, email, and password are required.'})

        if len(password) < 6:
            return JsonResponse({'success': False, 'message': 'Password must be at least 6 characters.'})

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'message': 'Username already exists.'})

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already registered.'})

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)

        return JsonResponse({
            'success': True,
            'message': 'Registration successful.',
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request format.'})
    except IntegrityError:
        return JsonResponse({'success': False, 'message': 'Username or email already exists.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})


@csrf_exempt
@require_http_methods(["POST"])
def user_login(request):
    """Log in an existing user."""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return JsonResponse({'success': False, 'message': 'Username and password are required.'})

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Login successful.',
                'user': {'id': user.id, 'username': user.username, 'email': user.email}
            })
        else:
            return JsonResponse({'success': False, 'message': 'Invalid username or password.'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request format.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})


@require_http_methods(["POST"])
def user_logout(request):
    """Log out the current user."""
    logout(request)
    return JsonResponse({'success': True, 'message': 'Logged out successfully.'})


@require_http_methods(["GET"])
def get_current_user(request):
    """Return the currently logged-in user's info."""
    if request.user.is_authenticated:
        return JsonResponse({
            'success': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email
            }
        })
    return JsonResponse({'success': False, 'user': None})


@require_http_methods(["GET"])
def get_chat_history(request):
    """Get chat history for the logged-in user."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required.', 'messages': []})

    messages = ChatMessage.objects.filter(user=request.user).order_by('created_at')
    return JsonResponse({
        'success': True,
        'messages': [
            {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'businesses': msg.businesses,
                'intent_data': msg.intent_data,
                'created_at': msg.created_at.isoformat()
            }
            for msg in messages
        ]
    })


def save_chat_message(request, role, content, businesses=None, intent_data=None):
    """Save a chat message to DB if user is authenticated."""
    if request.user.is_authenticated:
        ChatMessage.objects.create(
            user=request.user,
            role=role,
            content=content,
            businesses=businesses or [],
            intent_data=intent_data or {}
        )


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """
    Process a chat message using intent-based natural language understanding.
    
    Flow:
    1. Extract user intent using LLM
    2. Based on intent, either search businesses or answer generally
    3. Apply result count limits and sorting
    4. Generate natural language response using LLM
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        conversation_context = data.get('conversation_context', [])

        if not query:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a query.',
                'businesses': []
            })

        # Save user message to DB if authenticated
        save_chat_message(request, 'user', query)

        # Step 1: Extract intent using LLM
        intent_data = extract_intent(query, conversation_context)
        intent = intent_data.get('intent', 'business_search')
        business_type = intent_data.get('business_type')
        location = intent_data.get('location')
        nearby = intent_data.get('nearby', False)
        result_count = intent_data.get('result_count')
        sort_by = intent_data.get('sort_by', 'relevance')
        filters = intent_data.get('filters', {})

        # Step 2: Handle different intents
        if intent == 'greeting':
            message = generate_response(intent_data, [], user_lat, user_lon)
            save_chat_message(request, 'assistant', message, [], intent_data)
            return JsonResponse({
                'success': True,
                'message': message,
                'businesses': [],
                'intent_data': intent_data
            })

        if intent == 'help':
            message = generate_response(intent_data, [], user_lat, user_lon)
            save_chat_message(request, 'assistant', message, [], intent_data)
            return JsonResponse({
                'success': True,
                'message': message,
                'businesses': [],
                'intent_data': intent_data
            })

        if intent == 'general_question':
            # For general questions, use LLM to answer without searching businesses
            message = generate_response(intent_data, [], user_lat, user_lon)
            save_chat_message(request, 'assistant', message, [], intent_data)
            return JsonResponse({
                'success': True,
                'message': message,
                'businesses': [],
                'intent_data': intent_data
            })

        if intent == 'follow_up':
            # For follow-up queries, try to use previous results from context
            # or perform a new search with the extracted business type
            if not business_type and conversation_context:
                # Try to extract business type from previous bot messages
                for msg in reversed(conversation_context):
                    if msg.get('role') == 'assistant':
                        content = msg.get('content', '').lower()
                        # Look for business type mentions
                        for cat in ['Hotel', 'Restaurant', 'Hospital', 'Beauty Salon', 'Supermarket',
                                   'Textiles', 'Automobile Service', 'Gym', 'Electronics', 'Education', 'Real Estate']:
                            if cat.lower() in content:
                                business_type = cat
                                break
                        if business_type:
                            break

            if not business_type:
                message = "I'm not sure what you're referring to. Could you please search for something first?"
                save_chat_message(request, 'assistant', message, [], intent_data)
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'businesses': [],
                    'intent_data': intent_data
                })

            # Perform search with the extracted business type
            # Use a larger radius for follow-ups to ensure we find results
            results = search_businesses(
                category=business_type,
                location=location,
                radius_km=50,  # Larger radius for follow-up context
                user_lat=user_lat,
                user_lon=user_lon,
                result_count=result_count or 1,
                sort_by=sort_by,
                filters=filters
            )

            businesses = []
            for business, distance in results:
                businesses.append({
                    'id': business.business_id,
                    'name': business.name,
                    'category': business.category,
                    'subcategory': business.subcategory,
                    'description': business.description,
                    'address': business.address,
                    'area': business.area,
                    'phone': business.phone,
                    'rating': business.rating,
                    'review_count': business.review_count,
                    'price_range': business.price_range,
                    'open_hours': business.open_hours,
                    'distance_km': round(distance, 2) if distance > 0 else None,
                    'latitude': business.latitude,
                    'longitude': business.longitude,
                })

            message = generate_response(intent_data, businesses, user_lat, user_lon)
            save_chat_message(request, 'assistant', message, businesses, intent_data)
            return JsonResponse({
                'success': True,
                'message': message,
                'businesses': businesses,
                'intent_data': intent_data
            })

        # Step 3: Business search intent
        if not business_type:
            message = "I couldn't understand what you're looking for. Try asking for hotels, restaurants, hospitals, salons, supermarkets, textiles, automobile services, gyms, electronics, education, or real estate."
            save_chat_message(request, 'assistant', message, [], intent_data)
            return JsonResponse({
                'success': True,
                'message': message,
                'businesses': [],
                'intent_data': intent_data
            })

        # Step 4: Search businesses with intent-based parameters
        results = search_businesses(
            category=business_type,
            location=location,
            radius_km=10,
            user_lat=user_lat,
            user_lon=user_lon,
            result_count=result_count,
            sort_by=sort_by,
            filters=filters
        )

        # Step 5: Format response
        businesses = []
        for business, distance in results:
            businesses.append({
                'id': business.business_id,
                'name': business.name,
                'category': business.category,
                'subcategory': business.subcategory,
                'description': business.description,
                'address': business.address,
                'area': business.area,
                'phone': business.phone,
                'rating': business.rating,
                'review_count': business.review_count,
                'price_range': business.price_range,
                'open_hours': business.open_hours,
                'distance_km': round(distance, 2) if distance > 0 else None,
                'latitude': business.latitude,
                'longitude': business.longitude,
            })

        # Step 6: Generate natural language response
        message = generate_response(intent_data, businesses, user_lat, user_lon)

        # Save assistant message to DB if authenticated
        save_chat_message(request, 'assistant', message, businesses, intent_data)

        return JsonResponse({
            'success': True,
            'message': message,
            'businesses': businesses,
            'intent_data': intent_data
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request format.',
            'businesses': []
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}',
            'businesses': []
        })


@require_http_methods(["GET"])
def search(request):
    """Direct search API endpoint."""
    category = request.GET.get('category', '')
    area = request.GET.get('area', '')
    radius = int(request.GET.get('radius', 5))
    lat = request.GET.get('latitude')
    lon = request.GET.get('longitude')
    limit = int(request.GET.get('limit', 10))

    user_lat = float(lat) if lat else None
    user_lon = float(lon) if lon else None

    if not category:
        return JsonResponse({'success': False, 'message': 'Category is required.'})

    results = search_businesses(category, area, radius, user_lat, user_lon, result_count=limit)

    businesses = []
    for business, distance in results:
        businesses.append({
            'id': business.business_id,
            'name': business.name,
            'category': business.category,
            'subcategory': business.subcategory,
            'description': business.description,
            'address': business.address,
            'area': business.area,
            'phone': business.phone,
            'rating': business.rating,
            'review_count': business.review_count,
            'price_range': business.price_range,
            'open_hours': business.open_hours,
            'distance_km': round(distance, 2) if distance > 0 else None,
        })

    return JsonResponse({
        'success': True,
        'count': len(businesses),
        'businesses': businesses
    })


@require_http_methods(["GET"])
def business_detail(request, business_id):
    """Get details for a specific business."""
    try:
        business = Business.objects.get(business_id=business_id)
        return JsonResponse({
            'success': True,
            'business': {
                'id': business.business_id,
                'name': business.name,
                'category': business.category,
                'subcategory': business.subcategory,
                'description': business.description,
                'services': business.services,
                'address': business.address,
                'area': business.area,
                'city': business.city,
                'phone': business.phone,
                'rating': business.rating,
                'review_count': business.review_count,
                'price_range': business.price_range,
                'open_hours': business.open_hours,
                'latitude': business.latitude,
                'longitude': business.longitude,
            }
        })
    except Business.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Business not found.'})


@require_http_methods(["GET"])
def categories(request):
    """Get all available categories."""
    cats = Business.objects.filter(status='active').values_list('category', flat=True).distinct().order_by('category')
    return JsonResponse({
        'success': True,
        'categories': list(cats)
    })


@require_http_methods(["GET"])
def areas(request):
    """Get all known Coimbatore areas."""
    from .services import COIMBATORE_AREAS
    return JsonResponse({
        'success': True,
        'areas': list(COIMBATORE_AREAS.keys())
    })
