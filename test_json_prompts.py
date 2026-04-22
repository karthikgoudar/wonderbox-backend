"""
Test JSON Context Prefix Integration
=====================================

Demonstrates how context prefixes from JSON are prepended to child's speech
to add age-appropriate flavor.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.prompt_builder import build_sticker_prompt
from app.services.prompt_loader import get_prompt_loader


def test_context_prefix():
    """Test context prefix integration with prompt builder."""
    
    print("=" * 80)
    print("JSON CONTEXT PREFIX INTEGRATION TEST")
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
    
    # Test with the same speech text across all ages
    speech_examples = ["a dragon", "a cat playing", "a magical forest"]
    
    for age, group_name in age_groups:
        print(f"\n{'='*80}")
        print(f"{group_name} - Age {age}")
        print(f"{'='*80}\n")
        
        # Get context prefix for this age
        context = loader.get_context_prefix(age)
        if context:
            print(f"✓ Context Prefix: '{context}'")
        else:
            print(f"✗ No context prefix configured (using speech as-is)")
        print()
        
        for speech_text in speech_examples:
            # Test with context prefix enabled (default)
            prompt_with_context = build_sticker_prompt(speech_text, child_age=age, use_context_prefix=True)
            
            # Test with context prefix disabled
            prompt_without_context = build_sticker_prompt(speech_text, child_age=age, use_context_prefix=False)
            
            print(f"Child says: '{speech_text}'")
            if context:
                print(f"  WITH context:    '{context} {speech_text}' + [age modifiers]")
            else:
                print(f"  WITH context:    '{speech_text}' + [age modifiers] (no context)")
            print(f"  WITHOUT context: '{speech_text}' + [age modifiers]")
            print(f"  Full prompt: {prompt_with_context[:100]}...")
            print()
    
    print("\n" + "=" * 80)
    print("HOW CONTEXT PREFIX WORKS")
    print("=" * 80)
    print("""
1. Child speaks: "a dragon"
2. STT converts to text: "a dragon"
3. Prompt Builder checks JSON for age-appropriate context:
   
   IF context_prefix is configured for age group:
      → Prepend context to child's speech
      → Example: context='magical and detailed' + 'a dragon' = 'magical and detailed a dragon'
   
   IF no context_prefix (placeholder):
      → Use child's speech as-is
      → Example: 'a dragon'

4. Age-appropriate style modifiers are added automatically:
   - Complexity (simple/moderate/detailed/complex)
   - Details level
   - Line weights
   - Spacing
   
5. Final prompt sent to image generation API

CONFIGURATION:
- Edit prompts/age_based_prompts.json
- Set "context_prefix" for each age group
- Examples: "cute and simple", "exciting and dynamic", "highly detailed"
- Leave as placeholder to disable context prefix (uses plain speech)
    """)
    print("\n" + "=" * 80)
    print("EXAMPLE WORKFLOW")
    print("=" * 80)
    print("""
Age 5 child: Says "a cat"
→ Context: "simple and cute"
→ Prompt: "simple and cute a cat, very simple, large shapes, minimal details, 
          chunky outlines, extra thick lines, black and white line drawing..."

Age 11 child: Says "a cat"  
→ Context: "detailed and magical"
→ Prompt: "detailed and magical a cat, detailed, fine details, intricate patterns,
          textures, medium lines, black and white line drawing..."

Same speech text, age-appropriate context and styling!
    """)

def test_hot_reload():
    """Test hot-reloading context prefixes."""
    print("\n" + "=" * 80)
    print("CONTEXT PREFIX HOT-RELOADING")
    print("=" * 80)
    print()
    
    loader = get_prompt_loader()
    
    print("You can reload context prefixes at runtime without restarting:")
    print()
    print("Python code:")
    print("  >>> from app.services.prompt_loader import get_prompt_loader")
    print("  >>> loader = get_prompt_loader()")
    print("  >>> loader.reload()  # Reloads JSON file")
    print()
    print("This allows you to:")
    print("  - Change context prefixes")
    print("  - Enable/disable context system")
    print("  - Test different contexts instantly")
    print("  - Changes take effect immediately for new requests")


if __name__ == "__main__":
    test_context_prefix()
    test_hot_reload()
