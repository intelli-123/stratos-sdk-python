"""Side-effect entry so telemetry starts on import.

    import stratos_sdk.register   # put this as the FIRST import in your entrypoint
"""
from . import start

start()
