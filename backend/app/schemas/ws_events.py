from datetime import datetime

from pydantic import BaseModel


class WSEvent(BaseModel):
    type: str
    timestamp: str = ""
    pipeline_id: str | None = None
    payload: dict

    def model_post_init(self, __context):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
