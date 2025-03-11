import os
import argparse
import pdfplumber
import openai
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key and model from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key. Add it to the .env file or set it as an environment variable.")
if not OPENAI_MODEL:
    raise ValueError("Missing OpenAI model. Add it to the .env file or set it as an environment variable.")

# Get paths from environment variables with defaults
PDF_FOLDER = os.getenv("PDF_FOLDER", "pdf")  # Folder containing PDFs
RECIPE_OUTPUT_FOLDER = os.getenv("RECIPE_OUTPUT_FOLDER", "recipeFiles")  # Folder to save formatted recipes

# Ensure output folder exists
os.makedirs(RECIPE_OUTPUT_FOLDER, exist_ok=True)

# CLI argument parsing
parser = argparse.ArgumentParser(description="Extract recipes from a PDF.")
parser.add_argument("--start", type=int, default=1, help="Start page number (1-based index)")
parser.add_argument("--end", type=int, default=None, help="End page number (inclusive, 1-based index)")
args = parser.parse_args()

# Extract text only from specified pages
def extract_text(pdf_path, start_page, end_page):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        start_page = max(1, start_page)
        end_page = min(end_page or total_pages, total_pages)

        for i in range(start_page - 1, end_page):
            page_text = pdf.pages[i].extract_text()
            if page_text:
                text += page_text + "\n\n"

    return text.strip()

# AI-based text parsing
def parse_recipe_with_ai(text):
    client = openai.OpenAI()
    
    prompt = f"""
    Extract structured recipe data from the following text:
    ---
    {text}
    ---
    Format the output as structured Markdown. Each recipe should have:
    - A `# Recipe Title` at the top (in Title Case)
    - A `## Macros` section using blockquotes for nutritional information:
      > Calories (cal/kcal)
      > Protein (g)
      > Carbohydrates (g)
      > Fat (g)
    - A `## Ingredients` section with ingredients formatted as `- Ingredient (Brand) | Quantity | optional`
      - Use Title Case For All Ingredient Names (Capitalize Each Main Word)
      - Include brand/type in parentheses after the ingredient name if available
      - Spell out all ingredient names completely (no abbreviations)
      - Format milk types as "[Type] Milk" (e.g., "Almond Milk" not "Milk, Almond")
      - List all ingredients, including spices and seasonings, as top-level items
      - Never group or nest seasonings under a "Seasonings" category
      - Mark optional ingredients with "optional" at the end of the line
      - Use standardized measurement abbreviations as before
      - Remove personal pronouns or phrases like "I used" or "We recommend"
    
    Example format:
    # Recipe Title
    ## Macros
    > Calories: 290
    > Protein: 8g
    > Carbohydrates: 44g
    > Fat: 9g

    ## Ingredients
    - Almond Milk (Silk Unsweetened) | 1 c
    - Vanilla Extract | 1 tsp
    - Protein Powder (MyProtein) | 2 scoops
    - Oreo Thins | 2 | optional
    - Chocolate Chips | 1 tbsp | optional
    - Cinnamon | 1/4 tsp
    - Salt | 1/8 tsp

    Example conversions:
    Incorrect: "- Optional Toppings (Oreo Thins) | 2"
    Correct: "- Oreo Thins | 2 | optional"

    Incorrect: "- Optional Chocolate Chips | 1 tbsp"
    Correct: "- Chocolate Chips | 1 tbsp | optional"

    ## Instructions
    1. First step
    2. Second step
    3. Final step

    Return **only the structured Markdown recipes**, nothing else. Do not include any separators or dashes at the end of the recipe.
    """

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Extract structured recipe data as Markdown, including nutritional information from any format (nutrition labels, inline text, etc.)."},
            {"role": "user", "content": prompt}
        ]
    )

    ai_content = response.choices[0].message.content

    # Remove markdown code block if it exists
    ai_content = re.sub(r"```markdown\s*", "", ai_content)
    ai_content = re.sub(r"```", "", ai_content)

    return ai_content

# Extract and save multiple recipes from Markdown text
def save_recipes_from_markdown(markdown_text):
    recipes = markdown_text.split("\n# ")  # Split into individual recipes
    for recipe in recipes:
        recipe = recipe.strip()
        if not recipe:
            continue

        # Extract recipe name from first line
        first_line = recipe.split("\n")[0].strip()
        recipe_name = first_line.strip("# ").strip()

        # Clean filename (remove invalid characters)
        safe_recipe_name = re.sub(r"[^\w\s-]", "", recipe_name).replace(" ", "_").lower()

        # Save as .recipe file
        recipe_filepath = os.path.join(RECIPE_OUTPUT_FOLDER, f"{safe_recipe_name}.recipe")
        with open(recipe_filepath, "w") as f:
            f.write(f"# {recipe}")

        print(f"Saved recipe: {recipe_filepath}")

# Process all PDFs in the folder
pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
for pdf_file in pdf_files:
    pdf_path = os.path.join(PDF_FOLDER, pdf_file)
    print(f"Processing: {pdf_file} from pages {args.start} to {args.end or 'end'}")

    # Extract text from specified pages
    text_data = extract_text(pdf_path, args.start, args.end)

    # Parse extracted text with AI
    recipe_markdown = parse_recipe_with_ai(text_data)

    # Save recipes properly
    save_recipes_from_markdown(recipe_markdown)
    print(f"Completed processing: {pdf_file}")

print("Process complete. All PDFs processed and recipes extracted.")
