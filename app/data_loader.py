"""
Data loader for ToddlerBites LLM-based food recommendation system.
Loads JSON databases and provides utility functions for food analysis.
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class ToddlerFoodDatabase:
    """Load and manage toddler food safety database."""
    
    def __init__(self, data_dir: str = "."):
        """Initialize database loader.
        
        Args:
            data_dir: Directory containing JSON files
        """
        self.data_dir = Path(data_dir)
        self.databases = {}
        self._load_all_databases()
    
    def _load_all_databases(self):
        """Load all JSON database files."""
        files = [
            'foods_database.json',
            'age_guidelines.json',
            'ingredient_mappings.json',
            'nutrition_standards.json',
            'common_products.json'
        ]
        
        for file in files:
            filepath = self.data_dir / file
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.databases[file.replace('.json', '')] = json.load(f)
                    print(f"✓ Loaded {file}")
                except Exception as e:
                    print(f"✗ Error loading {file}: {e}")
            else:
                print(f"✗ File not found: {filepath}")
    
    def get_food_safety(self, food_name: str) -> Optional[Dict]:
        """Get safety information for a specific food."""
        foods_db = self.databases.get('foods_database', {}).get('foods', {})
        
        # Search across all categories
        for category, items in foods_db.items():
            if isinstance(items, dict):
                for food_key, food_info in items.items():
                    if food_name.lower() in food_key.lower() or \
                       food_name.lower() in food_info.get('name', '').lower():
                        return food_info
        return None
    
    def get_harmful_ingredients(self) -> Dict:
        """Get list of harmful ingredients."""
        mapping_db = self.databases.get('ingredient_mappings', {})
        return mapping_db.get('harmful_ingredients', {})
    
    def get_age_guidelines(self, age_bracket: str) -> Optional[Dict]:
        """Get age-specific guidelines."""
        guidelines = self.databases.get('age_guidelines', {}).get('age_brackets', {})
        return guidelines.get(age_bracket)
    
    def get_nutritional_standards(self, age_bracket: str) -> Optional[Dict]:
        """Get nutritional requirements for age bracket."""
        standards = self.databases.get('nutrition_standards', {}).get('nutrition_standards', {})
        return standards.get(age_bracket)
    
    def get_common_allergens(self) -> List[str]:
        """Get list of common allergens."""
        mapping_db = self.databases.get('ingredient_mappings', {})
        return mapping_db.get('common_allergens', [])
    
    def get_big_8_allergens(self) -> List[str]:
        """Get the Big 8 allergens."""
        mapping_db = self.databases.get('ingredient_mappings', {})
        return mapping_db.get('big_8_allergens', [])
    
    def get_choking_hazard_foods(self) -> List[str]:
        """Get list of choking hazard foods."""
        guidelines = self.databases.get('age_guidelines', {})
        return guidelines.get('choking_hazard_foods', [])
    
    def check_ingredient_safety(self, ingredient: str, age_bracket: str) -> Tuple[str, str]:
        """Check if ingredient is safe for given age.
        
        Returns:
            Tuple of (safety_status, reason)
        """
        harmful = self.get_harmful_ingredients()
        
        ingredient_lower = ingredient.lower()
        for harm_key, harm_info in harmful.items():
            if ingredient_lower in harm_key.lower() or \
               ingredient_lower in harm_info.get('name', '').lower():
                safe_from = harm_info.get('safe_from_age', 'NEVER')
                if safe_from == 'NEVER' or age_bracket not in safe_from:
                    return ('UNSAFE', harm_info.get('reason', 'Unknown risk'))
        
        return ('SAFE', 'No known risks')
    
    def get_daily_limits(self, age_bracket: str, nutrient: str) -> Optional[str]:
        """Get daily limit for nutrient."""
        guidelines = self.databases.get('age_guidelines', {})
        
        if nutrient.lower() == 'sugar':
            limits = guidelines.get('high_sugar_limits', {})
            return limits.get(age_bracket, {}).get('max_daily')
        elif nutrient.lower() == 'sodium':
            limits = guidelines.get('sodium_limits', {})
            return limits.get(age_bracket, {}).get('max_daily')
        
        return None
    
    def get_food_verdict(self, product_name: str) -> Optional[str]:
        """Get safety verdict for a packaged product."""
        products = self.databases.get('common_products', {}).get('products', {})
        
        # Search across all product categories
        for category, items in products.items():
            if isinstance(items, dict):
                for product_key, product_info in items.items():
                    if product_name.lower() in product_key.lower() or \
                       product_name.lower() in product_info.get('name', '').lower():
                        return product_info.get('verdict', 'No verdict')
        return None
    
    def build_gemini_context(self, age_bracket: str) -> str:
        """Build context string for Gemini API prompt."""
        age_guide = self.get_age_guidelines(age_bracket)
        nutrition = self.get_nutritional_standards(age_bracket)
        harmful = self.get_harmful_ingredients()
        
        context = f"""
TODDLER FOOD SAFETY CONTEXT FOR AGE: {age_bracket}

=== AGE GUIDELINES ===
Safe Foods: {', '.join(age_guide.get('safe_foods', [])[:10])}
Foods to Avoid: {', '.join(age_guide.get('strictly_avoid', [])[:10])}

=== DAILY NUTRITIONAL NEEDS ===
Calories: {nutrition.get('daily_energy', {}).get('kcal', 'N/A')}
Protein: {nutrition.get('macronutrients', {}).get('protein', {}).get('grams', 'N/A')}
Iron: {nutrition.get('micronutrients', {}).get('iron', {}).get('mg', 'N/A')}mg
Calcium: {nutrition.get('micronutrients', {}).get('calcium', {}).get('mg', 'N/A')}mg

=== CRITICAL HARMFUL INGREDIENTS ===
"""
        
        for harm_key, harm_info in list(harmful.items())[:5]:
            context += f"\n- {harm_info.get('name')}: {harm_info.get('reason')} (safe from {harm_info.get('safe_from_age')})"
        
        return context


def load_food_database(data_dir: str = ".") -> ToddlerFoodDatabase:
    """Convenience function to load database."""
    return ToddlerFoodDatabase(data_dir)


# Example usage
if __name__ == "__main__":
    # Initialize database
    db = load_food_database(".")
    
    # Example queries
    print("\n=== EXAMPLE QUERIES ===\n")
    
    # Check a food
    food = db.get_food_safety("banana")
    if food:
        print(f"Food: {food.get('name')}")
        print(f"Verdict: {food.get('verdict')}")
    
    # Get age guidelines
    guidelines = db.get_age_guidelines("1-2")
    if guidelines:
        print(f"\nAge 1-2 years guidelines:")
        print(f"Safe foods: {guidelines.get('safe_foods', [])[:5]}")
    
    # Check allergens
    allergens = db.get_common_allergens()
    print(f"\nCommon allergens: {allergens}")
    
    # Get nutritional needs
    nutrition = db.get_nutritional_standards("1-2")
    if nutrition:
        print(f"\nNutrition for 1-2 years:")
        print(f"Daily calories: {nutrition.get('daily_energy', {}).get('kcal')}")
    
    # Check product verdict
    verdict = db.get_food_verdict("Maggi Noodles")
    if verdict:
        print(f"\nMaggi Noodles verdict: {verdict}")
    
    # Get context for LLM
    context = db.build_gemini_context("1-2")
    print(f"\n=== LLM Context Preview ===\n{context[:300]}...")
