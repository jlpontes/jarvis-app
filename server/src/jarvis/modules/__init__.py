"""Os módulos do Jarvis. `build_registry()` é o único lugar que lista todos eles."""

from jarvis.core.registry import ModuleRegistry
from jarvis.modules.tasks.module import TasksModule


def build_registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.add(TasksModule())
    return registry
