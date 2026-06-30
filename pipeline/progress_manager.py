"""
Progress Manager Module
Handles progress tracking, checkpointing and resuming for the code generator
Created: 2025-03-24 12:19:44
Author: Sakkibbb
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Set

# Configure logging
logger = logging.getLogger(__name__)

class ProgressManager:
    """
    Manages generation progress tracking and checkpointing
    to enable resumable generation and even distribution
    """
    
    def __init__(self, output_dir: str, total_examples: int):
        """
        Initialize the progress manager.
        
        Args:
            output_dir: Directory to store progress files
            total_examples: Total number of examples to generate
        """
        self.output_dir = output_dir
        self.total_examples = total_examples
        self.progress_file = os.path.join(output_dir, "generation_progress.json")
        self.checkpoint_file = os.path.join(output_dir, "generation_checkpoint.json")
        
        # Progress tracking data
        self.completed_examples = []
        self.completed_ids = set()
        self.completed_combinations = {}
        self.last_completed_id = None
        self.generation_started_at = None
        self.generation_resumed_at = None
        self.total_generated = 0
        self.successful = 0
        self.failed = 0
        self.category_distribution = {}
        self.complexity_distribution = {}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def initialize(self, reset: bool = False) -> bool:
        """
        Initialize progress tracking, either reset or load existing progress.
        
        Args:
            reset: If True, reset progress tracking. If False, try to load existing progress.
            
        Returns:
            True if successfully initialized, False otherwise
        """
        if reset:
            return self._reset_progress()
        else:
            return self._load_progress()
    
    def _reset_progress(self) -> bool:
        """Reset progress tracking."""
        self.completed_examples = []
        self.completed_ids = set()
        self.completed_combinations = {}
        self.last_completed_id = None
        self.generation_started_at = datetime.now().isoformat()
        self.generation_resumed_at = None
        self.total_generated = 0
        self.successful = 0
        self.failed = 0
        self.category_distribution = {}
        self.complexity_distribution = {}
        
        # Save initial progress
        return self.save_progress()
    
    def _load_progress(self) -> bool:
        """Load existing progress if available."""
        if not os.path.exists(self.progress_file):
            logger.info("No existing progress file found. Starting fresh.")
            return self._reset_progress()
        
        try:
            with open(self.progress_file, 'r', encoding="utf-8") as f:
                data = json.load(f)

            self._apply_progress_data(data)

            # Record resume time
            self.generation_resumed_at = datetime.now().isoformat()

            # Save progress with updated resume time
            self.save_progress()

            logger.info(f"Resumed progress: {self.total_generated}/{self.total_examples} examples generated")
            logger.info(f"Last completed ID: {self.last_completed_id}")

            return True
        except Exception as e:
            logger.error(f"Error loading progress: {str(e)}")

            # Back up the corrupt file BEFORE doing anything destructive so the
            # original content is never lost (data-loss safety).
            try:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backup_path = self.progress_file + f".corrupt-{timestamp}"
                # Avoid clobbering an existing backup if called twice in the same second.
                counter = 0
                while os.path.exists(backup_path):
                    counter += 1
                    backup_path = self.progress_file + f".corrupt-{timestamp}-{counter}"
                os.rename(self.progress_file, backup_path)
                logger.warning(f"Backed up corrupt progress file to {backup_path}")
            except Exception as backup_err:
                logger.error(f"Failed to back up corrupt progress file: {str(backup_err)}")

            # Try the checkpoint file as a fallback before giving up.
            if os.path.exists(self.checkpoint_file):
                try:
                    with open(self.checkpoint_file, 'r', encoding="utf-8") as f:
                        data = json.load(f)
                    self._apply_progress_data(data)
                    self.generation_resumed_at = datetime.now().isoformat()
                    self.save_progress()
                    logger.info("Recovered progress from checkpoint file.")
                    return True
                except Exception as cp_err:
                    logger.error(f"Error loading checkpoint fallback: {str(cp_err)}")

            logger.info("Starting fresh due to error loading progress.")
            return self._reset_progress()

    def _apply_progress_data(self, data: Dict[str, Any]) -> None:
        """Populate instance state from a loaded progress/checkpoint dict."""
        self.completed_examples = data.get("completed_examples", [])
        self.completed_ids = set(data.get("completed_ids", []))
        self.completed_combinations = data.get("completed_combinations", {})
        self.last_completed_id = data.get("last_completed_id")
        self.generation_started_at = data.get("generation_started_at")
        self.total_generated = data.get("total_generated", 0)
        self.successful = data.get("successful", 0)
        self.failed = data.get("failed", 0)
        self.category_distribution = data.get("category_distribution", {})
        self.complexity_distribution = data.get("complexity_distribution", {})
    
    def is_completed(self, example_id: str) -> bool:
        """Check if an example has already been completed."""
        return example_id in self.completed_ids
    
    def generate_report(self):
        """Generate a summary report of the generation process."""
        total_examples = len(self.completed_examples)
        logger.info(f"Generation Report:")
        logger.info(f"Total examples completed: {total_examples}")
        # Add additional statistics as needed
        return True
        
    def record_completion(self, example_data: Dict[str, Any], success: bool) -> None:
        """
        Record completion of an example.
        
        Args:
            example_data: Data about the completed example
            success: Whether generation was successful
        """
        md = example_data.get("metadata", {})
        example_id = md.get("id")
        category = md.get("category", "unknown")
        subcategory = md.get("subcategory", "unknown")
        complexity = example_data.get("complexity", "unknown")

        # A record with no id can't be tracked; skip it rather than crash.
        if example_id is None:
            logger.warning("record_completion called with no example id; skipping.")
            return

        # Skip if already completed
        if example_id in self.completed_ids:
            logger.warning(f"Example {example_id} already marked as completed.")
            return
        
        # Update counters
        self.total_generated += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1
        
        # Update distributions
        if category not in self.category_distribution:
            self.category_distribution[category] = {}
        if subcategory not in self.category_distribution[category]:
            self.category_distribution[category][subcategory] = {}
        if complexity not in self.category_distribution[category][subcategory]:
            self.category_distribution[category][subcategory][complexity] = 0
        
        self.category_distribution[category][subcategory][complexity] += 1
        
        if complexity not in self.complexity_distribution:
            self.complexity_distribution[complexity] = 0
        self.complexity_distribution[complexity] += 1
        
        # Record completion
        self.completed_ids.add(example_id)
        self.last_completed_id = example_id
        
        # Store completion data for combination tracking
        combination_key = f"{category}:{subcategory}:{complexity}"
        if combination_key not in self.completed_combinations:
            self.completed_combinations[combination_key] = 0
        self.completed_combinations[combination_key] += 1
        
        # Add to completed examples list
        completion_record = {
            "id": example_id,
            "category": category,
            "subcategory": subcategory,
            "complexity": complexity,
            "timestamp": datetime.now().isoformat(),
            "success": success
        }
        self.completed_examples.append(completion_record)
        
        # Save progress periodically (every 10 examples)
        if self.total_generated % 10 == 0:
            self.save_progress()
        
        # Create checkpoint periodically (every 50 examples)
        if self.total_generated % 50 == 0:
            self.create_checkpoint()
    
    def save_progress(self) -> bool:
        """Save current progress to file."""
        try:
            progress_data = {
                "generation_started_at": self.generation_started_at,
                "generation_resumed_at": self.generation_resumed_at,
                "last_updated_at": datetime.now().isoformat(),
                "total_examples": self.total_examples,
                "total_generated": self.total_generated,
                "successful": self.successful,
                "failed": self.failed,
                "last_completed_id": self.last_completed_id,
                "completed_ids": list(self.completed_ids),
                "completed_combinations": self.completed_combinations,
                "completed_examples": self.completed_examples,
                "category_distribution": self.category_distribution,
                "complexity_distribution": self.complexity_distribution
            }
            
            # Atomic write: write to a temp file in the same directory, then
            # os.replace() to atomically swap it into place. This prevents a
            # mid-write interrupt from corrupting the progress file used for resume.
            tmp_file = self.progress_file + ".tmp"
            with open(tmp_file, 'w', encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2)
            os.replace(tmp_file, self.progress_file)

            return True
        except Exception as e:
            logger.error(f"Error saving progress: {str(e)}")
            # Don't leave a half-written temp file behind.
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except Exception:
                pass
            return False
    
    def create_checkpoint(self) -> bool:
        """Create checkpoint file from current progress."""
        try:
            # Copy current progress file to checkpoint file atomically:
            # copy to a temp file in the same directory, then os.replace() it
            # into place so an interrupt can't leave a half-written checkpoint.
            tmp_file = self.checkpoint_file + ".tmp"
            if os.path.exists(self.progress_file):
                shutil.copy2(self.progress_file, tmp_file)
                os.replace(tmp_file, self.checkpoint_file)
                logger.info(f"Checkpoint created: {self.total_generated}/{self.total_examples} examples")
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating checkpoint: {str(e)}")
            # Don't leave a half-written temp file behind.
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except Exception:
                pass
            return False
    
    def get_category_counts(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        """Get counts of examples by category, subcategory, and complexity."""
        return self.category_distribution
    
    def get_complexity_counts(self) -> Dict[str, int]:
        """Get counts of examples by complexity."""
        return self.complexity_distribution
    
    def get_completion_percentage(self) -> float:
        """Get percentage completion of generation."""
        if self.total_examples <= 0:
            return 0.0
        return (self.total_generated / self.total_examples) * 100.0
    
    def get_success_rate(self) -> float:
        """Get success rate of generation."""
        if self.total_generated <= 0:
            return 0.0
        return (self.successful / self.total_generated) * 100.0
    
    def get_generation_time(self) -> Dict[str, Any]:
        """Get details about generation time."""
        started_at = None
        if self.generation_started_at:
            try:
                started_at = datetime.fromisoformat(self.generation_started_at)
            except Exception:
                pass
        
        current_time = datetime.now()
        
        if started_at:
            total_seconds = (current_time - started_at).total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            return {
                "started_at": self.generation_started_at,
                "resumed_at": self.generation_resumed_at,
                "current_time": current_time.isoformat(),
                "elapsed": {
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds,
                    "total_seconds": total_seconds
                }
            }
        
        return {
            "started_at": self.generation_started_at,
            "resumed_at": self.generation_resumed_at,
            "current_time": current_time.isoformat(),
            "elapsed": None
        }
    
    def get_next_example_ids(self, target_mix: Dict[str, float], 
                             tasks: List[Tuple[str, str, str]], 
                             batch_size: int = 50) -> List[str]:
        """
        Get the next un-completed task IDs in order.

        Returns the first ``batch_size`` task IDs (in the order they appear in
        ``tasks``) that have not yet been completed, i.e. simple FIFO selection.

        Args:
            target_mix: Accepted for API compatibility; not used for selection.
            tasks: List of (category, subcategory, ID) tuples from the task list.
            batch_size: Maximum number of IDs to return.

        Returns:
            List of the next un-completed example IDs, in order.
        """
        # Filter out already completed tasks, preserving original order.
        remaining_ids = [ex_id for _, _, ex_id in tasks
                         if ex_id not in self.completed_ids]

        if not remaining_ids:
            logger.info("No tasks remaining!")
            return []

        return remaining_ids[:batch_size]

# Test the progress manager if run directly
if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a test progress manager
    pm = ProgressManager("./test_output", 100)
    
    # Initialize (reset progress)
    pm.initialize(reset=True)
    
    # Record some completions
    for i in range(10):
        example_data = {
            "metadata": {
                "id": f"{i+1:04d}",
                "category": "sensors",
                "subcategory": "temperature",
            },
            "complexity": "beginner" if i % 2 == 0 else "intermediate"
        }
        pm.record_completion(example_data, success=True)
    
    # Print stats
    print(f"Completion: {pm.get_completion_percentage():.1f}%")
    print(f"Success rate: {pm.get_success_rate():.1f}%")
    print(f"Category counts: {pm.get_category_counts()}")
    print(f"Complexity counts: {pm.get_complexity_counts()}")