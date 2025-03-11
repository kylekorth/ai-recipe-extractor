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
    - A `# Recipe Title` at the top
    - A `## Macros` section that includes any nutritional information like:
      - Calories (cal/kcal)
      - Protein (g)
      - Carbohydrates (g)
      - Fat (g)
      Look for this information anywhere in the text, including in nutrition labels, 
      nutrition facts panels, or inline text. Convert all formats to the standard format shown below.
    - A `## Ingredients` section with ingredients formatted as `- Ingredient | Quantity | Brand/Type`
      - Remove personal pronouns or phrases like "I used" or "We recommend"
      - Convert statements like "I used Brand X" to just "Brand X"
    - A `## Instructions` section with numbered steps
      - Keep instructions objective and direct, removing personal pronouns

    Return **only the structured Markdown recipes**, nothing else.

    Example conversions:
    Input: "1 scoop protein powder (I used 1UP brand)"
    Output: "- Protein powder | 1 scoop | 1UP"

    Input: "Nutrition: 345 calories, 40g protein, 21g carbs, 6g fat"
    Output:
    ## Macros
    - Calories: 345
    - Protein: 40g
    - Carbohydrates: 21g
    - Fat: 6g

    Input: "Nutrition Facts
    Serving Size 1 cup (240g)
    Amount Per Serving
    Calories 240
    Total Fat 8g
    Total Carbohydrate 37g
    Protein 8g"
    Output:
    ## Macros
    - Calories: 240
    - Protein: 8g
    - Carbohydrates: 37g
    - Fat: 8g
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
