# generate_product_data.py
import json
import random
import uuid
from faker import Faker

fake = Faker()

CATEGORIES = ["ring", "necklace", "earrings", "bracelet"] # Start with these 4
METALS = ["gold", "silver", "platinum", "rose gold", "white gold"]
GEMSTONES = ["diamond", "sapphire", "ruby", "emerald", "pearl", "amethyst", "topaz", "garnet", "opal", "none", "cubic zirconia", "moissanite"]
DESIGN_TYPES_RING = ["solitaire", "halo", "three-stone", "band", "cluster", "vintage inspired"]
DESIGN_TYPES_NECKLACE = ["pendant", "chain", "locket", "choker", "station"]
DESIGN_TYPES_EARRINGS = ["stud", "hoop", "drop", "chandelier", "cluster"]
DESIGN_TYPES_BRACELET = ["chain", "bangle", "cuff", "charm", "tennis"]
STYLES = ["classic", "modern", "vintage", "minimalist", "bohemian", "statement", "elegant", "delicate", "geometric", "bold"]
OCCASIONS = ["anniversary", "birthday", "engagement", "wedding", "graduation", "formal", "casual", "gift", "everyday wear", "valentine", "mothers day"]
RECIPIENTS = ["women", "unisex", "bride", "mother", "daughter", "girlfriend", "wife", "friend"] # Rings mostly for women in this example

def generate_product_name(category, metal, gemstones, style):
    gem_name = random.choice(gemstones) if "none" not in gemstones else ""
    if gem_name == "none": gem_name = ""

    name_patterns = [
        f"{random.choice(STYLES).capitalize()} {metal.capitalize()} {gem_name.capitalize()} {category.capitalize()}",
        f"{fake.word().capitalize()} {gem_name.capitalize()} {metal.capitalize()} {category.capitalize()}",
        f"{metal.capitalize()} {category.capitalize()} with {gem_name.capitalize()}",
        f"The {fake.word().capitalize()} {style.capitalize()} {category.capitalize()}"
    ]
    if not gem_name: # Adjust patterns if no gemstone
        name_patterns = [
            f"{random.choice(STYLES).capitalize()} {metal.capitalize()} {category.capitalize()}",
            f"{fake.word().capitalize()} {metal.capitalize()} {category.capitalize()}",
            f"Elegant {metal.capitalize()} {category.capitalize()}"
        ]
    return random.choice(name_patterns).replace("  ", " ").strip()


def get_design_types_for_category(category):
    if category == "ring": return DESIGN_TYPES_RING
    if category == "necklace": return DESIGN_TYPES_NECKLACE
    if category == "earrings": return DESIGN_TYPES_EARRINGS
    if category == "bracelet": return DESIGN_TYPES_BRACELET
    return ["general", "unique"] # Fallback

def generate_products(num_per_category=55): # Aiming for 200+ (55 * 4 = 220)
    products = []
    product_id_counter = 1

    for category in CATEGORIES:
        for i in range(num_per_category):
            product_id_prefix = category.upper()[:3]
            item_id = f"{product_id_prefix}{str(product_id_counter).zfill(3)}"
            product_id_counter += 1

            metal = random.choice(METALS)
            
            # Gemstones: 70% chance of having one, 20% two, 10% none (unless 'none' is picked)
            num_gems = 1
            if category not in ["bracelet"]: # Bracelets less likely to be gemstone-focused in this simple gen
                rand_gem_chance = random.random()
                if rand_gem_chance < 0.10: # 10% chance of no gemstone focus
                    current_gemstones = ["none"]
                elif rand_gem_chance < 0.80: # 70% chance of one gemstone
                    current_gemstones = [random.choice([g for g in GEMSTONES if g != "none"])]
                else: # 20% chance of two different gemstones
                    current_gemstones = random.sample([g for g in GEMSTONES if g != "none"], k=min(2, len(GEMSTONES)-1) )
            else:
                current_gemstones = ["none"] if random.random() < 0.5 else [random.choice([g for g in GEMSTONES if g != "none"])]


            style_tags = random.sample(STYLES, k=random.randint(1, 3))
            occasion_tags = random.sample(OCCASIONS, k=random.randint(1, 4))
            recipient_tags = random.sample(RECIPIENTS, k=random.randint(1,2)) if category != "men_specific" else ["men"] # adjust if adding men's categories

            name = generate_product_name(category, metal, current_gemstones, random.choice(style_tags))
            
            # Price range based on metal and gemstones
            base_price = random.uniform(50, 500)
            if "gold" in metal: base_price *= random.uniform(1.5, 3)
            if "platinum" in metal: base_price *= random.uniform(2, 4)
            if "diamond" in current_gemstones: base_price *= random.uniform(2, 5)
            if "sapphire" in current_gemstones or "ruby" in current_gemstones or "emerald" in current_gemstones:
                base_price *= random.uniform(1.5, 3)
            if len(current_gemstones) > 1 and "none" not in current_gemstones : base_price *= 1.3
            price = round(base_price, 2)
            if price < 20: price = round(random.uniform(19.99, 49.99),2) # Min price
            if price > 10000: price = round(random.uniform(5000, 9999.99),2) # Max price cap for this gen

            design_type_list = get_design_types_for_category(category)
            design_type = random.choice(design_type_list)
            
            description = f"{fake.sentence(nb_words=5)} {name.lower()}. {fake.sentence(nb_words=8)}"
            if "diamond" in current_gemstones:
                description += f" Features sparkling diamonds."
            if "vintage" in style_tags:
                description += " A piece with timeless vintage charm."


            product = {
                "id": item_id,
                "name": name,
                "category": category,
                "image_url": f"https://via.placeholder.com/200/{fake.hex_color()[1:]}/FFFFFF?Text={category.replace(' ', '+')}",
                "price": price,
                "metal": metal,
                "gemstones": current_gemstones, # Added this field
                "design_type": design_type,
                "style_tags": style_tags, # Added this field
                "occasion_tags": occasion_tags,
                "recipient_tags": recipient_tags, # Added this field
                "description": description
            }
            products.append(product)
            
    return products

if __name__ == "__main__":
    generated_product_list = generate_products(num_per_category=55) # Generate 55 for each of the 4 categories = 220
    
    # Option 1: Print as a Python list string to paste into your main file
    # print("PRODUCT_CATALOG_DB = [")
    # for i, product in enumerate(generated_product_list):
    #     print(f"    {json.dumps(product)},")
    # print("]")

    # Option 2: Save to a JSON file
    with open("product_catalog_large.json", "w") as f:
        json.dump(generated_product_list, f, indent=4)
    
    print(f"Generated {len(generated_product_list)} products and saved to product_catalog_large.json")
    print(f"Example product: {random.choice(generated_product_list)}")