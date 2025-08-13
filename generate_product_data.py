#!/usr/bin/env python3
"""
Generate comprehensive jewelry product data with proper tags for RAG matching
This ensures products can be accurately matched with user preferences
"""

import json
import random
from typing import List, Dict, Any

# Jewelry categories and their variations
JEWELRY_CATEGORIES = {
    'rings': ['engagement ring', 'wedding band', 'fashion ring', 'cocktail ring', 'stacking ring'],
    'necklaces': ['pendant necklace', 'chain necklace', 'statement necklace', 'choker', 'layered necklace'],
    'earrings': ['stud earrings', 'hoop earrings', 'drop earrings', 'chandelier earrings', 'ear cuffs'],
    'pendants': ['charm pendant', 'gemstone pendant', 'initial pendant', 'religious pendant'],
    'bracelets': ['charm bracelet', 'tennis bracelet', 'bangle', 'cuff bracelet', 'chain bracelet'],
    'watches': ['luxury watch', 'smartwatch', 'dress watch', 'sport watch']
}

# Metal types with variations
METAL_TYPES = {
    'gold': ['yellow gold', 'white gold', 'rose gold', '14k gold', '18k gold', '24k gold'],
    'silver': ['sterling silver', '925 silver', 'plated silver'],
    'platinum': ['platinum', '950 platinum', 'platinum alloy'],
    'rose gold': ['rose gold', 'pink gold', 'copper gold'],
    'white gold': ['white gold', 'rhodium plated gold']
}

# Style variations
STYLE_VARIATIONS = {
    'classic': ['traditional', 'timeless', 'elegant', 'sophisticated'],
    'modern': ['contemporary', 'minimalist', 'geometric', 'clean'],
    'vintage': ['antique', 'retro', 'art deco', 'victorian'],
    'minimalist': ['simple', 'clean', 'understated', 'modern'],
    'bold': ['dramatic', 'statement', 'eye-catching', 'luxurious'],
    'elegant': ['refined', 'graceful', 'sophisticated', 'classic']
}

# Gemstone types
GEMSTONE_TYPES = {
    'diamond': ['diamond', 'brilliant cut', 'princess cut', 'emerald cut', 'oval cut'],
    'sapphire': ['sapphire', 'blue sapphire', 'pink sapphire', 'yellow sapphire'],
    'ruby': ['ruby', 'burmese ruby', 'thai ruby', 'african ruby'],
    'emerald': ['emerald', 'colombian emerald', 'zambian emerald'],
    'pearl': ['pearl', 'freshwater pearl', 'south sea pearl', 'akoya pearl'],
    'none': ['plain', 'no gemstone', 'metal only']
}

# Occasion tags
OCCASION_TAGS = {
    'birthday': ['birthday', 'celebration', 'personal gift'],
    'anniversary': ['anniversary', 'romantic', 'couple gift'],
    'wedding': ['wedding', 'bridal', 'ceremony', 'marriage'],
    'graduation': ['graduation', 'achievement', 'academic'],
    'holiday': ['holiday', 'seasonal', 'festive', 'christmas', 'valentine']
}

# Recipient tags
RECIPIENT_TAGS = {
    'wife': ['wife', 'spouse', 'married', 'romantic'],
    'husband': ['husband', 'spouse', 'married', 'romantic'],
    'girlfriend': ['girlfriend', 'romantic', 'dating', 'relationship'],
    'boyfriend': ['boyfriend', 'romantic', 'dating', 'relationship'],
    'mother': ['mother', 'mom', 'parent', 'family'],
    'father': ['father', 'dad', 'parent', 'family'],
    'friend': ['friend', 'friendship', 'platonic', 'gift']
}

def generate_product_name(category: str, metal: str, style: str, gemstone: str) -> str:
    """Generate a realistic product name"""
    category_variants = JEWELRY_CATEGORIES.get(category, [category])
    metal_variants = METAL_TYPES.get(metal, [metal])
    style_variants = STYLE_VARIATIONS.get(style, [style])
    gemstone_variants = GEMSTONE_TYPES.get(gemstone, [gemstone])
    
    # Create name combinations
    if gemstone != 'none':
        name = f"{random.choice(style_variants).title()} {random.choice(gemstone_variants).title()} {random.choice(category_variants).title()}"
    else:
        name = f"{random.choice(style_variants).title()} {random.choice(metal_variants).title()} {random.choice(category_variants).title()}"
    
    return name

def generate_description(category: str, metal: str, style: str, gemstone: str, occasion: str, recipient: str) -> str:
    """Generate a detailed product description"""
    category_desc = f"Beautiful {category}"
    metal_desc = f"crafted in {metal}"
    style_desc = f"with {style} design"
    
    if gemstone != 'none':
        gemstone_desc = f"featuring stunning {gemstone}"
    else:
        gemstone_desc = f"with elegant {metal} finish"
    
    occasion_desc = f"Perfect for {occasion} gifts"
    recipient_desc = f"ideal for your {recipient}"
    
    description = f"{category_desc} {metal_desc}, {style_desc}, {gemstone_desc}. {occasion_desc}, {recipient_desc}. This piece combines timeless elegance with contemporary style."
    
    return description

def generate_price_range(category: str, metal: str, gemstone: str) -> float:
    """Generate realistic price based on category, metal, and gemstone"""
    base_prices = {
        'rings': {'gold': 800, 'silver': 200, 'platinum': 1500, 'rose gold': 900, 'white gold': 1000},
        'necklaces': {'gold': 600, 'silver': 150, 'platinum': 1200, 'rose gold': 700, 'white gold': 800},
        'earrings': {'gold': 400, 'silver': 100, 'platinum': 800, 'rose gold': 450, 'white gold': 500},
        'pendants': {'gold': 300, 'silver': 80, 'platinum': 600, 'rose gold': 350, 'white gold': 400},
        'bracelets': {'gold': 500, 'silver': 120, 'platinum': 1000, 'rose gold': 550, 'white gold': 600},
        'watches': {'gold': 2000, 'silver': 300, 'platinum': 3000, 'rose gold': 2200, 'white gold': 2500}
    }
    
    base_price = base_prices.get(category, {}).get(metal, 500)
    
    # Adjust for gemstone
    if gemstone != 'none':
        gemstone_multipliers = {
            'diamond': 2.5,
            'sapphire': 1.8,
            'ruby': 1.6,
            'emerald': 1.7,
            'pearl': 1.2
        }
        base_price *= gemstone_multipliers.get(gemstone, 1.5)
    
    # Add some variation (±20%)
    variation = random.uniform(0.8, 1.2)
    return round(base_price * variation, 2)

def generate_comprehensive_tags(category: str, metal: str, style: str, gemstone: str, occasion: str, recipient: str) -> List[str]:
    """Generate comprehensive tags for accurate RAG matching"""
    tags = []
    
    # Category tags
    tags.extend(JEWELRY_CATEGORIES.get(category, [category]))
    
    # Metal tags
    tags.extend(METAL_TYPES.get(metal, [metal]))
    
    # Style tags
    tags.extend(STYLE_VARIATIONS.get(style, [style]))
    
    # Gemstone tags
    tags.extend(GEMSTONE_TYPES.get(gemstone, [gemstone]))
    
    # Occasion tags
    tags.extend(OCCASION_TAGS.get(occasion, [occasion]))
    
    # Recipient tags
    tags.extend(RECIPIENT_TAGS.get(recipient, [recipient]))
    
    # Additional descriptive tags
    tags.extend(['jewelry', 'luxury', 'gift', 'premium', 'handcrafted'])
    
    return list(set(tags))  # Remove duplicates

def generate_product(category: str, metal: str, style: str, gemstone: str, occasion: str, recipient: str) -> Dict[str, Any]:
    """Generate a complete product with all attributes"""
    name = generate_product_name(category, metal, style, gemstone)
    description = generate_description(category, metal, style, gemstone, occasion, recipient)
    price = generate_price_range(category, metal, gemstone)
    tags = generate_comprehensive_tags(category, metal, style, gemstone, occasion, recipient)
    
    # Generate placeholder image URL
    image_url = f"https://via.placeholder.com/340x200/cccccc/FFFFFF?text={category.title()}+{metal.title()}"
    
    return {
        "id": f"{category}_{metal}_{style}_{gemstone}_{random.randint(1000, 9999)}",
        "name": name,
        "description": description,
        "price": price,
        "category": category,
        "metal": metal,
        "style": style,
        "gemstone": gemstone,
        "occasion": occasion,
        "recipient": recipient,
        "style_tags": tags,
        "image_url": image_url,
        "tags": tags  # For backward compatibility
    }

def generate_product_catalog() -> List[Dict[str, Any]]:
    """Generate a comprehensive product catalog"""
    products = []
    
    # Generate products for each combination
    for category in JEWELRY_CATEGORIES.keys():
        for metal in METAL_TYPES.keys():
            for style in STYLE_VARIATIONS.keys():
                for gemstone in GEMSTONE_TYPES.keys():
                    for occasion in OCCASION_TAGS.keys():
                        for recipient in RECIPIENT_TAGS.keys():
                            # Generate 2-3 products per combination for variety
                            for _ in range(random.randint(2, 3)):
                                product = generate_product(category, metal, style, gemstone, occasion, recipient)
                                products.append(product)
    
    # Shuffle products for variety
    random.shuffle(products)
    
    return products

def main():
    """Main function to generate and save product catalog"""
    print("Generating comprehensive jewelry product catalog...")
    
    # Generate products
    products = generate_product_catalog()
    
    print(f"Generated {len(products)} products")
    
    # Save to JSON file
    with open('product_catalog_comprehensive.json', 'w') as f:
        json.dump(products, f, indent=2)
    
    print("Product catalog saved to 'product_catalog_comprehensive.json'")
    
    # Show sample products
    print("\nSample products:")
    for i, product in enumerate(products[:3]):
        print(f"\n{i+1}. {product['name']}")
        print(f"   Price: ${product['price']:.2f}")
        print(f"   Category: {product['category']}")
        print(f"   Metal: {product['metal']}")
        print(f"   Style: {product['style']}")
        print(f"   Gemstone: {product['gemstone']}")
        print(f"   Tags: {', '.join(product['tags'][:5])}...")

if __name__ == "__main__":
    main()