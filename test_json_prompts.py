"""
Test JSON Prompt Integration
=============================

Demonstrates how custom prompts from JSON are used when available,
and falls back to speech text when JSON has placeholders.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.prompt_builder import build_sticker_prompt
from app.services.prompt_loader import get_prompt_loader


def test_prompt_integration():
    """Test prompt loader integration with prompt builder."""
    
    print("=" * 80)
    print("JSON PROMPT INTEGRATION TEST")
    print("=" * 80)
    print()
    
    # Initialize loader
    loader = get_prompt_loader()
    
    # Test for each age group
    age_groups = [
        (5, "Early Childhood"),
        (8, "Middle Childhood"),
        (11, "Late Childhood"),
        (14, "Teen")
    ]
    
    for age, group_name in age_groups:
        print(f"\n{'='*80}")
        print(f"{group_name} - Age {age}")
        print(f"{'='*80}\n")
        
        # Check if custom prompts exist
        has_prompts = loader.has_valid_prompts(age)
        print(f"Custom prompts available: {has_prompts}")
        
        if has_prompts:
            all_prompts = loader.get_all_prompts(age)
            print(f"Number of custom prompts: {len(all_prompts)}")
            print(f"Custom prompts: {all_prompts}\n")
        
        # Test with custom prompts enabled (default)
        print("--- WITH Custom Prompts (use_custom_prompts=True) ---")
        speech_text = "a flying unicorn"
        prompt_custom = build_sticker_prompt(speech_text, child_age=age, use_custom_prompts=True)
        print(f"Speech text: '{speech_text}'")
        print(f"Generated prompt: {prompt_custom}\n")
        
        # Test with custom prompts disabled (uses speech text)
        print("--- WITHOUT Custom Prompts (use_custom_prompts=False) ---")
        prompt_speech = build_sticker_prompt(speech_text, child_age=age, use_custom_prompts=False)
        print(f"Speech text: '{speech_text}'")
        print(f"Generated prompt: {prompt_speech}\n")
        
        # Explain behavior
        if has_prompts:
            print("ℹ️ BEHAVIOR: Custom prompt from JSON is used (speech text ignored)")
        else:
            print("ℹ️ BEHAVIOR: No custom prompts → Falls back to speech text")
    
    print("\n" + "=" * 80)
    print("HOW IT WORKS")
    print("=" * 80)
    print("""
1. Child speaks: "a flying unicorn"
2. STT converts to text: "a flying unicorn"
3. Prompt Builder checks JSON for custom prompts:
   
   IF custom prompts exist in JSON for age group:
      → Use random custom prompt from JSON
      → Child's speech text is IGNORED
      → Example: JSON says "a princess in a castle" → that's what gets generated
   
   IF no custom prompts (placeholders only):
      → Use child's speech text
      → Example: Child says "a flying unicorn" → that's what gets generated

4. Age-appropriate style modifiers are added automatically
5. Final prompt sent to image generation API

CONFIGURATION:
- Edit prompts/age_based_prompts.json to add custom prompts
- Remove [PLACEHOLDER] and add real prompts
- When you add prompts, children will get ONLY those prompts (speech ignored)
- Leave placeholders to use children's speech as prompts
    """)


def test_prompt_reload():
    """Test hot-reloading prompts."""
    print("\n" + "=" * 80)
    print("PROMPT HOT-RELOADING TEST")
    print("=" * 80)
    print()
    
    loader = get_prompt_loader()
    
    print("You can reload prompts at runtime without restarting the server:")
    print()
    print("Python code:")
    print("  >>> from app.services.prompt_loader import get_prompt_loader")
    print("  >>> loader = get_prompt_loader()")
    print("  >>> loader.reload()  # Reloads JSON file")
    print()
    print("This allows you to:")
    print("  - Add new prompts")
    print("  - Edit existing prompts")
    print("  - Remove prompts")
    print("  - Changes take effect immediately for new requests")


if __name__ == "__main__":
    test_prompt_integration()
    test_prompt_reload()
