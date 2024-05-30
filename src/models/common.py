import datetime as dt

from beanie import Document, after_event, Replace, SaveChanges, Update, ValidateOnSave
from pydantic import Field


class DateMetadataDocument(Document):
    """DateMetadataDocument provides created and updated time fields, and sets the correct `updated_time` each time the
    model instance is modified."""

    created_time: dt.datetime = Field(default_factory=dt.datetime.now)
    updated_time: dt.datetime = Field(default_factory=dt.datetime.now)

    @after_event(Update, Replace, SaveChanges, ValidateOnSave)
    def update_document_time(self) -> None:
        self.updated_time = dt.datetime.now()
