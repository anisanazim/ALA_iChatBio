from pathlib import Path

CAPABILITIES_DIR = Path(__file__).parent / "capabilities"


class ToolCapabilityRegistry:
    """
    Loads tool capability docs from markdown files at startup.
    Single source of truth for what each tool does.

    Used by:
    - ALAPlanner: get_all_for_planner() → injected into system prompt
    - Documentation generators
    - Eval harnesses
    - Future coordinator agents
    """

    def __init__(self):
        self._capabilities: dict[str, str] = {}
        self._load_all()

    def _load_all(self):
        for path in sorted(CAPABILITIES_DIR.glob("*.md")):
            tool_name = path.stem
            self._capabilities[tool_name] = path.read_text(encoding="utf-8")

    def get(self, tool_name: str) -> str:
        """Get capability doc for a single tool."""
        return self._capabilities.get(tool_name, "")

    def get_all_for_planner(self) -> str:
        """
        Returns all capability docs formatted for injection
        into the planner system prompt.
        """
        sections = []
        for content in self._capabilities.values():
            sections.append(content)
        return "\n\n---\n\n".join(sections)

    @property
    def tool_names(self) -> list[str]:
        """Returns list of all registered tool names."""
        return list(self._capabilities.keys())


# Singleton — import and use directly
registry = ToolCapabilityRegistry()