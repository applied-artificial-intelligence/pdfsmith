"""Client cleanup that keeps extraction failures and completed content visible."""

from typing import Any

from pdfsmith.errors import BackendOperationError


def close_client(
    client: Any,
    backend: str,
    *,
    content: str | None,
    resource_ids: dict[str, str],
    primary: BaseException | None,
    completion_unknown: bool = False,
) -> None:
    try:
        client.close()
    except Exception as exc:
        errors: tuple[str, ...] = (f"client.close: {type(exc).__name__}: {exc}",)
        if isinstance(primary, BackendOperationError):
            errors = (*primary.cleanup_errors, *errors)
            completion_unknown |= primary.completion_unknown
            resource_ids = {**primary.resource_ids, **resource_ids}
            if content is None and primary.parse_completed:
                content = primary.recovered_content
        raise BackendOperationError(
            f"{backend} client cleanup failed",
            parse_completed=content is not None,
            recovered_content=content,
            resource_ids=resource_ids,
            completion_unknown=completion_unknown,
            cleanup_errors=errors,
        ) from (primary or exc)
