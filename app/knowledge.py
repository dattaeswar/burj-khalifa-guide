"""
app/knowledge.py - Knowledge base loader and manager.
Loads the extracted Markdown knowledge base, section chunks, and compiles the system prompt.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("burj_guide.knowledge")

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system.md"
DATA_DIR = BASE_DIR / "data"
KB_MD_PATH = DATA_DIR / "knowledge_base.md"
CHUNKS_JSON_PATH = DATA_DIR / "chunks.json"


class KnowledgeManager:
    def __init__(self):
        self.system_prompt_template: str = ""
        self.knowledge_base_text: str = ""
        self.compiled_system_prompt: str = ""
        self.chunks: list[dict] = []
        self._loaded: bool = False
        self.load()

    def load(self):
        """Load knowledge base and system prompt."""
        try:
            # If files don't exist, trigger ingest
            if not KB_MD_PATH.exists() or not CHUNKS_JSON_PATH.exists():
                logger.info("Knowledge base files missing, triggering ingestion...")
                import ingest
                ingest.run_ingestion()

            # Read system prompt template
            if SYSTEM_PROMPT_PATH.exists():
                with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                    self.system_prompt_template = f.read()
            else:
                self.system_prompt_template = "You are the Burj Khalifa Guide.\n\n{knowledge_base}"

            # Read knowledge base markdown
            with open(KB_MD_PATH, "r", encoding="utf-8") as f:
                self.knowledge_base_text = f.read()

            # Read chunks JSON
            with open(CHUNKS_JSON_PATH, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)

            # Compile system prompt
            self.compiled_system_prompt = self.system_prompt_template.replace(
                "{knowledge_base}", self.knowledge_base_text
            )

            self._loaded = bool(self.compiled_system_prompt and self.chunks)
            logger.info("Knowledge base successfully loaded with %d sections.", len(self.chunks))

        except Exception as e:
            logger.error("Failed to load knowledge base: %s", e)
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_system_prompt(self) -> str:
        return self.compiled_system_prompt

    def get_chunks(self) -> list[dict]:
        return self.chunks


# Singleton instance
kb_manager = KnowledgeManager()
