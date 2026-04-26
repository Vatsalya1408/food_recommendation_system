from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app
from app.ocr import extract_ingredients
from app.gemini import analyze_ingredients
from app.utils import rate_limit_decorator
from app.cache_manager import get_cached_analysis, cache_analysis_result, get_cache_stats

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Redirect root to login page - login loads first."""
    return redirect(url_for('main.login'))

@bp.route('/login')
def login():
    """Login page - first page users see."""
    return render_template('login.html')

@bp.route('/dashboard')
def dashboard():
    """Main app - food recommendation system (after login)."""
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
@rate_limit_decorator
def upload():
    try:
        # Get files and age bracket from request
        files = request.files.getlist('productImage')
        age_bracket = request.form.get('ageBracket')
        diet_preference = request.form.get('dietPreference', 'none')
        allergens = request.form.get('allergies', '')

        if not files:
            return jsonify({'error': 'No files uploaded'}), 400

        if not age_bracket:
            return jsonify({'error': 'Age bracket not provided'}), 400

        # Extract ingredients from images
        ingredients = []
        for file in files:
            if file.filename == '':
                continue
            # Reset file pointer to beginning
            file.seek(0)
            # Verify file extension
            filename = file.filename.lower()
            if not (filename.endswith('.png') or filename.endswith('.jpg') or
                    filename.endswith('.jpeg') or filename.endswith('.gif') or
                    filename.endswith('.bmp') or filename.endswith('.webp')):
                return jsonify({'error': f'Invalid file type: {file.filename}. Please upload an image file.'}), 400

            text = extract_ingredients(file)
            if text:
                ingredients.extend(text.split('\n'))

        # Clean up extracted ingredients
        ingredients = [ingredient.strip() for ingredient in ingredients if ingredient.strip()]

        if not ingredients:
            return jsonify({'error': 'No text could be extracted from the images. Please ensure the images contain readable text.'}), 400

        # Get food database from app context
        food_db = current_app.food_db

        # Build enhanced prompt with database context
        age_guidelines = food_db.get_age_guidelines(age_bracket)
        nutrition_standards = food_db.get_nutritional_standards(age_bracket)
        harmful_ingredients = food_db.get_harmful_ingredients()

        # Create enhanced context for Gemini
        context_parts = []

        if age_guidelines:
            safe_foods = age_guidelines.get('safe_foods', [])[:10]
            avoid_foods = age_guidelines.get('strictly_avoid', [])[:10]
            context_parts.append(f"SAFE FOODS FOR {age_bracket.upper()}: {', '.join(safe_foods)}")
            context_parts.append(f"FOODS TO AVOID FOR {age_bracket.upper()}: {', '.join(avoid_foods)}")

        if nutrition_standards:
            daily_energy = nutrition_standards.get('daily_energy', {}).get('kcal', 'N/A')
            protein = nutrition_standards.get('macronutrients', {}).get('protein', {}).get('grams', 'N/A')
            iron = nutrition_standards.get('micronutrients', {}).get('iron', {}).get('mg', 'N/A')
            calcium = nutrition_standards.get('micronutrients', {}).get('calcium', {}).get('mg', 'N/A')
            context_parts.append(f"DAILY NUTRITIONAL NEEDS FOR {age_bracket.upper()}: Energy {daily_energy}kcal, Protein {protein}g, Iron {iron}mg, Calcium {calcium}mg")

        if harmful_ingredients:
            harmful_list = []
            for harm_key, harm_info in list(harmful_ingredients.items())[:8]:
                name = harm_info.get('name', harm_key)
                reason = harm_info.get('reason', 'Unknown risk')
                safe_from = harm_info.get('safe_from_age', 'NEVER')
                harmful_list.append(f"{name} ({reason}, safe from {safe_from})")
            context_parts.append(f"CRITICAL HARMFUL INGREDIENTS: {'; '.join(harmful_list)}")

        # Build enhanced prompt
        enhanced_prompt = "\n".join(context_parts) + "\n\nINGREDIENTS TO ANALYZE:\n" + "\n".join(ingredients)

        # Check for cached analysis first
        cached_result = get_cached_analysis(ingredients, age_bracket, diet_preference, allergens)
        if cached_result:
            print(f"✓ Using cached analysis for {len(ingredients)} ingredients")
            response = {
                'age_bracket': age_bracket,
                'ingredients': ingredients,
                'verdict': cached_result['verdict'],
                'allergen_check': cached_result['allergen_check'],
                'nutrition_info': cached_result['nutrition_info'],
                'age_specific_notes': cached_result['age_specific_notes'],
                'analysis': cached_result['analysis'],
                'cached': True,
                'cached_at': cached_result['cached_at'],
                'message': 'Ingredients analyzed successfully (from cache)'
            }
            return jsonify(response)

        # Analyze ingredients with Gemini (with enhanced context)
        try:
            analysis = analyze_ingredients([enhanced_prompt], age_bracket, diet_preference, allergens)
        except Exception as gemini_error:
            error_msg = str(gemini_error)
            # Provide user-friendly error messages
            if "Rate Limit" in error_msg or "quota" in error_msg.lower():
                return jsonify({'error': error_msg}), 429
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return jsonify({'error': 'Request timed out. Please try again. The API may be experiencing high load.'}), 504
            else:
                return jsonify({'error': f'Failed to analyze ingredients: {error_msg}'}), 500

        # Parse the analysis to extract structured data
        verdict = "UNKNOWN"
        allergen_check = {}
        nutrition_info = {}
        age_specific_notes = {}

        # Simple parsing of the HTML response (this could be improved with proper HTML parsing)
        analysis_lower = analysis.lower()
        if "verdict-safe" in analysis or "safe" in analysis_lower.split("verdict")[1].split("</")[0] if "verdict" in analysis_lower else False:
            verdict = "SAFE"
        elif "verdict-caution" in analysis or "caution" in analysis_lower.split("verdict")[1].split("</")[0] if "verdict" in analysis_lower else False:
            verdict = "CAUTION"
        elif "verdict-unsafe" in analysis or "unsafe" in analysis_lower.split("verdict")[1].split("</")[0] if "verdict" in analysis_lower else False:
            verdict = "UNSAFE"

        # Cache the analysis result for future use
        try:
            cache_analysis_result(
                ingredients=ingredients,
                age_bracket=age_bracket,
                diet_preference=diet_preference,
                allergens=allergens,
                verdict=verdict,
                allergen_check=allergen_check,
                nutrition_info=nutrition_info,
                age_specific_notes=age_specific_notes,
                analysis=analysis
            )
        except Exception as cache_error:
            print(f"Warning: Could not cache analysis result: {cache_error}")
            # Don't fail the request if caching fails

        response = {
            'age_bracket': age_bracket,
            'ingredients': ingredients,
            'verdict': verdict,
            'allergen_check': allergen_check,
            'nutrition_info': nutrition_info,
            'age_specific_notes': age_specific_notes,
            'analysis': analysis,
            'cached': False,
            'message': 'Ingredients analyzed successfully'
        }

        return jsonify(response)

    except Exception as e:
        import traceback
        error_details = str(e)
        # Don't expose full traceback to users in production
        return jsonify({'error': f'An error occurred: {error_details}'}), 500

@bp.route('/cache/stats')
def cache_stats():
    """Get cache statistics."""
    try:
        stats = get_cache_stats()
        return jsonify({
            'status': 'success',
            'cache_stats': stats
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/cache/clear-expired', methods=['POST'])
def clear_expired_cache_route():
    """Clear expired cache entries."""
    try:
        from app.cache_manager import clear_expired_cache
        clear_expired_cache()
        return jsonify({
            'status': 'success',
            'message': 'Expired cache entries cleared'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/cache/clear-all', methods=['POST'])
def clear_all_cache_route():
    """Clear all cache entries (admin only)."""
    try:
        from app.cache_manager import clear_all_cache
        clear_all_cache()
        return jsonify({
            'status': 'success',
            'message': 'All cache entries cleared'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
