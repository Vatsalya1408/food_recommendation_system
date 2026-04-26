import os
from typing import List

# If python-dotenv is installed, load .env automatically so the project can use a local
# .env file with GOOGLE_API_KEY=... without requiring users to export the var manually.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional — if it's not installed, environment variables must be exported normally.
    pass
from dotenv import load_dotenv

load_dotenv()  # loads .env into environment

_HAS_GEMINI = False
genai = None
try:
    # google.generativeai is the canonical package name used by Google's examples
    import google.generativeai as genai
    # configure with env var if present
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        # Clean the API key (remove whitespace, newlines, etc.)
        api_key = api_key.strip()
        if api_key:
            try:
                genai.configure(api_key=api_key)
            except Exception as e:
                # Log configuration error but continue - will surface during actual calls
                print(f"Warning: Could not configure Gemini API: {e}")
                pass
    else:
        print("Warning: GOOGLE_API_KEY not found in environment variables")
    _HAS_GEMINI = True
except Exception as e:
    print(f"Warning: Could not import google.generativeai: {e}")
    _HAS_GEMINI = False


def _extract_text_from_response(resp):
    """Try several common response shapes and extract the assistant text."""
    # dict-like responses
    try:
        if isinstance(resp, dict):
            # candidates -> content
            cands = resp.get("candidates") or resp.get("outputs")
            if cands and len(cands) > 0:
                first = cands[0]
                # several shapes: {"content": ...} or {"output": ...} or {"text": ...}
                return first.get("content") or first.get("output") or first.get("text") or ""
    except Exception:
        pass

    # objects with attributes
    try:
        if hasattr(resp, "candidates") and len(resp.candidates) > 0:
            cand = resp.candidates[0]
            if hasattr(cand, "content"):
                return cand.content
            if hasattr(cand, "output"):
                return cand.output
            if isinstance(cand, dict):
                return cand.get("content") or cand.get("output") or cand.get("text") or ""
    except Exception:
        pass

    # fallback to string
    try:
        return str(resp)
    except Exception:
        return ""


def _get_best_available_model():
    """Try to find the best available model, preferring stable models over previews/experimental."""
    if not _HAS_GEMINI or genai is None:
        return "gemini-2.5-flash"  # fallback
    
    try:
        available_models = genai.list_models()
        # Prefer stable (non-preview, non-experimental) models
        stable_pro_models = []
        stable_flash_models = []
        preview_pro_models = []
        preview_flash_models = []
        
        for model in available_models:
            if 'generateContent' in model.supported_generation_methods:
                name = model.name.replace('models/', '')
                # Avoid experimental and preview models (they may have different quota limits)
                is_experimental = 'exp' in name.lower() or 'experimental' in name.lower()
                is_preview = 'preview' in name.lower()
                
                if 'pro' in name.lower() and not is_experimental:
                    if is_preview:
                        preview_pro_models.append(name)
                    else:
                        stable_pro_models.append(name)
                elif 'flash' in name.lower() and not is_experimental:
                    if is_preview:
                        preview_flash_models.append(name)
                    else:
                        stable_flash_models.append(name)
        
        # Return best available model (prefer stable, avoid experimental)
        # Prioritize: stable flash > stable pro > preview flash > preview pro
        if stable_flash_models:
            return stable_flash_models[0]
        elif stable_pro_models:
            return stable_pro_models[0]
        elif preview_flash_models:
            return preview_flash_models[0]
        elif preview_pro_models:
            return preview_pro_models[0]
    except Exception:
        pass
    
    # Fallback to stable model
    return "gemini-2.5-flash"

def analyze_ingredients(ingredients: List[str], age_bracket: str, diet_preference: str = "none", allergens: str = "", model: str = None) -> str:
    """Analyze ingredients using Google Gemini / Generative AI.

    Args:
      ingredients: list of ingredient strings
      age_bracket: human-readable age bracket (e.g., "1-2 years")
      diet_preference: user's dietary preference (e.g., "vegan", "vegetarian", "halal", "none")
      allergens: comma-separated string of allergens to avoid (e.g., "nuts, dairy")
      model: optional model name to use. If None, automatically detects the best available model.
            For paid plans, try: "gemini-2.5-pro", "gemini-1.5-pro", or "gemini-pro"
            For free tier: "gemini-2.5-flash" (default)

    Returns:
      String with the model's analysis.

    Raises:
      RuntimeError: if the Gemini library or API key is not available, or the call fails.
    """
    prompt = (
        f"You are a food safety and nutrition analysis engine specialized in toddler food evaluation.\n\n"
        f"IMPORTANT DATA INTERPRETATION RULES:\n"
        f"1. If the input text contains ingredient-like terms (e.g. water, sugar, flour, oil, additives, acids, flavors), treat them as an EXTRACTED INGREDIENTS LIST, even if the list appears incomplete or noisy.\n"
        f"2. Do NOT state that the ingredients list is missing if any ingredient-like items are present.\n"
        f"3. Only state \"ingredients list missing\" if NO ingredient-like items are detected at all.\n"
        f"4. If the ingredient list appears incomplete or partially extracted, clearly label it as:\n"
        f"   \"Partially extracted ingredients — analysis based on visible text only.\"\n\n"
        f"CRITICAL UI & FORMAT RULES:\n"
        f"- Use ONLY HTML for formatting.\n"
        f"- The OVERALL VERDICT must appear FIRST inside a colored verdict box.\n"
        f"- SAFE → green, CAUTION → yellow, UNSAFE → red.\n"
        f"- Section headings must use <h3>.\n"
        f"- Important labels must use <strong>.\n"
        f"- Extracted Ingredients MUST be the LAST section.\n"
        f"- Follow the exact order below. Do NOT add or reorder sections.\n\n"
        f"You will receive:\n"
        f"- OCR-extracted text from a product image (may include Nutrition Facts and Ingredients mixed)\n"
        f"- Toddler age bracket\n"
        f"- Parent dietary preferences\n"
        f"- Parent allergen restrictions\n\n"
        f"Your task:\n"
        f"Perform a conservative, safety-first analysis for toddlers using the visible ingredient-related information, even if partial.\n\n"
        f"===========================\n"
        f"STRICT OUTPUT FORMAT (HTML)\n"
        f"===========================\n\n"
        f"<!-- VERDICT BOX (TOP MOST) -->\n"
        f"<div class=\"verdict-box verdict-{{safe|caution|unsafe}}\">\n"
        f"  <h2>Overall Verdict</h2>\n"
        f"  <p class=\"verdict-label\"><strong>{{SAFE / CAUTION / UNSAFE}}</strong></p>\n"
        f"  <p class=\"verdict-summary\">{{one-line summary explaining the verdict}}</p>\n"
        f"</div>\n\n"
        f"<h3>Age Bracket</h3>\n"
        f"<p>{age_bracket}</p>\n\n"
        f"<h3>Reasoned Explanation</h3>\n"
        f"<p>{{2–4 clear, parent-friendly sentences explaining why this verdict was given}}</p>\n\n"
        f"<h3>Allergen Check</h3>\n"
        f"<ul>\n"
        f"  <li><strong>Dairy:</strong> Present / Not Present / Unclear</li>\n"
        f"  <li><strong>Nuts:</strong> Present / Not Present / Unclear</li>\n"
        f"  <li><strong>Soy:</strong> Present / Not Present / Unclear</li>\n"
        f"  <li><strong>Wheat/Gluten:</strong> Present / Not Present / Unclear</li>\n"
        f"  <li><strong>Other Allergens:</strong> list or \"None detected\"</li>\n"
        f"</ul>\n\n"
        f"<h3>Dietary Compatibility</h3>\n"
        f"<ul>\n"
        f"  <li><strong>Vegan:</strong> Compatible / Not Compatible / Unclear (short reason)</li>\n"
        f"  <li><strong>Halal:</strong> Compatible / Not Compatible / Unclear (short reason)</li>\n"
        f"  <li><strong>Vegetarian:</strong> Compatible / Not Compatible / Unclear (short reason)</li>\n"
        f"</ul>\n\n"
        f"<h3>Age-Specific Concerns</h3>\n"
        f"<ul>\n"
        f"  <li><strong>Added Sugars:</strong> explanation</li>\n"
        f"  <li><strong>Caffeine:</strong> explanation if applicable</li>\n"
        f"  <li><strong>Other Risks:</strong> explanation if applicable</li>\n"
        f"</ul>\n\n"
        f"<h3>Nutritional Value</h3>\n"
        f"<p>{{brief summary of nutritional usefulness or lack thereof}}</p>\n\n"
        f"<h3>Final Recommendation</h3>\n"
        f"<p>{{clear, actionable advice written for parents}}</p>\n\n"
        f"<h3>Extracted Ingredients</h3>\n"
        f"<p>\n"
        f"<strong>Note:</strong> Ingredients were partially extracted from the image. Analysis is based on visible text only.<br/>\n"
        f"{{comma-separated ingredient-like items detected from the image}}\n"
        f"</p>\n\n"
        f"===========================\n"
        f"ADDITIONAL RULES\n"
        f"===========================\n"
        f"- Never contradict yourself (do not say ingredients missing if listed)\n"
        f"- Safety-first, conservative tone\n"
        f"- Parent-friendly language\n"
        f"- No emojis\n"
        f"- No extra commentary\n\n"
        f"OCR-extracted text to analyze:\n"
        + "\n".join(ingredients)
    )

    if not _HAS_GEMINI or genai is None:
        raise RuntimeError(
            "Google Gemini support not available: install the library with `pip install google-generative-ai` "
            "and set the environment variable GOOGLE_API_KEY to a valid key."
        )

    # Ensure API key is configured
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "GOOGLE_API_KEY not found. Please set it in your .env file:\n"
            "GOOGLE_API_KEY=your_api_key_here\n\n"
            "Get an API key from: https://makersuite.google.com/app/apikey"
        )
    
    # Re-configure with cleaned API key (in case it wasn't configured at import time)
    try:
        genai.configure(api_key=api_key.strip())
    except Exception as e:
        if "invalid" in str(e).lower() or "API key" in str(e):
            raise RuntimeError(
                f"Invalid API key configuration: {e}\n\n"
                "Please check your .env file and ensure GOOGLE_API_KEY is set correctly.\n"
                "Get a new API key from: https://makersuite.google.com/app/apikey"
            )
        # If it's already configured, that's fine
        pass

    # Auto-detect best model if not specified
    if model is None:
        model = _get_best_available_model()

    # Retry logic with exponential backoff
    import time
    max_retries = 3
    retry_delay = 2  # Start with 2 seconds
    
    for attempt in range(max_retries):
        last_err = None
        
        # 1) Current API: GenerativeModel.generate_content()
        try:
            model_instance = genai.GenerativeModel(model)
            # Try simple call first (most compatible)
            try:
                response = model_instance.generate_content(prompt)
            except (TypeError, AttributeError, Exception):
                # If simple call fails, try with timeout
                try:
                    response = model_instance.generate_content(
                        prompt,
                        request_options={"timeout": 90}
                    )
                except (TypeError, AttributeError):
                    # If request_options not supported, try with generation config
                    try:
                        from google.generativeai.types import GenerationConfig
                        response = model_instance.generate_content(
                            prompt,
                            generation_config=GenerationConfig(
                                max_output_tokens=1000,
                                temperature=0.7,
                            )
                        )
                    except (ImportError, AttributeError, TypeError):
                        # Last resort: simple call
                        response = model_instance.generate_content(prompt)
            # Extract text from response
            if hasattr(response, 'text'):
                return response.text.strip()
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    parts = candidate.content.parts
                    if parts and len(parts) > 0:
                        return parts[0].text.strip()
        except Exception as e:
            last_err = e
            error_str = str(e)
            error_type = type(e).__name__
            
            # Check for ResourceExhausted (quota/billing issue)
            if error_type == "ResourceExhausted" or "exceeded your current quota" in error_str.lower():
                # Don't retry quota errors - they need billing/quota resolution
                break
            
            # Check if it's a rate limit error - don't retry immediately, wait longer
            if "429" in error_str or "rate limit" in error_str.lower():
                import re
                retry_match = re.search(r'retry in ([\d.]+)s', error_str, re.IGNORECASE)
                if retry_match:
                    wait_time = int(float(retry_match.group(1))) + 2
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                # If we can't extract wait time or it's the last attempt, break and show error
                break
            
            # For other errors, retry with exponential backoff
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff: 2s, 4s, 8s
                continue

        # 2) Try older API pattern: generate_content without config
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            if hasattr(response, 'text'):
                return response.text.strip()
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    parts = candidate.content.parts
                    if parts and len(parts) > 0:
                        return parts[0].text.strip()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue

        # 3) Fallback: Try legacy API patterns
        try:
            if hasattr(genai, "generate_text"):
                resp = genai.generate_text(model=model, prompt=prompt)
                text = _extract_text_from_response(resp)
                if text:
                    return text.strip()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                continue

    # If we get here, all attempts failed.
    error_str = str(last_err) if last_err else ""
    error_type = type(last_err).__name__ if last_err else ""
    
    # Check for quota exceeded (billing/quota issue - different from rate limit)
    if (error_type == "ResourceExhausted" or 
        "exceeded your current quota" in error_str.lower() or 
        ("quota" in error_str.lower() and "exceeded" in error_str.lower() and "429" not in error_str)):
        msg = (
            "⚠️ API Quota Exceeded: Your Google Gemini API quota has been exceeded.\n\n"
            "This is a billing/quota issue, not a temporary rate limit. To resolve:\n\n"
            "1. Check your billing status at: https://console.cloud.google.com/billing\n"
            "2. Verify your API quota limits at: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas\n"
            "3. Ensure you have billing enabled and sufficient quota available\n"
            "4. For free tier users: You may have reached your daily/monthly free tier limit\n\n"
            "For more information, visit: https://ai.google.dev/gemini-api/docs/quota"
        )
        raise RuntimeError(msg)
    
    # Check for rate limit errors (temporary - can retry)
    if "429" in error_str or "rate limit" in error_str.lower():
        import re
        # Try to extract retry delay from error message
        retry_match = re.search(r'retry in ([\d.]+)s', error_str, re.IGNORECASE)
        retry_seconds = int(float(retry_match.group(1))) if retry_match else 60
        
        # Check if it's free tier or paid tier limit
        is_free_tier = "free_tier" in error_str.lower() or "free" in error_str.lower()
        
        if is_free_tier:
            msg = (
                f"⚠️ Rate Limit Exceeded: You've reached the FREE tier limit (10 requests per minute).\n\n"
                f"Your API key appears to be on the free tier. To use Gemini Pro with higher limits:\n"
                f"1. Go to https://ai.google.dev/\n"
                f"2. Upgrade your API plan to a paid tier\n"
                f"3. Ensure your API key has access to paid models\n\n"
                f"Please wait approximately {retry_seconds} seconds before trying again.\n\n"
                f"For more information, visit: https://ai.google.dev/gemini-api/docs/rate-limits"
            )
        else:
            msg = (
                f"⚠️ Rate Limit Exceeded: You've reached your API rate limit.\n\n"
                f"Please wait approximately {retry_seconds} seconds before trying again.\n\n"
                f"This is a temporary limit. For permanent increases, check your quota settings at: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas"
            )
        raise RuntimeError(msg)
    
    # Check for invalid API key errors
    if ("API key not valid" in error_str or 
        "API_KEY_INVALID" in error_str or 
        "invalid api key" in error_str.lower() or
        "400" in error_str and "api key" in error_str.lower()):
        msg = (
            "⚠️ Invalid API Key: Your Google Gemini API key is not valid or has been revoked.\n\n"
            "To fix this:\n\n"
            "1. Go to https://makersuite.google.com/app/apikey or https://aistudio.google.com/app/apikey\n"
            "2. Create a new API key or check if your current key is still active\n"
            "3. Update your .env file with the new key:\n"
            "   GOOGLE_API_KEY=your_new_api_key_here\n"
            "4. Restart the server after updating the key\n\n"
            "Make sure the API key has access to the Gemini API and is not restricted.\n"
            "For more information, visit: https://ai.google.dev/gemini-api/docs"
        )
        raise RuntimeError(msg)
    
    # Check for model not found errors
    if "not found" in error_str.lower() or "not supported" in error_str.lower():
        msg = (
            "Model not found or not supported. "
            "Try using 'gemini-2.5-flash' or 'gemini-2.5-pro-preview-05-06' as the model name."
        )
        try:
            available_models = genai.list_models()
            model_names = [m.name for m in available_models if 'generateContent' in m.supported_generation_methods]
            if model_names:
                msg += f" Available models: {', '.join(model_names[:5])}"
        except:
            pass
        raise RuntimeError(msg)
    
    # Generic error message
    msg = (
        "Failed to call Google Generative AI (Gemini). Ensure `google-generative-ai` is installed, "
        "the `GOOGLE_API_KEY` env var is set, and the model name is correct."
    )
    if error_str:
        msg += f" Error: {error_str}"
    raise RuntimeError(msg)

