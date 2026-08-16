"""Ownership timeline API (alias router with timeline prefix)."""
from app.api.ownership import router  # re-export; endpoints live under /cases/{id}/timeline

router = router
