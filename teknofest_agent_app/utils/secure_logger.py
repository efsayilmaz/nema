import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class SecureAuditLogger:
    """
    Hash-chained (Blockchain mantığı) Append-Only Denetim Logu.
    Geriye dönük silinme ve değiştirilmeyi kriptografik olarak engeller.
    """
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit_chain.jsonl"
        self.last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        if not self.log_file.exists():
            return "0" * 64  # Genesis hash
        
        with open(self.log_file, "rb") as f:
            try:
                # Dosyanın son satırını oku
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b'\n':
                    f.seek(-2, os.SEEK_CUR)
                last_line = f.readline().decode()
                last_record = json.loads(last_line)
                return last_record.get("hash", "0" * 64)
            except Exception:
                return "0" * 64

    def log_action(self, actor: str, action: str, document_id: str, purpose: str, details: Dict[str, Any]):
        """Denetim kaydı oluşturur."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        record_content = {
            "timestamp": timestamp,
            "actor": actor,          # İşlemi yapan rol/kullanıcı (örn: auditor, sysadmin, agent)
            "action": action,        # Yapılan işlem (READ_ARCHIVE, APPROVE_DRAFT, DELETE_REQUEST)
            "document_id": document_id, 
            "purpose": purpose,      # Amaç Sınırlaması: Veriye neden erişildi?
            "details": details,
            "previous_hash": self.last_hash
        }
        
        # İçeriğin hash'ini al (SHA-256)
        content_string = json.dumps(record_content, sort_keys=True)
        current_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
        
        record = {**record_content, "hash": current_hash}
        
        # Append-Only modunda kaydet
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
        self.last_hash = current_hash
        return current_hash

# Global Singleton Logger
audit_logger = SecureAuditLogger()
