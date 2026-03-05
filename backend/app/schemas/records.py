from __future__ import annotations

from pydantic import BaseModel


class RecordsImportResult(BaseModel):
    imported: int
    patient_id: int
