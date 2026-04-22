"""
Prompt Builder for Age-Appropriate Sticker Generation
======================================================

Builds optimized image generation prompts based on child's age group.
Adjusts complexity, detail level, and style to match developmental stage.

Supports custom prompt templates from JSON configuration.
"""

from typing import Optional
from app.services.prompt_loader import get_prompt_loader


# Base style components
_BASE_STYLE = "black and white line drawing, coloring book style, bold outlines"
_BACKGROUND = "white background, clean lines"


# Age group definitions and style modifiers
_AGE_GROUPS = {
    "early_childhood": {
        "range": (3, 6),
        "name": "Early Childhood (3-6 years)",
        "complexity": "very simple",
        "details": "large shapes, minimal details, chunky outlines",
        "themes": "basic familiar objects, animals, toys",
        "line_weight": "extra thick lines",
        "spacing": "wide spacing between elements",
    },
    "middle_childhood": {
        "range": (7, 9),
        "name": "Middle Childhood (7-9 years)",
        "complexity": "moderate",
        "details": "medium detail, clear distinct shapes",
        "themes": "action scenes, characters, adventures",
        "line_weight": "thick lines",
        "spacing": "balanced spacing",
    },
    "late_childhood": {
        "range": (10, 12),
        "name": "Late Childhood (10-12 years)",
        "complexity": "detailed",
        "details": "fine details, intricate patterns, textures",
        "themes": "creative concepts, fantasy, storytelling",
        "line_weight": "medium lines",
        "spacing": "compact spacing",
    },
    "teen": {
        "range": (13, 99),
        "name": "Teen (12+ years)",
        "complexity": "complex",
        "details": "sophisticated details, realistic proportions, shading guides",
        "themes": "advanced concepts, manga style, detailed scenes",
        "line_weight": "varied line weights",
        "spacing": "dense composition",
    },
}


def _get_age_group(child_age: Optional[int]) -> dict:
    """
    Determine age group based on child's age.
    
    Returns the age group configuration dict.
    """
    if child_age is None:
        # Default to middle childhood if age not provided
        return _AGE_GROUPS["middle_childhood"]
    
    for group_key, group_config in _AGE_GROUPS.items():
        min_age, max_age = group_config["range"]
        if min_age <= child_age <= max_age:
            return group_config
    
    # Fallback to middle childhood
    return _AGE_GROUPS["middle_childhood"]


def build_sticker_prompt(text: str, child_age: Optional[int] = None, use_context_prefix: bool = True) -> str:
    """
    Build an age-appropriate sticker generation prompt.
    
    Adapts complexity and style based on child's developmental stage:
    - 3-6 years: Very simple, large shapes, thick lines
    - 7-9 years: Moderate detail, action scenes
    - 10-12 years: Detailed, intricate patterns
    - 12+ years: Complex, sophisticated details
    
    If context prefix is configured in JSON, it's prepended to child's speech.
    
    Args:
        text: Raw text from child's speech (e.g., "a flying dragon")
        child_age: Child's age in years (optional)
        use_context_prefix: Whether to use context prefix from JSON (default: True)
    
    Returns:
        Complete prompt optimized for image generation API
    
    Examples:
        >>> build_sticker_prompt("a cat", child_age=4)
        'simple and cute a cat, very simple, large shapes, minimal details, ...'
        
        >>> build_sticker_prompt("a dragon fighting a knight", child_age=11)
        'detailed and magical a dragon fighting a knight, detailed, fine details, ...'
    """
    # Start with child's speech text
    clean_text = (text or "").strip()
    
    # Handle empty input
    if not clean_text:
        clean_text = "a simple shape"
    
    # Try to get context prefix from JSON configuration
    context = None
    if use_context_prefix:
        try:
            loader = get_prompt_loader()
            context = loader.get_context_prefix(child_age)
        except Exception as e:
            print(f"Error loading context prefix: {e}")
            context = None
    
    # Prepend context to child's speech if available
    if context:
        base_text = f"{context} {clean_text}"
    else:
        base_text = clean_text
    
    # Get age-appropriate style modifiers
    age_group = _get_age_group(child_age)
    
    # Build the complete prompt with age-appropriate modifiers
    prompt_parts = [
        base_text,
        age_group["complexity"],
        age_group["details"],
        age_group["line_weight"],
        _BASE_STYLE,
        _BACKGROUND,
        age_group["spacing"],
    ]
    
    # Join with commas and clean up
    full_prompt = ", ".join(part.strip() for part in prompt_parts if part.strip())
    
    return full_prompt


def get_age_group_info(child_age: Optional[int] = None) -> dict:
    """
    Get information about the age group for a given age.
    
    Useful for debugging or showing parents what style their child gets.
    
    Args:
        child_age: Child's age in years
    
    Returns:
        {
            "name": "Middle Childhood (7-9 years)",
            "range": (7, 9),
            "complexity": "moderate",
            "description": "Age-appropriate details"
        }
    """
    age_group = _get_age_group(child_age)
    
    return {
        "name": age_group["name"],
        "range": age_group["range"],
        "complexity": age_group["complexity"],
        "themes": age_group["themes"],
        "details": age_group["details"],
    }
