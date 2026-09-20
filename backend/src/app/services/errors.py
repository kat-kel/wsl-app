# Domain errors raised by the service layer
#
# Raised instead of HTTPException so that callers which are not HTTP -- the CSV
# load job -- get the same rules without importing FastAPI.


class UnknownReference(Exception):
    """A record refers to a country or team that does not exist."""
