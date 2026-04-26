"""
Cache Manager for ToddlerBites Analysis Results
Stores and retrieves cached analysis results to reduce API calls and improve performance.
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional


class AnalysisCache:
    """Manages caching of food analysis results."""

    def __init__(self, cache_file: str = "analysis_cache.json", cache_dir: str = "data"):
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / cache_file
        self.cache_expiry_days = 30

        self.cache_dir.mkdir(exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _generate_cache_key(self, ingredients: list, age_bracket: str, diet_preference: str = "none", allergens: str = "") -> str:
        sorted_ingredients = sorted([ing.lower().strip() for ing in ingredients])
        content = f"{age_bracket}|{diet_preference}|{allergens}|{'|'.join(sorted_ingredients)}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _is_expired(self, cached_at: str) -> bool:
        try:
            cached_time = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
            expiry_time = cached_time + timedelta(days=self.cache_expiry_days)
            return datetime.now(expiry_time.tzinfo) > expiry_time
        except Exception:
            return True

    def get_cached_analysis(self, ingredients: list, age_bracket: str, diet_preference: str = "none", allergens: str = "") -> Optional[Dict]:
        cache_key = self._generate_cache_key(ingredients, age_bracket, diet_preference, allergens)

        if cache_key in self.cache:
            entry = self.cache[cache_key]

            if self._is_expired(entry.get('cached_at', '')):
                del self.cache[cache_key]
                self._save_cache()
                return None

            return {
                'verdict': entry['verdict'],
                'allergen_check': entry.get('allergen_check', {}),
                'nutrition_info': entry.get('nutrition_info', {}),
                'age_specific_notes': entry.get('age_specific_notes', {}),
                'analysis': entry['analysis'],
                'cached': True,
                'cached_at': entry['cached_at']
            }

        return None

    def cache_analysis_result(self, ingredients: list, age_bracket: str, diet_preference: str, allergens: str,
                            verdict: str, allergen_check: Dict, nutrition_info: Dict,
                            age_specific_notes: Dict, analysis: str):
        cache_key = self._generate_cache_key(ingredients, age_bracket, diet_preference, allergens)

        cache_entry = {
            'ingredients': ingredients,
            'age_bracket': age_bracket,
            'diet_preference': diet_preference,
            'allergens': allergens,
            'verdict': verdict,
            'allergen_check': allergen_check,
            'nutrition_info': nutrition_info,
            'age_specific_notes': age_specific_notes,
            'analysis': analysis,
            'cached_at': datetime.now().isoformat()
        }

        self.cache[cache_key] = cache_entry
        self._save_cache()
        print(f"✓ Cached analysis result for {len(ingredients)} ingredients")

    def get_cache_stats(self) -> Dict:
        total_entries = len(self.cache)
        expired_count = 0

        for entry in self.cache.values():
            if self._is_expired(entry.get('cached_at', '')):
                expired_count += 1

        return {
            'total_entries': total_entries,
            'expired_entries': expired_count,
            'valid_entries': total_entries - expired_count,
            'cache_file_size': self.cache_file.stat().st_size if self.cache_file.exists() else 0
        }

    def clear_expired_cache(self):
        keys_to_remove = []

        for cache_key, entry in self.cache.items():
            if self._is_expired(entry.get('cached_at', '')):
                keys_to_remove.append(cache_key)

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            self._save_cache()
            print(f"✓ Cleared {len(keys_to_remove)} expired cache entries")

    def clear_all_cache(self):
        self.cache = {}
        self._save_cache()
        print("✓ Cleared all cache entries")


_cache_instance = None

def get_cache():
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AnalysisCache()
    return _cache_instance

def get_cached_analysis(*args, **kwargs):
    return get_cache().get_cached_analysis(*args, **kwargs)

def cache_analysis_result(*args, **kwargs):
    return get_cache().cache_analysis_result(*args, **kwargs)

def get_cache_stats():
    return get_cache().get_cache_stats()

def clear_expired_cache():
    return get_cache().clear_expired_cache()

def clear_all_cache():
    return get_cache().clear_all_cache()