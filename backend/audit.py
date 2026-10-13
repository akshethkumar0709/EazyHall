import hashlib
import json
from sqlalchemy.orm import Session
from models import AuditLog
import datetime

def calculate_log_hash(prev_hash: str, timestamp: datetime.datetime, tenant_id: int, user_id: int, action: str, details: str) -> str:
    """
    Computes a SHA-256 hash representing a single log block, chaining it to the previous hash.
    """
    # Use isoformat to have a stable string representation of the timestamp
    ts_str = timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else str(timestamp)
    
    payload = f"{prev_hash}|{ts_str}|{tenant_id}|{user_id}|{action}|{details}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def add_audit_log(db: Session, tenant_id: int, user_id: int, action: str, details: dict) -> AuditLog:
    """
    Adds a new audit log to the hash chain.
    """
    # Fetch last log to get previous hash
    last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = last_log.hash if last_log else "genesis_block_0000000000000000000000"
    
    timestamp = datetime.datetime.utcnow()
    details_str = json.dumps(details, sort_keys=True)
    
    curr_hash = calculate_log_hash(
        prev_hash=prev_hash,
        timestamp=timestamp,
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        details=details_str
    )
    
    log_entry = AuditLog(
        timestamp=timestamp,
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        details=details_str,
        prev_hash=prev_hash,
        hash=curr_hash
    )
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def verify_audit_chain(db: Session) -> dict:
    """
    Verifies the integrity of the audit logs hash-chain.
    Returns a dict with 'valid' status and any error/tampering details.
    """
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not logs:
        return {"valid": True, "message": "No logs to verify"}
    
    expected_prev_hash = "genesis_block_0000000000000000000000"
    
    for i, log in enumerate(logs):
        # 1. Check link to previous hash
        if log.prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "error": "Link broken",
                "log_id": log.id,
                "action": log.action,
                "details": f"Log #{log.id} has incorrect prev_hash. Expected: {expected_prev_hash}, Got: {log.prev_hash}"
            }
        
        # 2. Recalculate hash and verify match
        recalculated_hash = calculate_log_hash(
            prev_hash=log.prev_hash,
            timestamp=log.timestamp,
            tenant_id=log.tenant_id,
            user_id=log.user_id,
            action=log.action,
            details=log.details
        )
        
        if log.hash != recalculated_hash:
            return {
                "valid": False,
                "error": "Hash mismatch",
                "log_id": log.id,
                "action": log.action,
                "details": f"Log #{log.id} details or hash have been altered. Stored: {log.hash}, Recalculated: {recalculated_hash}"
            }
            
        expected_prev_hash = log.hash
        
    return {"valid": True, "count": len(logs), "message": "All audit log signatures verified successfully."}
