CHARACTER_FEATURE_EXTRACTION_PROMPT = """
Based on the following character information, extract detailed visual features for consistent image generation.

Character Name: {name}
Description: {description}
Appearance: {appearance}

Please provide a detailed prompt template for generating this character's reference image.
The reference image should:
1. Include ALL distinctive features of the character
2. Be a full body portrait on white background
3. Have no environmental elements
4. Focus on the character's appearance only

Return a JSON object with the following structure:
{{
    "base_prompt": "detailed prompt for the character",
    "negative_prompt": "things to avoid in the image",
    "features": {{
        "gender": "male/female",
        "age": "age description",
        "hair": "detailed hair description",
        "eyes": "detailed eye description",
        "clothing": "detailed clothing description",
        "distinctive_features": "unique characteristics"
    }}
}}
"""

SCENE_PROMPT_TEMPLATE = """
{base_prompt}, {scene_context}
"""
