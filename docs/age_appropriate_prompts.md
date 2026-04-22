# Age-Appropriate Prompt Generation

## Overview

The WonderBox backend automatically adapts sticker complexity and style based on the child's age, ensuring developmentally appropriate coloring content.

## Age Groups

### 🧒 Early Childhood (3-6 years)

**Characteristics:**
- Very simple shapes and concepts
- Large, chunky elements
- Extra thick outlines for easy coloring
- Wide spacing between elements
- Basic familiar objects (animals, toys, food)

**Example Prompts:**
```
Input: "a cat"
Output: "a cat, very simple, large shapes, minimal details, chunky outlines, 
         extra thick lines, black and white line drawing, coloring book style, 
         bold outlines, white background, clean lines, wide spacing between elements"
```

**Why this matters:**
- Fine motor skills are still developing
- Attention span is shorter
- Need clear, recognizable shapes
- Fewer details = less frustration

---

### 👧 Middle Childhood (7-9 years)

**Characteristics:**
- Moderate complexity
- Action scenes and characters
- Medium detail level
- Balanced spacing
- Clear distinct shapes

**Example Prompts:**
```
Input: "a dragon fighting a knight"
Output: "a dragon fighting a knight, moderate, medium detail, clear distinct shapes,
         thick lines, black and white line drawing, coloring book style,
         bold outlines, white background, clean lines, balanced spacing"
```

**Why this matters:**
- Motor skills improving
- Can handle more detail
- Enjoys narratives and action
- Building confidence in coloring

---

### 🧑 Late Childhood (10-12 years)

**Characteristics:**
- Detailed and intricate
- Complex patterns and textures
- Fine details
- Creative concepts and fantasy themes
- Medium line weights

**Example Prompts:**
```
Input: "a princess in an enchanted forest"
Output: "a princess in an enchanted forest, detailed, fine details, 
         intricate patterns, textures, medium lines, black and white line drawing,
         coloring book style, bold outlines, white background, clean lines, 
         compact spacing"
```

**Why this matters:**
- Advanced fine motor skills
- Seeks creative challenges
- Can focus for longer periods
- Appreciates complexity

---

### 🧔 Teen (12+ years)

**Characteristics:**
- Complex and sophisticated
- Realistic proportions
- Varied line weights
- Advanced concepts
- Manga/anime style options
- Dense composition

**Example Prompts:**
```
Input: "an anime character with magical powers"
Output: "an anime character with magical powers, complex, sophisticated details,
         realistic proportions, shading guides, varied line weights, 
         black and white line drawing, coloring book style, bold outlines,
         white background, clean lines, dense composition"
```

**Why this matters:**
- Fully developed motor skills
- Artistic expression important
- Seeks sophisticated content
- May pursue art as hobby

---

## Implementation Details

### How Age is Determined

```python
# In the database, each child has a date_of_birth field
class Child(Base):
    __tablename__ = "children"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    date_of_birth = Column(Date)  # ← Used to calculate age
```

### Age Calculation

```python
# In the orchestrator, age is calculated from date of birth
if child.date_of_birth:
    today = datetime.now().date()
    age_delta = today - child.date_of_birth
    child_age = age_delta.days // 365
```

### Prompt Building

```python
from app.services.prompt_builder import build_sticker_prompt

# Automatically adapts based on age
prompt = build_sticker_prompt("a flying dragon", child_age=8)
```

---

## API Integration

The age-appropriate prompt generation is **automatic** in the sticker pipeline:

```
1. Child speaks → Device sends audio + child_id
2. Backend validates child + calculates age from date_of_birth
3. STT converts speech to text: "a flying dragon"
4. Prompt builder creates age-appropriate prompt
5. Image API generates coloring book image
6. Device receives age-appropriate sticker
```

**No additional API calls needed!** The system automatically uses the child's age from the database.

---

## Parent App Integration

### When Creating a Child Profile

```json
POST /children
{
  "name": "Emma",
  "date_of_birth": "2016-03-15",  // Will be 10 years old
  "parent_id": 123
}
```

### Viewing Child's Age Group

```python
from app.services.prompt_builder import get_age_group_info

age_info = get_age_group_info(child_age=10)
# Returns:
{
    "name": "Late Childhood (10-12 years)",
    "range": (10, 12),
    "complexity": "detailed",
    "themes": "creative concepts, fantasy, storytelling",
    "details": "fine details, intricate patterns, textures"
}
```

---

## Testing

### Run Age Group Examples

```bash
python test_prompt_ages.py
```

This will show:
- All age group configurations
- Example prompts for different ages
- How the same input adapts across age groups

### Manual Testing

```python
from app.services.prompt_builder import build_sticker_prompt

# Test different ages
ages = [4, 8, 11, 14]
for age in ages:
    prompt = build_sticker_prompt("a cat", child_age=age)
    print(f"Age {age}: {prompt}")
```

---

## Benefits

### For Children

✅ **Frustration-free** - Age-appropriate complexity prevents frustration  
✅ **Confidence building** - Success at their skill level builds confidence  
✅ **Developmental support** - Matches their motor skill development  
✅ **Engaging content** - Themes that interest their age group

### For Parents

✅ **Automatic** - No manual settings needed  
✅ **Grows with child** - Automatically adapts as child ages  
✅ **Educational** - Supports skill development  
✅ **Peace of mind** - Content appropriate for their child

### For the Business

✅ **Better retention** - Kids stay engaged longer  
✅ **Age targeting** - Can market to specific age groups  
✅ **Differentiation** - Unique feature vs competitors  
✅ **Scalability** - Same system works for all ages

---

## Future Enhancements

### Possible Additions:

1. **Skill Level Override**
   - Let parents manually adjust if child is advanced/behind
   - `child.skill_level = "advanced"` → use next age group

2. **Theme Preferences**
   - Track what themes child likes (animals, vehicles, fantasy)
   - Enhance prompts with preferred themes

3. **Learning Mode**
   - Start simpler, gradually increase complexity
   - Track completion rate and adjust

4. **Seasonal Themes**
   - Holiday-appropriate content
   - Educational themes (letters, numbers for younger kids)

5. **Multi-Language Support**
   - Age-appropriate vocabulary in different languages
   - Cultural context for themes

---

## Configuration

Age group boundaries can be adjusted in [prompt_builder.py](../app/services/prompt_builder.py):

```python
_AGE_GROUPS = {
    "early_childhood": {
        "range": (3, 6),  # ← Adjust age boundaries here
        "complexity": "very simple",
        # ... other settings
    },
    # ... other age groups
}
```

---

## FAQ

**Q: What if date_of_birth is not set?**  
A: Defaults to middle childhood (7-9 years) as a safe middle ground.

**Q: Can parents see what age group their child is in?**  
A: Yes, use `get_age_group_info(child_age)` in the API to show this in the parent app.

**Q: Does this work with device without parent app?**  
A: Child profile must exist in database with date_of_birth to calculate age.

**Q: What about kids on the age boundary (e.g., exactly 6)?**  
A: Age 6 falls in early childhood (3-6 range). At age 7 they move to the next group.

**Q: Can we override the age group for a specific request?**  
A: Currently no, but could add `age_override` parameter if needed.

---

## Summary

Age-appropriate prompt generation ensures every child gets coloring content that matches their developmental stage, making WonderBox engaging for ages 3-16+. The system is automatic, requiring only a child's date of birth in the database.

**The result:** Happier kids, happier parents, better retention! 🎨
