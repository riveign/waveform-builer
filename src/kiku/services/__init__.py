"""Use-cases — what the application can do, independent of who is asking.

Routes and the CLI are transports: they parse a request, call in here, and render
whatever comes back. Anything that would otherwise be written twice, once per
entry point, belongs in this package (docs/notes/OBS-006/K2).
"""
