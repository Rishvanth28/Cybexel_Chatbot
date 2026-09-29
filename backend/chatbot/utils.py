import math
from django.db import models
from .services import COIMBATORE_AREAS, DEFAULT_RESULT_COUNT, MAX_RESULT_COUNT


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on Earth in km."""
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_area_coordinates(area_name):
    """Get coordinates for a known Coimbatore area."""
    area_lower = area_name.lower().strip()
    return COIMBATORE_AREAS.get(area_lower, (11.0168, 76.9558))  # Default to Coimbatore center


def search_businesses(
    category,
    location=None,
    radius_km=5,
    user_lat=None,
    user_lon=None,
    result_count=None,
    sort_by='relevance',
    filters=None
):
    """
    Search businesses by category, location, and radius with intent-based parameters.
    
    Args:
        category: Business category (e.g., 'Hotel', 'Restaurant')
        location: Area name or 'current_location'
        radius_km: Search radius in kilometers
        user_lat: User's latitude (for proximity search)
        user_lon: User's longitude (for proximity search)
        result_count: Maximum number of results to return
        sort_by: Sorting preference ('relevance', 'distance', 'rating', 'price')
        filters: Additional filters (e.g., {'cuisine': 'Indian'})
    
    Returns:
        List of (business, distance) tuples, sorted and limited
    """
    from .models import Business

    # Start with category filter
    queryset = Business.objects.filter(category=category, status='active')

    # Apply additional filters if provided
    if filters:
        if 'cuisine' in filters:
            queryset = queryset.filter(
                models.Q(subcategory__icontains=filters['cuisine']) |
                models.Q(search_keywords__icontains=filters['cuisine']) |
                models.Q(description__icontains=filters['cuisine'])
            )
        if 'price_range' in filters:
            queryset = queryset.filter(price_range=filters['price_range'])
        if 'min_rating' in filters:
            queryset = queryset.filter(rating__gte=filters['min_rating'])

    # Determine result count limit
    if result_count is None:
        limit = DEFAULT_RESULT_COUNT
    else:
        limit = min(result_count, MAX_RESULT_COUNT)

    # If user provided coordinates, calculate distance and filter
    if user_lat is not None and user_lon is not None:
        results = []
        for business in queryset:
            distance = haversine_distance(user_lat, user_lon, business.latitude, business.longitude)
            if distance <= radius_km:
                results.append((business, distance))

        # Apply sorting
        if sort_by == 'distance':
            results.sort(key=lambda x: x[1])
        elif sort_by == 'rating':
            results.sort(key=lambda x: (x[0].rating, -x[1]), reverse=True)
        elif sort_by == 'price':
            # Sort by price range (assuming format like "₹100-₹500" or "Budget", "Mid-range", "Luxury")
            price_order = {'Budget': 1, 'Mid-range': 2, 'Luxury': 3, '': 0}
            results.sort(key=lambda x: (price_order.get(x[0].price_range, 0), x[1]))
        else:  # relevance - combination of rating and distance
            results.sort(key=lambda x: (x[0].rating * 0.7 + (1 / (x[1] + 0.1)) * 0.3), reverse=True)

        return results[:limit]

    # If location is a known area, use area coordinates
    if location and location.lower() != 'current_location':
        area_lat, area_lon = get_area_coordinates(location)
        results = []
        for business in queryset:
            distance = haversine_distance(area_lat, area_lon, business.latitude, business.longitude)
            if distance <= radius_km:
                results.append((business, distance))

        # Apply sorting
        if sort_by == 'distance':
            results.sort(key=lambda x: x[1])
        elif sort_by == 'rating':
            results.sort(key=lambda x: (x[0].rating, -x[1]), reverse=True)
        elif sort_by == 'price':
            price_order = {'Budget': 1, 'Mid-range': 2, 'Luxury': 3, '': 0}
            results.sort(key=lambda x: (price_order.get(x[0].price_range, 0), x[1]))
        else:  # relevance
            results.sort(key=lambda x: (x[0].rating * 0.7 + (1 / (x[1] + 0.1)) * 0.3), reverse=True)

        return results[:limit]

    # Fallback: return businesses sorted by preference
    if sort_by == 'rating':
        results = [(b, 0) for b in queryset.order_by('-rating')[:limit]]
    elif sort_by == 'price':
        price_order = {'Budget': 1, 'Mid-range': 2, 'Luxury': 3, '': 0}
        all_businesses = list(queryset)
        all_businesses.sort(key=lambda x: price_order.get(x.price_range, 0))
        results = [(b, 0) for b in all_businesses[:limit]]
    else:  # relevance or distance - default to rating
        results = [(b, 0) for b in queryset.order_by('-rating')[:limit]]

    return results



