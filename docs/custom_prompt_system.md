# Custom Prompt System Guide

## Overview

The WonderBox backend supports **custom prompt templates** via JSON configuration. This allows you to curate specific sticker content for each age group, overriding children's speech input.

## How It Works

### 🎯 Two Operating Modes

#### Mode 1: Custom Prompts (Curated Content)
When you add prompts to the JSON file:
- **Children's speech is IGNORED**
- Random prompt selected from your JSON file
- Perfect for curated, quality-controlled content
- Use when you want specific themes/subjects

#### Mode 2: Speech-Based (Dynamic Content)
When JSON has only placeholders:
- **Children's speech is USED**
- Whatever child says becomes the prompt
- Perfect for creative freedom
- Use when you want dynamic, user-generated content

---

## Configuration File

**Location:** `prompts/age_based_prompts.json`

### Structure

```json
{
  "age_groups": {
  early_childhood:
    name: "Early Childhood (3-6 years)"
    prompts:
      - "a happy sun with a smile"
      - "a cute puppy playing"
      # Add more prompts here
  
  middle_childhood:
    name: "Middle Childhood (7-9 years)"
    prompts:
      - "a superhero saving the day"
      - "a dragon flying over mountains"
      # Add more prompts here
  
  late_childhood:
    name: "Late Childhood (10-12 years)"
    prompts:
      - "an enchanted forest with magical creatures"
      - "a detailed castle with towers"
      # Add more prompts here
  
  teen:
    name: "Teen (12+ years)"
    prompts:
      - "an anime warrior with intricate armor"
      - "a realistic portrait of a fantasy character"
      # Add more prompts here

settings:
  shuffle_prompts: true  # Randomly select prompts
  max_prompts_per_group: 50  # Limit per age group
```

---

## Adding Custom Prompts

### Step 1: Edit JSON File

Open `prompts/age_based_prompts.json` and replace placeholders:

**Before:**
```json
"early_childhood": {
  "prompts": [
    "[PLACEHOLDER] Add simple prompts here",
    "[PLACEHOLDER]"
  ]
}
```

**After:**
```json
"early_childhood": {
  "prompts": [
    "a happy cat",
    "a big red ball",
    "a smiling sun",
    "a colorful butterfly"
  ]
}
```

### Step 2: Test Your Prompts

```bash
# Test the integration (no extra dependencies needed!)
python test_json_prompts.py
```

### Step 3: Hot-Reload (Optional)

No need to restart the server! Prompts can be reloaded at runtime:

```python
from app.services.prompt_loader import get_prompt_loader

loader = get_prompt_loader()
loader.reload()  # Reloads JSON file immediately
```

---

## Prompt Writing Guidelines

### ✅ Good Prompts

- **Concise:** "a happy dog playing"
- **Clear subjects:** "a castle on a hill"
- **Simple descriptions:** "a butterfly with colorful wings"
- **Age-appropriate themes:** Match the age group

### ❌ Bad Prompts

- **Too long:** "a detailed photorealistic portrait of a dog with fluffy fur sitting in a garden with flowers"
- **Complex sentences:** "Create an image that shows a dog and cat playing together in the park while the sun sets"
- **Style instructions:** "simple coloring book style drawing" (added automatically)
- **Copyrighted content:** "Mickey Mouse", "Pokemon Pikachu"

### Why Short Prompts?

The system automatically adds age-appropriate style modifiers:

**Your prompt:** `"a dragon"`

**What gets sent to API:**
```
"a dragon, moderate, medium detail, clear distinct shapes, thick lines, 
black and white line drawing, coloring book style, bold outlines, 
white background, clean lines, balanced spacing"
```

---

## Prompt Selection Logic

### When Custom Prompts Are Used

```python
# JSON has valid prompts
"prompts": [
  "a happy cat",
  "a playful dog"
]

# Child says: "I want a unicorn"
# System generates: "a happy cat" OR "a playful dog"
# Child's speech is IGNORED
```

### When Speech Is Used

```python
# JSON has only placeholders
"prompts": [
  "[PLACEHOLDER]"
]

# Child says: "I want a unicorn"
# System generates: "I want a unicorn" (with style modifiers)
# Child's speech is USED
```

---

## Age Group Guidelines

### 🧒 Early Childhood (3-6 years)

**Characteristics:**
- Very simple objects
- Familiar everyday items
- Single subjects (no scenes)

**Example Prompts:**
```json
[
  "a happy sun",
  "a big ball",
  "a cute cat",
  "a red apple",
  "a smiling flower"
]
```

---

### 👧 Middle Childhood (7-9 years)

**Characteristics:**
- Action and movement
- Simple scenes
- Character interactions

**Example Prompts:**
```yaml
- "a superhero flying"
- "a dragon breathing fire"
- "a princess in a garden"
- "a pirate ship sailing"
- "a robot building blocks"
```

---

### 🧑 Late Childhood (10-12 years)

**Characteristics:**
- Fantasy themes
- Detailed concepts
- Creative scenarios

**Example Prompts:**
```yaml
- "an enchanted forest with fairies"
- "a magical wizard casting spells"
- "a detailed castle with towers and flags"
- "a phoenix rising from flames"
- "an underwater kingdom with mermaids"
```

---

### 🧔 Teen (12+ years)

**Characteristics:**
- Complex compositions
- Sophisticated themes
- Artistic styles

**Example Prompts:**
```yaml
- "an anime warrior with detailed armor"
- "a gothic cathedral with intricate details"
- "a cyberpunk cityscape"
- "a realistic portrait of a fantasy elf"
- "a mandala pattern with complex geometry"
```

---

## API Integration

### Automatic in Sticker Pipeline

The custom prompt system works automatically:

```
1. Child speaks → STT transcribes
2. Backend identifies child and age
3. Prompt builder checks YAML:
   - If custom prompts exist → Use random custom prompt
   - If no custom prompts → Use child's speech
4. Age-appropriate styles added
5. Image generated
```

### Programmatic Control

You can control prompt behavior programmatically:

```python
from app.services.prompt_builder import build_sticker_prompt

# Use custom prompts from YAML (default)
prompt = build_sticker_prompt("child's speech", child_age=8)

# Force use of speech text (ignore YAML)
prompt = build_sticker_prompt(
    "child's speech", 
    child_age=8, 
    use_custom_prompts=False
)
```

---

## Use Cases

### 🎨 Use Custom Prompts When:

1. **Quality Control**
   - You want to ensure appropriate content
   - Pre-reviewed, curated subjects
   - Brand consistency

2. **Themed Collections**
   - Seasonal themes (Christmas, Halloween)
   - Educational themes (animals, vehicles)
   - Special events

3. **Limited Subject Matter**
   - Focus on specific learning topics
   - Age-appropriate content only
   - Safe, approved subjects

### 🗣️ Use Speech-Based When:

1. **Creative Freedom**
   - Let children express imagination
   - Dynamic, unique content
   - Personalized experience

2. **Open-Ended Play**
   - Exploratory learning
   - No content restrictions
   - User-driven experience

3. **Testing/Development**
   - Quick iteration
   - No need to curate prompts
   - Dynamic testing scenarios

---

## Configuration Settings

### Shuffle Prompts

```yaml
settings:
  shuffle_prompts: true  # Random selection
```

- `true`: Random prompt each time
- `false`: Always use first prompt in list

### Max Prompts

```yaml
settings:
  max_prompts_per_group: 50
```

Limits prompts per age group (for performance).

---

## Testing

### Run Integration Test

```bash
python test_yaml_prompts.py
```

**Output shows:**
- Available custom prompts per age group
- Generated prompts with/without custom mode
- How system behaves in each scenario

### Manual Testing

```python
from app.services.prompt_loader import get_prompt_loader

loader = get_prompt_loader()

# Check if prompts exist for age 8
has_prompts = loader.has_valid_prompts(child_age=8)
print(f"Has prompts: {has_prompts}")

# Get all prompts for age 8
prompts = loader.get_all_prompts(child_age=8)
print(f"Prompts: {prompts}")

# Get random prompt
random_prompt = loader.get_random_prompt(child_age=8)
print(f"Random: {random_prompt}")
```

---

## Troubleshooting

### Prompts Not Loading

**Check file location:**
```bash
# Should be in project root
prompts/age_based_prompts.yaml
```

**Check YAML syntax:**
```bash
# Validate YAML
python -c "import yaml; yaml.safe_load(open('prompts/age_based_prompts.yaml'))"
```

### Placeholders Still Present

**Check for:**
- `[PLACEHOLDER]` in prompt text
- Empty prompts
- Very short prompts (< 5 characters)

These are automatically filtered out.

### Wrong Prompts for Age

**Check age group ranges:**
```yaml
early_childhood:
  age_range: [3, 6]  # Ages 3-6 inclusive
```

---

## Best Practices

### 1. Start Small
- Add 5-10 prompts per age group
- Test thoroughly
- Expand gradually

### 2. Regular Updates
- Add seasonal content
- Refresh stale prompts
- Track popular themes

### 3. Monitor Quality
- Review generated images
- Remove problematic prompts
- Keep prompt list curated

### 4. Version Control
- Track YAML changes in git
- Document major updates
- Keep backup of working versions

### 5. User Feedback
- Monitor what children enjoy
- Adjust prompts based on usage
- A/B test different approaches

---

## Migration Strategy

### Phase 1: Testing (Current)
- YAML has placeholders
- System uses speech text
- Test infrastructure

### Phase 2: Partial Rollout
- Add prompts for one age group
- Monitor behavior
- Gather feedback

### Phase 3: Full Deployment
- Add prompts for all age groups
- System uses curated content
- Speech text ignored

### Phase 4: Hybrid Approach
- Mix custom prompts with speech
- Use feature flags
- A/B test both modes

---

## FAQ

**Q: Do I have to add prompts?**  
A: No! If you don't add prompts (leave placeholders), the system uses children's speech. It's fully backwards compatible.

**Q: Can I mix modes (some age groups custom, others speech)?**  
A: Yes! Age groups with prompts use custom, others use speech.

**Q: How many prompts should I add?**  
A: Start with 10-20 per age group. You can always add more.

**Q: Can children still say what they want?**  
A: If using custom prompts, their speech is ignored. Use speech mode for creative freedom.

**Q: How do I switch between modes?**  
A: Edit the YAML file. Add prompts = custom mode. Remove prompts (placeholders) = speech mode.

**Q: Can I reload without restarting the server?**  
A: Yes! Call `get_prompt_loader().reload()` to hot-reload.

---

## Summary

The custom prompt system gives you **complete control** over sticker content:

✅ **Curated Mode:** Add prompts → quality control  
✅ **Dynamic Mode:** Keep placeholders → creative freedom  
✅ **Hybrid:** Mix both approaches per age group  
✅ **Hot-Reload:** Update prompts without restart  
✅ **Age-Appropriate:** Automatic style adaptation

**Default behavior:** Uses speech (backwards compatible)  
**When you're ready:** Add prompts for curated content
