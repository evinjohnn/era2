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

fake = Faker()

# --- Configuration aligned with the conversational flow ---
CATEGORIES = ["ring", "necklace", "earrings", "bracelet"]
METALS = ["gold", "silver", "platinum", "rose gold", "white gold"]
GEMSTONES = ["diamond", "sapphire", "ruby", "emerald", "pearl", "amethyst", "none"]
STYLES = ["classic", "modern", "vintage", "minimalist", "elegant", "bold"]
OCCASIONS = ["wedding", "birthday", "anniversary", "other", "gift", "formal"]
RECIPIENTS = ["wife", "parent", "girlfriend", "friend", "myself"]

def generate_product_name(category: str, style: str, gemstone: str, material: str) -> str:
    """Generate a realistic product name."""
    name_parts = [style.title()]
    if gemstone != 'none':
        name_parts.append(gemstone.title())
    name_parts.append(material.title())
    name_parts.append(category.title())
    return ' '.join(name_parts)

def generate_tags(category: str, style: str, gemstone: str, material: str, occasion: str, recipient: str) -> List[str]:
    """Generate comprehensive tags for the product."""
    tags = {category, style, material, occasion, recipient}
    if gemstone != 'none':
        tags.add(gemstone)
    return list(tags)

def create_product(product_id: int, category: str) -> Dict[str, Any]:
    """Generate a single product with all attributes."""
    style = random.choice(STYLES)
    material = random.choice(METALS)
    gemstone = random.choice(GEMSTONES)
    occasion = random.choice(OCCASIONS)
    recipient = random.choice(RECIPIENTS)
    
    name = generate_product_name(category, style, gemstone, material)
    tags = generate_tags(category, style, gemstone, material, occasion, recipient)
    
    price = 150.0 + (random.random() * 850)
    if "platinum" in material: price *= 2.0
    elif "gold" in material: price *= 1.5
    if "diamond" in gemstone: price *= 3.0
    elif gemstone not in ['none', 'pearl']: price *= 1.8
    
    return {
        'id': f"{category[:3].upper()}{product_id:04d}",
        'name': name,
        'category': category,
        'image_url': f"https://via.placeholder.com/300x300/{fake.hex_color()[1:]}/FFFFFF?Text={category.title()}",
        'price': round(price, 2),
        'metal': material,
        'gemstones': [gemstone] if gemstone != 'none' else [],
        'design_type': random.choice(['solitaire', 'halo', 'cluster', 'pendant', 'stud']),
        'style_tags': list(set([style] + random.sample(STYLES, k=random.randint(1, 2)))),
        'occasion_tags': list(set([occasion] + random.sample(OCCASIONS, k=random.randint(1, 2)))),
        'recipient_tags': list(set([recipient] + random.sample(RECIPIENTS, k=random.randint(1, 2)))),
        'tags': tags,
        'description': f"A stunning {style} {category} perfect for a {occasion} gift for your {recipient}. Crafted in beautiful {material}."
    }

def main():
    """Main function to generate and save the product catalog."""
    print("Generating enhanced product catalog...")
    products = [create_product(i, random.choice(CATEGORIES)) for i in range(1, 501)]
    
    output_file = "product_catalog_large.json"
    with open(output_file, 'w') as f:
        json.dump(products, f, indent=4)
    
    print(f"Generated {len(products)} products and saved to {output_file}")

if __name__ == "__main__":
    main()