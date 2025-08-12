#!/usr/bin/env python3
"""
Enhanced Product Database Generator
Creates a comprehensive product catalog optimized for conversational e-commerce
with rich tagging for RAG-based recommendations.
"""

import json
import random
from faker import Faker
from typing import List, Dict, Any

# Initialize Faker
fake = Faker()

# Product categories and their variations
CATEGORIES = {
    'rings': {
        'designs': ['solitaire', 'halo', 'three-stone', 'vintage', 'modern', 'classic', 'geometric', 'bohemian'],
        'materials': ['gold', 'white gold', 'rose gold', 'platinum', 'silver'],
        'gemstones': ['diamond', 'ruby', 'emerald', 'sapphire', 'pearl', 'moissanite', 'aquamarine', 'amethyst'],
        'styles': ['elegant', 'romantic', 'sophisticated', 'minimalist', 'bold', 'delicate', 'timeless']
    },
    'necklaces': {
        'designs': ['pendant', 'choker', 'layered', 'statement', 'minimalist', 'vintage', 'modern'],
        'materials': ['gold', 'white gold', 'rose gold', 'platinum', 'silver', 'sterling silver'],
        'gemstones': ['diamond', 'pearl', 'sapphire', 'ruby', 'emerald', 'opal', 'turquoise'],
        'styles': ['elegant', 'romantic', 'sophisticated', 'casual', 'trendy', 'classic', 'bohemian']
    },
    'earrings': {
        'designs': ['stud', 'hoop', 'drop', 'chandelier', 'cluster', 'vintage', 'modern'],
        'materials': ['gold', 'white gold', 'rose gold', 'platinum', 'silver', 'sterling silver'],
        'gemstones': ['diamond', 'pearl', 'sapphire', 'ruby', 'emerald', 'cubic zirconia'],
        'styles': ['elegant', 'romantic', 'sophisticated', 'casual', 'trendy', 'classic', 'playful']
    },
    'bracelets': {
        'designs': ['chain', 'bangle', 'charm', 'tennis', 'vintage', 'modern', 'stackable'],
        'materials': ['gold', 'white gold', 'rose gold', 'platinum', 'silver', 'sterling silver'],
        'gemstones': ['diamond', 'pearl', 'sapphire', 'ruby', 'emerald', 'crystal'],
        'styles': ['elegant', 'romantic', 'sophisticated', 'casual', 'trendy', 'classic', 'charming']
    }
}

# Occasion mappings
OCCASION_MAPPINGS = {
    'wedding': ['wedding', 'engagement', 'bridal', 'formal', 'romantic', 'celebration'],
    'birthday': ['birthday', 'celebration', 'gift', 'personal', 'special'],
    'anniversary': ['anniversary', 'romantic', 'love', 'celebration', 'milestone'],
    'valentine': ['valentine', 'romantic', 'love', 'couples', 'romance'],
    'christmas': ['christmas', 'holiday', 'gift', 'celebration', 'festive'],
    'mother': ['mother', 'maternal', 'family', 'appreciation', 'love'],
    'graduation': ['graduation', 'achievement', 'milestone', 'success', 'celebration']
}

# Recipient mappings
RECIPIENT_MAPPINGS = {
    'wife': ['wife', 'spouse', 'romantic', 'elegant', 'sophisticated', 'loving'],
    'girlfriend': ['girlfriend', 'romantic', 'young', 'trendy', 'stylish', 'sweet'],
    'mother': ['mother', 'parent', 'family', 'classic', 'timeless', 'caring'],
    'daughter': ['daughter', 'family', 'young', 'trendy', 'sweet', 'loving'],
    'friend': ['friend', 'casual', 'stylish', 'modern', 'fun', 'friendly'],
    'sister': ['sister', 'family', 'sibling', 'close', 'loving', 'supportive'],
    'myself': ['self', 'personal', 'individual', 'unique', 'self-care', 'indulgence']
}

def generate_product_name(category: str, design: str, gemstone: str, material: str) -> str:
    """Generate a realistic product name."""
    name_parts = []
    
    # Add design/style descriptor
    if design in ['vintage', 'modern', 'classic', 'bohemian']:
        name_parts.append(design.title())
    
    # Add material
    if material == 'white gold':
        name_parts.append('White Gold')
    elif material == 'rose gold':
        name_parts.append('Rose Gold')
    else:
        name_parts.append(material.title())
    
    # Add gemstone
    if gemstone != 'none':
        name_parts.append(gemstone.title())
    
    # Add category
    name_parts.append(category.title())
    
    return ' '.join(name_parts)

def generate_description(category: str, design: str, gemstone: str, material: str, style: str) -> str:
    """Generate a realistic product description."""
    descriptions = [
        f"A beautiful {style} {category} featuring {gemstone} and crafted in {material}.",
        f"Elegant {design} {category} design with {gemstone} accents in {material}.",
        f"Stunning {style} {category} perfect for special occasions, made with {material} and {gemstone}.",
        f"Timeless {design} {category} showcasing {gemstone} beauty in {material}.",
        f"Exquisite {style} {category} with {gemstone} details, crafted in premium {material}."
    ]
    return random.choice(descriptions)

def generate_tags(category: str, design: str, gemstone: str, material: str, style: str, 
                  occasion: str, recipient: str) -> List[str]:
    """Generate comprehensive tags for the product."""
    tags = []
    
    # Basic category and design tags
    tags.extend([category, design, material, style])
    
    # Gemstone tags
    if gemstone != 'none':
        tags.append(gemstone)
    
    # Occasion tags
    if occasion in OCCASION_MAPPINGS:
        tags.extend(OCCASION_MAPPINGS[occasion])
    
    # Recipient tags
    if recipient in RECIPIENT_MAPPINGS:
        tags.extend(RECIPIENT_MAPPINGS[recipient])
    
    # Additional contextual tags
    if occasion == 'wedding':
        tags.extend(['bridal', 'formal', 'luxury'])
    elif occasion == 'birthday':
        tags.extend(['gift', 'personal', 'celebration'])
    elif occasion == 'anniversary':
        tags.extend(['romantic', 'love', 'milestone'])
    
    if recipient in ['wife', 'girlfriend']:
        tags.extend(['romantic', 'couples'])
    elif recipient in ['mother', 'daughter', 'sister']:
        tags.extend(['family', 'loving'])
    
    # Style-specific tags
    if style == 'elegant':
        tags.extend(['sophisticated', 'refined'])
    elif style == 'romantic':
        tags.extend(['loving', 'sentimental'])
    elif style == 'modern':
        tags.extend(['contemporary', 'trendy'])
    elif style == 'vintage':
        tags.extend(['retro', 'classic'])
    
    # Remove duplicates while preserving order
    unique_tags = []
    for tag in tags:
        if tag.lower() not in [t.lower() for t in unique_tags]:
            unique_tags.append(tag)
    
    return unique_tags

def generate_price(category: str, material: str, gemstone: str, design: str) -> float:
    """Generate realistic pricing based on product attributes."""
    base_price = 100.0
    
    # Material multiplier
    material_multipliers = {
        'silver': 1.0,
        'gold': 2.5,
        'white gold': 3.0,
        'rose gold': 3.2,
        'platinum': 4.0
    }
    
    # Gemstone multiplier
    gemstone_multipliers = {
        'none': 0.8,
        'cubic zirconia': 1.0,
        'pearl': 1.2,
        'crystal': 1.3,
        'amethyst': 1.5,
        'aquamarine': 1.8,
        'turquoise': 2.0,
        'opal': 2.2,
        'emerald': 3.0,
        'ruby': 3.5,
        'sapphire': 3.8,
        'diamond': 5.0,
        'moissanite': 2.5
    }
    
    # Design complexity multiplier
    design_multipliers = {
        'minimalist': 0.8,
        'classic': 1.0,
        'modern': 1.2,
        'vintage': 1.3,
        'geometric': 1.4,
        'bohemian': 1.5,
        'halo': 1.8,
        'three-stone': 2.0,
        'chandelier': 2.2,
        'statement': 2.5
    }
    
    # Category base price
    category_base = {
        'rings': 200,
        'necklaces': 150,
        'earrings': 120,
        'bracelets': 100
    }
    
    base_price = category_base.get(category, 150)
    
    # Calculate final price
    price = base_price
    price *= material_multipliers.get(material, 1.0)
    price *= gemstone_multipliers.get(gemstone, 1.0)
    price *= design_multipliers.get(design, 1.0)
    
    # Add some randomness
    price *= random.uniform(0.8, 1.2)
    
    # Round to nearest dollar
    return round(price, 2)

def generate_product(category: str, product_id: str) -> Dict[str, Any]:
    """Generate a single product with all attributes."""
    category_info = CATEGORIES[category]
    
    # Randomly select attributes
    design = random.choice(category_info['designs'])
    material = random.choice(category_info['materials'])
    gemstone = random.choice(category_info['gemstones'] + ['none'])
    style = random.choice(category_info['styles'])
    
    # Randomly select occasion and recipient
    occasion = random.choice(list(OCCASION_MAPPINGS.keys()))
    recipient = random.choice(list(RECIPIENT_MAPPINGS.keys()))
    
    # Generate product details
    name = generate_product_name(category, design, gemstone, material)
    description = generate_description(category, design, gemstone, material, style)
    price = generate_price(category, material, gemstone, design)
    tags = generate_tags(category, design, gemstone, material, style, occasion, recipient)
    
    # Generate image URL (placeholder)
    image_url = f"https://via.placeholder.com/300x300/random?text={category.title()}"
    
    return {
        'id': product_id,
        'name': name,
        'category': category,
        'image_url': image_url,
        'price': price,
        'metal': material,
        'gemstones': [gemstone] if gemstone != 'none' else [],
        'design_type': design,
        'style_tags': [style],
        'occasion_tags': [occasion],
        'recipient_tags': [recipient],
        'tags': tags,
        'description': description
    }

def generate_product_catalog(num_products: int = 1000) -> List[Dict[str, Any]]:
    """Generate a complete product catalog."""
    products = []
    
    # Ensure we have a good distribution across categories
    categories = list(CATEGORIES.keys())
    products_per_category = num_products // len(categories)
    
    for i, category in enumerate(categories):
        start_id = i * products_per_category + 1
        
        for j in range(products_per_category):
            product_id = f"{category[:3].upper()}{start_id + j:03d}"
            product = generate_product(category, product_id)
            products.append(product)
    
    # Add some extra products to reach the target number
    remaining = num_products - len(products)
    for i in range(remaining):
        category = random.choice(categories)
        product_id = f"{category[:3].upper()}{len(products) + 1:03d}"
        product = generate_product(category, product_id)
        products.append(product)
    
    return products

def main():
    """Main function to generate and save the product catalog."""
    print("Generating enhanced product catalog for conversational e-commerce...")
    
    # Generate products
    products = generate_product_catalog(1000)
    
    # Save to file
    output_file = "product_catalog_large.json"
    with open(output_file, 'w') as f:
        json.dump(products, f, indent=2)
    
    print(f"Generated {len(products)} products and saved to {output_file}")
    
    # Print some statistics
    categories = {}
    occasions = {}
    recipients = {}
    
    for product in products:
        cat = product['category']
        categories[cat] = categories.get(cat, 0) + 1
        
        occ = product['occasion_tags'][0] if product['occasion_tags'] else 'none'
        occasions[occ] = occasions.get(occ, 0) + 1
        
        rec = product['recipient_tags'][0] if product['recipient_tags'] else 'none'
        recipients[rec] = recipients.get(rec, 0) + 1
    
    print("\nProduct Distribution:")
    print("Categories:", dict(sorted(categories.items())))
    print("Occasions:", dict(sorted(occasions.items())))
    print("Recipients:", dict(sorted(recipients.items())))
    
    print(f"\nPrice Range: ${min(p['price'] for p in products):.2f} - ${max(p['price'] for p in products):.2f}")
    print(f"Average Price: ${sum(p['price'] for p in products) / len(products):.2f}")

if __name__ == "__main__":
    main()