"""Google Document AI with complete results and explicit batch-resource ownership."""

import importlib.metadata
import os
import re
import sys
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pdfsmith._documents import pdf_page_count
from pdfsmith._inputs import validate_input
from pdfsmith.config import Option, normalize_options
from pdfsmith.errors import BackendOperationError

try:
    importlib.metadata.version("google-cloud-documentai")
    AVAILABLE = True
except importlib.metadata.PackageNotFoundError:
    AVAILABLE = False


class GoogleDocumentAIBackend:
    name = "google_document_ai"
    options_schema = {
        "project_id": Option(None, str, allow_none=True),
        "processor_id": Option(None, str, allow_none=True),
        "location": Option("us", str),
        "processor_version": Option(None, str, allow_none=True),
        "gcs_bucket": Option(None, str, allow_none=True),
        "mode": Option("auto", str, ("auto", "sync", "batch")),
        "max_wait": Option(600.0, float, minimum=0.001),
        "poll_interval": Option(1.0, float, minimum=0.001),
        "request_timeout": Option(60.0, float, minimum=0.001),
    }

    def __init__(self, **options: Any) -> None:
        explicit = {
            key: os.environ[env]
            for key, env in {
                "project_id": "GOOGLE_CLOUD_PROJECT",
                "processor_id": "GOOGLE_DOCUMENT_AI_PROCESSOR_ID",
                "location": "GOOGLE_CLOUD_LOCATION",
                "gcs_bucket": "GOOGLE_DOCUMENT_AI_GCS_BUCKET",
            }.items()
            if env in os.environ
        }
        self._options = normalize_options(
            self.name, {**explicit, **options}, self.options_schema
        )
        for key in ("project_id", "processor_id", "processor_version", "location"):
            value = self._options[key]
            if value is not None and not re.fullmatch(r"[A-Za-z0-9_-]+", value):
                raise ValueError(f"google_document_ai.{key} must be a resource ID")
        bucket = self._options["gcs_bucket"]
        if bucket is not None and not re.fullmatch(
            r"[a-z0-9][a-z0-9._-]{1,221}[a-z0-9]", bucket
        ):
            raise ValueError("google_document_ai.gcs_bucket must be a bucket name")

    @property
    def effective_options(self) -> dict[str, Any]:
        return deepcopy(self._options)

    def _create_client(self) -> Any:
        from google.api_core.client_options import ClientOptions
        from google.cloud import documentai_v1 as documentai

        return documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(
                api_endpoint=f"{self._options['location']}-documentai.googleapis.com"
            ),
            transport="rest",
        )

    def _create_storage(self) -> Any:
        import google.cloud.storage as storage

        return storage.Client(project=self._options["project_id"])

    def parse(self, pdf_path: Path) -> str:
        path = validate_input(pdf_path)
        count = pdf_page_count(path)
        size = path.stat().st_size
        batch = self._options["mode"] == "batch" or (
            self._options["mode"] == "auto" and (count > 15 or size > 40_000_000)
        )
        if (not batch and (count > 15 or size > 40_000_000)) or (
            batch and (count > 500 or size > 1_000_000_000)
        ):
            raise ValueError("PDF exceeds the selected Google OCR processing limits")
        if not self._options["project_id"] or not self._options["processor_id"]:
            raise RuntimeError("Google parsing requires project_id and processor_id")
        if batch and not self._options["gcs_bucket"]:
            raise RuntimeError("Google batch parsing requires gcs_bucket")
        name = (
            f"projects/{self._options['project_id']}/locations/{self._options['location']}"
            f"/processors/{self._options['processor_id']}"
        )
        if self._options["processor_version"]:
            name += f"/processorVersions/{self._options['processor_version']}"
        client = self._create_client()
        storage = None
        bucket = None
        prefix = ""
        content = None
        resources = {"processor": name}
        remote_possible = False
        terminal = False
        operation_name = ""
        timeout = self._options["request_timeout"]
        try:
            from google.cloud import documentai_v1 as documentai

            if not batch:
                response = client.process_document(
                    request=documentai.ProcessRequest(
                        name=name,
                        raw_document=documentai.RawDocument(
                            content=path.read_bytes(), mime_type="application/pdf"
                        ),
                        skip_human_review=True,
                    ),
                    retry=None,
                    timeout=timeout,
                )
                content = self._combine([response.document], count)
                return content
            storage = self._create_storage()
            bucket = storage.bucket(self._options["gcs_bucket"])
            prefix = f"pdfsmith-tmp/{uuid.uuid4().hex}/"
            input_name = prefix + "input.pdf"
            input_uri = f"gs://{bucket.name}/{input_name}"
            output_uri = f"gs://{bucket.name}/{prefix}output/"
            resources.update(input_gcs_uri=input_uri, output_gcs_uri=output_uri)
            bucket.blob(input_name).upload_from_filename(
                str(path),
                content_type="application/pdf",
                if_generation_match=0,
                retry=None,
                timeout=timeout,
            )
            remote_possible = True
            operation = client.batch_process_documents(
                request=documentai.BatchProcessRequest(
                    name=name,
                    input_documents=documentai.BatchDocumentsInputConfig(
                        gcs_documents=documentai.GcsDocuments(
                            documents=[
                                documentai.GcsDocument(
                                    gcs_uri=input_uri, mime_type="application/pdf"
                                )
                            ]
                        )
                    ),
                    document_output_config=documentai.DocumentOutputConfig(
                        gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                            gcs_uri=output_uri,
                            sharding_config=documentai.DocumentOutputConfig.GcsOutputConfig.ShardingConfig(
                                pages_per_shard=100, pages_overlap=0
                            ),
                        )
                    ),
                    skip_human_review=True,
                ),
                retry=None,
                timeout=timeout,
            )
            snapshot = operation.operation
            expected = (
                f"projects/{self._options['project_id']}/locations/"
                f"{self._options['location']}/operations/"
            )
            if (
                not snapshot.name.startswith(expected)
                or "/" in snapshot.name[len(expected) :]
                or not snapshot.name[len(expected) :]
            ):
                raise RuntimeError("Google returned an unexpected operation identity")
            operation_name = snapshot.name
            resources["operation"] = operation_name
            deadline = time.monotonic() + self._options["max_wait"]
            while not snapshot.done:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Google batch deadline exceeded")
                snapshot = client.transport.operations_client.get_operation(
                    operation_name, retry=None, timeout=min(timeout, remaining)
                )
                if snapshot.name != operation_name:
                    raise RuntimeError("Google changed the polled operation identity")
                if not snapshot.done:
                    time.sleep(
                        min(
                            self._options["poll_interval"],
                            max(0, deadline - time.monotonic()),
                        )
                    )
            terminal = True
            if snapshot.HasField("error"):
                raise RuntimeError(
                    f"Google batch failed ({snapshot.error.code}): "
                    f"{snapshot.error.message}"
                )
            if not snapshot.HasField("response"):
                raise RuntimeError("Google omitted its terminal batch response")
            metadata = documentai.BatchProcessMetadata()
            if not snapshot.metadata.Unpack(
                documentai.BatchProcessMetadata.pb(metadata)
            ):
                raise RuntimeError("Google omitted its typed batch metadata")
            if metadata.state != documentai.BatchProcessMetadata.State.SUCCEEDED:
                raise RuntimeError(
                    f"Google batch metadata failed: {metadata.state_message}"
                )
            statuses = metadata.individual_process_statuses
            if len(statuses) != 1 or statuses[0].input_gcs_source != input_uri:
                raise RuntimeError("Google returned mismatched document metadata")
            status = statuses[0]
            if status.status.code:
                raise RuntimeError(
                    f"Google document failed ({status.status.code}): "
                    f"{status.status.message}"
                )
            destination = status.output_gcs_destination
            if not destination.startswith(output_uri) or not destination.endswith("/"):
                raise RuntimeError("Google returned an unowned output destination")
            url = urlparse(destination)
            if (
                url.scheme != "gs"
                or url.netloc != bucket.name
                or url.query
                or url.fragment
            ):
                raise RuntimeError("Google returned an invalid output destination")
            blobs = list(
                bucket.list_blobs(
                    prefix=url.path.lstrip("/"), retry=None, timeout=timeout
                )
            )
            documents = []
            for blob in blobs:
                if not blob.name.startswith(
                    url.path.lstrip("/")
                ) or not blob.name.endswith(".json"):
                    raise RuntimeError("Google returned an unexpected output object")
                documents.append(
                    documentai.Document.from_json(
                        blob.download_as_bytes(retry=None, timeout=timeout),
                        ignore_unknown_fields=False,
                    )
                )
            content = self._combine(documents, count)
            return content
        except Exception as exc:
            from google.api_core import exceptions as google_errors

            if (
                remote_possible
                and not operation_name
                and isinstance(
                    exc,
                    google_errors.BadRequest
                    | google_errors.Unauthenticated
                    | google_errors.PermissionDenied
                    | google_errors.NotFound
                    | google_errors.ResourceExhausted,
                )
            ):
                terminal = True
            if remote_possible and not terminal:
                diagnostics = []
                if operation_name:
                    try:
                        # Document AI 3.16 REST overrides omit the cancel body binding.
                        transport = client.transport.operations_client.transport
                        for binding in transport._http_options[
                            "google.longrunning.Operations.CancelOperation"
                        ]:
                            binding["body"] = "*"
                        client.transport.operations_client.cancel_operation(
                            operation_name, retry=None, timeout=min(10.0, timeout)
                        )
                        snapshot = client.transport.operations_client.get_operation(
                            operation_name, retry=None, timeout=min(10.0, timeout)
                        )
                        terminal = snapshot.done and snapshot.name == operation_name
                    except Exception as cancel_error:
                        diagnostics.append(
                            f"cancellation: {type(cancel_error).__name__}: "
                            f"{cancel_error}"
                        )
                raise BackendOperationError(
                    "Google batch failed; cancellation was requested where possible",
                    resource_ids=resources,
                    completion_unknown=not terminal,
                    cleanup_errors=tuple(diagnostics),
                ) from exc
            raise
        finally:
            primary = sys.exc_info()[1]
            errors = []
            if bucket is not None and prefix and (not remote_possible or terminal):
                try:
                    owned = list(
                        bucket.list_blobs(prefix=prefix, retry=None, timeout=timeout)
                    )
                    for blob in owned:
                        if not blob.name.startswith(prefix):
                            raise RuntimeError(
                                "Google cleanup encountered an unowned object"
                            )
                        try:
                            blob.delete(
                                if_generation_match=blob.generation,
                                retry=None,
                                timeout=timeout,
                            )
                        except Exception as exc:
                            errors.append(
                                f"delete {blob.name}: {type(exc).__name__}: {exc}"
                            )
                except Exception as exc:
                    errors.append(f"list cleanup: {type(exc).__name__}: {exc}")
            closers = [("processor", client.transport)]
            if batch and remote_possible:
                closers.insert(
                    0,
                    (
                        "operations",
                        client.transport.operations_client.transport._session,
                    ),
                )
            if storage is not None:
                closers.insert(0, ("storage", storage))
            for label, owned_client in closers:
                try:
                    owned_client.close()
                except Exception as exc:
                    errors.append(f"{label}.close: {type(exc).__name__}: {exc}")
            if errors:
                if isinstance(primary, BackendOperationError):
                    errors = [*primary.cleanup_errors, *errors]
                raise BackendOperationError(
                    "Google resource cleanup failed",
                    parse_completed=content is not None,
                    recovered_content=content,
                    resource_ids=resources,
                    completion_unknown=remote_possible and not terminal,
                    cleanup_errors=tuple(errors),
                ) from primary

    @staticmethod
    def _combine(documents: list[Any], count: int) -> str:
        if not documents:
            raise RuntimeError("Google returned no document output")
        for document in documents:
            if document.error.code:
                raise RuntimeError(
                    f"Google document error ({document.error.code}): "
                    f"{document.error.message}"
                )
        sharded = any(document.shard_info.shard_count for document in documents)
        if sharded:
            documents = sorted(documents, key=lambda d: d.shard_info.shard_index)
            if any(d.shard_info.shard_count != len(documents) for d in documents) or [
                d.shard_info.shard_index for d in documents
            ] != list(range(len(documents))):
                raise RuntimeError(
                    "Google returned missing or duplicate document shards"
                )
            offset = 0
            for document in documents:
                if document.shard_info.text_offset != offset:
                    raise RuntimeError(
                        "Google returned overlapping or missing shard text"
                    )
                offset += len(document.text)
        elif len(documents) != 1:
            raise RuntimeError("Google omitted shard identity")
        if [page.page_number for d in documents for page in d.pages] != list(
            range(1, count + 1)
        ):
            raise RuntimeError(
                "Google returned incomplete or overlapping page coverage"
            )
        return "".join(document.text for document in documents).strip()
