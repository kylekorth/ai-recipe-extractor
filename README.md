# Recipe Extractor
## Overview

This script extracts recipes from PDFs and saves them as .recipe files. It uses OpenAI to pull the recipes out of the PDF and then uses AI to format them into a .recipe file for consumption by the recipe manager app [Grocery](https://apps.apple.com/us/app/grocery-smart-shopping-list/id1195676848).

## Prep
- Buy Recipes from some social media influencer and download the PDFs.
- Edit out the pages that are not recipes.
- Drop the PDFs into the `pdf` folder.

## Setup

`brew install poppler`

`pip install -r requirements.txt`

`python convert.py`

### Advanced

If you want to extract recipes from a single page, you can do so by changing the `start` and `end` arguments in the `convert.py` file.

```python
python convert.py --start 1 --end 2
```

This will extract the first and second pages of every PDF in the `pdf` folder.

## OpenAI

You can change the OpenAI model by changing the `OPENAI_MODEL` environment variable in the `.env` file.
