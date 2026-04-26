from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
import time

# Simple in-memory rate limiter
# In production, use Redis or similar for distributed systems
_rate_limit_store = {}
MIN_TIME_BETWEEN_REQUESTS = 20  # Minimum 20 seconds between requests
MAX_REQUESTS_PER_WINDOW = 3  # Max 3 requests per window
RATE_LIMIT_WINDOW = 90  # 90 seconds window (1.5 minutes)

def get_client_identifier():
    """Get a unique identifier for the client (IP address)"""
    # Try to get real IP if behind proxy
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

def check_rate_limit():
    """
    Check if the client has exceeded rate limits.
    Returns (allowed, wait_time_seconds, error_message)
    """
    client_id = get_client_identifier()
    now = time.time()
    
    # Initialize if first request
    if client_id not in _rate_limit_store:
        _rate_limit_store[client_id] = {
            'requests': [],
            'last_request_time': 0
        }
    
    client_data = _rate_limit_store[client_id]
    
    # Clean old requests (older than window)
    client_data['requests'] = [
        req_time for req_time in client_data['requests']
        if now - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check minimum time between requests
    time_since_last = now - client_data['last_request_time']
    if time_since_last < MIN_TIME_BETWEEN_REQUESTS:
        wait_time = int(MIN_TIME_BETWEEN_REQUESTS - time_since_last) + 1
        return (False, wait_time, f'Please wait {wait_time} seconds between requests. Minimum delay is {MIN_TIME_BETWEEN_REQUESTS} seconds.')
    
    # Check request count in window
    if len(client_data['requests']) >= MAX_REQUESTS_PER_WINDOW:
        oldest_request = min(client_data['requests'])
        wait_time = int(RATE_LIMIT_WINDOW - (now - oldest_request)) + 1
        return (False, wait_time, f'Rate limit exceeded: {MAX_REQUESTS_PER_WINDOW} requests per {RATE_LIMIT_WINDOW} seconds. Please wait {wait_time} seconds.')
    
    # All checks passed - record this request
    client_data['requests'].append(now)
    client_data['last_request_time'] = now
    
    return (True, 0, None)

def rate_limit_decorator(f):
    """Decorator to add rate limiting to a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        allowed, wait_time, error_msg = check_rate_limit()
        if not allowed:
            return jsonify({
                'error': error_msg,
                'wait_time': wait_time,
                'rate_limit_info': {
                    'max_requests': MAX_REQUESTS_PER_WINDOW,
                    'window_seconds': RATE_LIMIT_WINDOW,
                    'min_delay_seconds': MIN_TIME_BETWEEN_REQUESTS
                }
            }), 429
        return f(*args, **kwargs)
    return decorated_function

