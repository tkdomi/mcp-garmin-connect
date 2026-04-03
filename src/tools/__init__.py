from src.tools import health, training

ALL_TOOLS = health.TOOL_DEFINITIONS + training.TOOL_DEFINITIONS


async def dispatch(name: str, arguments: dict):
    for module in [health, training]:
        result = await module.handle(name, arguments)
        if result is not None:
            return result
    return None
