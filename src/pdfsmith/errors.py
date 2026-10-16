"""Operational failures that preserve completed content and resource identity."""


class BackendOperationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        parse_completed: bool = False,
        recovered_content: str | None = None,
        resource_ids: dict[str, str] | None = None,
        completion_unknown: bool = False,
        cleanup_errors: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.parse_completed = parse_completed
        self.recovered_content = recovered_content
        self.resource_ids = dict(resource_ids or {})
        self.completion_unknown = completion_unknown
        self.cleanup_errors = cleanup_errors
