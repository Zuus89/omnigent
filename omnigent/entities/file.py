"""File entity."""

from dataclasses import dataclass


@dataclass
class StoredFile:
    """
    A stored file with metadata.

    :param id: Unique file identifier (bare 32-char hex), e.g. ``"abc123"``.
    :param created_at: Unix epoch timestamp of upload.
    :param filename: Original filename, e.g. ``"report.pdf"``.
    :param bytes: File size in bytes.
    :param content_type: MIME type, e.g. ``"application/pdf"``.
    :param session_id: Owning session/conversation id when the file
        is session-scoped, e.g. ``"abc123"``. ``None`` for
        historical unscoped records created before session-scoped
        file resources were introduced.
    """

    id: str
    created_at: int
    filename: str
    bytes: int
    content_type: str | None = None
    session_id: str | None = None
