import logging
from datetime import datetime


audit_logger = logging.getLogger("agri_audit")


def log_audit(action: str, entity: str, user_id: int | None = None, record_id: int | None = None, details: str = ""):
    timestamp = datetime.utcnow().isoformat()
    audit_logger.info(
        "[%s] action=%s entity=%s user_id=%s record_id=%s details=%s",
        timestamp,
        action,
        entity,
        user_id,
        record_id,
        details,
    )
