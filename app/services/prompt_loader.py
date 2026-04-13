"""
Prompt Loader Service
=====================

Loads custom prompts from JSON configuration file.
Provides random selection from age-appropriate prompt collections.
"""

import json
import random
from pathlib import Path
from typing import Optional, List, Dict


class PromptLoader:
    """Loads and manages age-based prompts from JSON configuration."""
    
    def __init__(self, prompts_file: str = "prompts/age_based_prompts.json"):
        """
        Initialize prompt loader.
        
        Args:
            prompts_file: Path to JSON file relative to project root
        """
        self.prompts_file = prompts_file
        self._prompts_data: Optional[Dict] = None
        self._load_prompts()
    
    def _get_project_root(self) -> Path:
        """Get the project root directory (where prompts/ folder is)."""
        # Start from current file location and go up to project root
        current_file = Path(__file__).resolve()
        # Go up from app/services/ to root
        return current_file.parent.parent.parent
    
    def _load_prompts(self):
        """Load prompts from JSON file."""
        try:
            project_root = self._get_project_root()
            json_path = project_root / self.prompts_file
            
            if not json_path.exists():
                print(f"Prompts file not found: {json_path}")
                self._prompts_data = None
                return
            
            with open(json_path, 'r', encoding='utf-8') as f:
                self._prompts_data = json.load(f)
            
            print(f"Successfully loaded prompts from {json_path}")
            
        except Exception as e:
            print(f"Error loading prompts file: {e}")
            self._prompts_data = None
    
    def _is_placeholder(self, prompt: str) -> bool:
        """Check if a prompt is a placeholder."""
        if not prompt:
            return True
        prompt_lower = prompt.lower().strip()
        return (
            "[placeholder]" in prompt_lower or
            prompt_lower.startswith("[") and prompt_lower.endswith("]") or
            len(prompt_lower) < 5
        )
    
    def _filter_placeholders(self, prompts: List[str]) -> List[str]:
        """Remove placeholder prompts from list."""
        return [p for p in prompts if not self._is_placeholder(p)]
    
    def _get_age_group_key(self, child_age: Optional[int]) -> str:
        """Map child age to age group key."""
        if child_age is None:
            return "middle_childhood"
        
        if 3 <= child_age <= 6:
            return "early_childhood"
        elif 7 <= child_age <= 9:
            return "middle_childhood"
        elif 10 <= child_age <= 12:
            return "late_childhood"
        else:
            return "teen"
    
    def get_random_prompt(self, child_age: Optional[int] = None) -> Optional[str]:
        """
        Get a random prompt for the given age group.
        
        Args:
            child_age: Child's age in years
        
        Returns:
            Random prompt string, or None if no prompts available
        """
        if not self._prompts_data:
            return None
        
        age_group_key = self._get_age_group_key(child_age)
        
        try:
            age_groups = self._prompts_data.get("age_groups", {})
            age_group_data = age_groups.get(age_group_key, {})
            prompts = age_group_data.get("prompts", [])
            
            # Filter out placeholders
            valid_prompts = self._filter_placeholders(prompts)
            
            if not valid_prompts:
                return None
            
            # Check shuffle setting
            settings = self._prompts_data.get("settings", {})
            if settings.get("shuffle_prompts", True):
                return random.choice(valid_prompts)
            else:
                return valid_prompts[0]
        
        except Exception as e:
            print(f"Error getting random prompt: {e}")
            return None
    
    def get_all_prompts(self, child_age: Optional[int] = None) -> List[str]:
        """
        Get all prompts for the given age group.
        
        Args:
            child_age: Child's age in years
        
        Returns:
            List of prompts (excluding placeholders)
        """
        if not self._prompts_data:
            return []
        
        age_group_key = self._get_age_group_key(child_age)
        
        try:
            age_groups = self._prompts_data.get("age_groups", {})
            age_group_data = age_groups.get(age_group_key, {})
            prompts = age_group_data.get("prompts", [])
            
            return self._filter_placeholders(prompts)
        
        except Exception as e:
            print(f"Error getting prompts: {e}")
            return []
    
    def has_valid_prompts(self, child_age: Optional[int] = None) -> bool:
        """
        Check if there are valid (non-placeholder) prompts for age group.
        
        Args:
            child_age: Child's age in years
        
        Returns:
            True if valid prompts exist
        """
        return len(self.get_all_prompts(child_age)) > 0
    
    def reload(self):
        """Reload prompts from JSON file (useful for hot-reloading config)."""
        self._load_prompts()


# Global instance (singleton pattern)
_prompt_loader_instance: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get or create the global prompt loader instance."""
    global _prompt_loader_instance
    
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    
    return _prompt_loader_instance
