"""Compatibility facade for GCC knowledge loaders."""

from gcc_agent.knowledge.loaders import (
    PROJECTS_PATH,
    VALUES_PATH,
    as_gcc_summary_block,
    as_system_block,
    load_projects,
    load_values,
    reload_values,
)

__all__ = [
    "PROJECTS_PATH",
    "VALUES_PATH",
    "as_gcc_summary_block",
    "as_system_block",
    "load_projects",
    "load_values",
    "reload_values",
]
