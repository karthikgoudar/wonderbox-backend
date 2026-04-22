"""
Age-Appropriate Prompt Generation Examples
===========================================

This script demonstrates how the prompt builder adapts prompts based on child's age.
"""

from app.services.prompt_builder import build_sticker_prompt, get_age_group_info


def show_examples():
    """Show how prompts are adapted for different age groups."""
    
    # Example phrases children might say
    examples = [
        "a cat",
        "a dragon flying in the sky",
        "a princess in a castle",
        "a robot fighting monsters",
    ]
    
    # Test ages representing each group
    test_ages = [4, 8, 11, 14]
    
    print("=" * 80)
    print("AGE-APPROPRIATE STICKER PROMPT GENERATION")
    print("=" * 80)
    print()
    
    for age in test_ages:
        age_info = get_age_group_info(age)
        print(f"\n{'=' * 80}")
        print(f"AGE GROUP: {age_info['name']}")
        print(f"Complexity: {age_info['complexity']}")
        print(f"Details: {age_info['details']}")
        print(f"Themes: {age_info['themes']}")
        print(f"{'=' * 80}\n")
        
        for example in examples:
            prompt = build_sticker_prompt(example, child_age=age)
            print(f"Input (age {age}): {example}")
            print(f"Prompt: {prompt}")
            print()
    
    # Show what happens with no age specified
    print(f"\n{'=' * 80}")
    print("NO AGE SPECIFIED (defaults to middle childhood)")
    print(f"{'=' * 80}\n")
    
    for example in examples[:2]:
        prompt = build_sticker_prompt(example, child_age=None)
        print(f"Input: {example}")
        print(f"Prompt: {prompt}")
        print()


def show_age_groups():
    """Show all age group configurations."""
    print("\n" + "=" * 80)
    print("ALL AGE GROUPS")
    print("=" * 80 + "\n")
    
    for age in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
        info = get_age_group_info(age)
        print(f"Age {age:2d}: {info['name']:30s} | Complexity: {info['complexity']}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    
    show_age_groups()
    print("\n")
    show_examples()
    
    print("\n" + "=" * 80)
    print("TIP: Prompts automatically adapt to child's developmental stage!")
    print("=" * 80)
