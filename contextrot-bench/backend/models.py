from cognee.infrastructure.engine import DataPoint
from typing import Optional, Dict, Any, List

class Fact(DataPoint):
    subject: str
    predicate: str
    value: str
    timestamp: str
    supersedes: Optional[str] = None
    metadata: Dict[str, Any] = {"index_fields": ["subject", "predicate", "value"]}
