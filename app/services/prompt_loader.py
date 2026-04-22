"""
Prompt Loader Service
=====================

Loads age-appropriate context prefixes from JSON configuration.
These prefixes are prepended to child's speech to add age-appropriate flavor.
"""

import json
from pathlib import Path
from typing import Optional, Dict


class PromptLoader:
    """Loads and manages age-based context prefixes from JSON configuration."""
    
    def __init__(self, prompts_file: str = "prompts/age_based_prompts.json"):
        """
        Initialize prompt loader.
        
        Args:
            prompts_file: Path to JSON file relative to project root
        """
        self.prompts_file = prompts_file
        self._prompts_data: Optional[Dict] = None
        self._loaded = False  # Track if we've attempted to load
    
    def _get_project_root(self) -> Path:
        """Get the project root directory (where prompts/ folder is)."""
        # Start from current file location and go up to project root
        current_file = Path(__file__).resolve()
        # Go up from app/services/ to root
        return current_file.parent.parent.parent
    
    def _ensure_loaded(self):
        """Lazy load prompts from JSON file (only once)."""
        if self._loaded:
            return  # Already loaded (or attempted to load)
        
        self._loaded = True  # Mark as loaded to prevent re-loading
        
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
    
    def _is_valid_context(self, context: str) -> bool:
        """Check if a context prefix is valid (not a placeholder)."""
        if not context:
            return False
        context_lower = context.lower().strip()
        return not (
            "[add your context" in context_lower or
            "[placeholder]" in context_lower or
            context_lower.startswith("[") and context_lower.endswith("]")
        )
    
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
    
    def get_context_prefix(self, child_age: Optional[int] = None) -> Optional[str]:
        """
        Get the context prefix for the given age group.
        
        This prefix gets prepended to the child speech to add age-appropriate flavor.
        
        Args:
            child_age: Child age in years
        
        Returns:
            Context prefix string, or None if not configured
            
        Examples:
            loader.get_context_prefix(5) returns 'simple and cute'
            Child says "a dragon"
            Final prompt: "simple and cute a dragon" + style modifiers
        """
        self._ensure_loaded()  # Lazy load on first access
        
        if not self._prompts_data:
            return None
        
        # Check if context prefix is enabled
        settings = self._prompts_data.get("settings", {})
        if not settings.get("enable_context_prefix", True):
            return None
        
        age_group_key = self._get_age_group_key(child_age)
        
        try:
            age_groups = self._prompts_data.get("age_groups", {})
            age_group_data = age_groups.get(age_group_key, {})
            context = age_group_data.get("context_prefix", "")
            
            # Check if context is valid (not a placeholder)
            if self._is_valid_context(context):
                return context.strip()
            else:
                return None
        
        except Exception as e:
            print(f"Error getting context prefix: {e}")
            return None
    
    def reload(self):
        """Reload prompts from JSON file (useful for hot-reloading config)."""
        self._loaded = False  # Reset loaded flag
        self._ensure_loaded()  # Force reload


# Global instance (singleton pattern)
_prompt_loader_instance: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get or create the global prompt loader instance."""
    global _prompt_loader_instance
    
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    
    return _prompt_loader_instance

