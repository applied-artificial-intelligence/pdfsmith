"""Real Google REST/storage SDKs connected to an in-memory HTTP adapter."""

import base64
import hashlib
import io
import json
from email.parser import BytesParser
from urllib.parse import parse_qs, unquote, urlparse


def google_clients(case="complete"):
    import requests
    from google.auth.credentials import AnonymousCredentials
    from google.auth.transport.requests import AuthorizedSession
    from google.cloud import documentai_v1 as documentai
    from google.cloud import storage
    from google.cloud.documentai_v1.services import (
        document_processor_service as service,
    )

    class Wire(requests.adapters.BaseAdapter):
        def __init__(self):
            self.calls = []
            self.objects = {}
            self.input_uri = None
            self.output_uri = None
            self.closed = 0
            self.polls = 0
            self.cancelled = False
            self.input_count = 2
            self.upload_name = None
            self.uploaded = bytearray()

        def close(self):
            self.closed += 1
            if case == "close-error":
                raise RuntimeError("Controlled Google transport close error")

        def document(self, page, text, index=None):
            result = {
                "text": text,
                "pages": [{"pageNumber": page}],
                "mimeType": "application/pdf",
            }
            if index is not None:
                result["shardInfo"] = {
                    "shardIndex": str(index),
                    "shardCount": "2",
                    "textOffset": str(
                        0 if index == 0 else len("FIRST PAGE SENTINEL\n")
                    ),
                }
            if case == "text-gap" and index == 1:
                result["shardInfo"]["textOffset"] = "999"
            if case == "duplicate-page" and index == 1:
                result["pages"][0]["pageNumber"] = 1
            if case == "document-error":
                result["error"] = {"code": 3, "message": "Controlled document error"}
            return result

        def operation(self, done):
            op = {
                "name": "projects/offline/locations/us/operations/owned-job",
                "done": done,
            }
            metadata = {
                "@type": (
                    "type.googleapis.com/"
                    "google.cloud.documentai.v1.BatchProcessMetadata"
                ),
                "state": "SUCCEEDED" if done else "RUNNING",
            }
            if done:
                metadata["individualProcessStatuses"] = [
                    {
                        "inputGcsSource": self.input_uri,
                        "status": {"code": 3 if case == "individual-error" else 0},
                        "outputGcsDestination": self.output_uri + "owned-job/0/",
                    }
                ]
                if case == "wrong-destination":
                    metadata["individualProcessStatuses"][0]["outputGcsDestination"] = (
                        "gs://other-bucket/unowned/"
                    )
                op["response"] = {
                    "@type": (
                        "type.googleapis.com/"
                        "google.cloud.documentai.v1.BatchProcessResponse"
                    )
                }
            if done and case == "metadata-failed":
                metadata["state"] = "FAILED"
            if done and case == "missing-status":
                metadata["individualProcessStatuses"] = []
            if done and case == "wrong-source":
                metadata["individualProcessStatuses"][0]["inputGcsSource"] = (
                    "gs://unowned/file.pdf"
                )
            if done and case == "terminal-error":
                op.pop("response", None)
                op["error"] = {"code": 3, "message": "Controlled failed batch"}
            if done and case == "missing-response":
                op.pop("response", None)
            if self.cancelled and case == "cancel-complete":
                op["done"] = True
                op["error"] = {"code": 1, "message": "Cancelled"}
            if case == "wrong-operation" and self.polls:
                op["name"] = "projects/offline/locations/us/operations/other-job"
            op["metadata"] = metadata
            return op

        def send(self, request, **kwargs):
            from pypdf import PdfReader

            self.calls.append({"method": request.method, "url": request.url})
            url = urlparse(request.url)
            body = request.body
            if isinstance(body, bytes):
                body = body.decode(
                    "latin1" if url.path.startswith("/upload/") else "utf-8"
                )
            result = {}
            status = 200
            if url.path.endswith(":process"):
                data = json.loads(body)
                assert data["rawDocument"]["mimeType"] == "application/pdf"
                pdf = base64.b64decode(data["rawDocument"]["content"])
                count = len(PdfReader(io.BytesIO(pdf)).pages)
                result = {
                    "document": {
                        "text": "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL",
                        "pages": [{"pageNumber": n} for n in range(1, count + 1)],
                    }
                }
                if case == "document-error":
                    result["document"]["error"] = {
                        "code": 3,
                        "message": "Controlled document error",
                    }
                if case == "blank":
                    result["document"]["text"] = ""
                if case == "missing-pages":
                    result["document"]["pages"] = []
            elif url.path.endswith(":batchProcess"):
                data = json.loads(body)
                self.input_uri = data["inputDocuments"]["gcsDocuments"]["documents"][0][
                    "gcsUri"
                ]
                self.output_uri = data["documentOutputConfig"]["gcsOutputConfig"][
                    "gcsUri"
                ]
                prefix = self.output_uri.split("/", 3)[3] + "owned-job/0/"
                # Deliberately reverse filename order; service metadata defines order.
                self.objects[prefix + "z-first.json"] = self.document(
                    1, "FIRST PAGE SENTINEL\n", 0
                )
                self.objects[prefix + "a-final.json"] = self.document(
                    2, "FINAL PAGE SENTINEL", 1
                )
                middle = (self.input_count + 1) // 2
                self.objects[prefix + "z-first.json"]["pages"] = [
                    {"pageNumber": n} for n in range(1, middle + 1)
                ]
                self.objects[prefix + "a-final.json"]["pages"] = [
                    {"pageNumber": n} for n in range(middle + 1, self.input_count + 1)
                ]
                if case == "duplicate-page":
                    self.objects[prefix + "a-final.json"]["pages"][0]["pageNumber"] = 1
                if case == "missing-shard":
                    del self.objects[prefix + "z-first.json"]
                if case == "duplicate-shard":
                    self.objects[prefix + "duplicate.json"] = self.document(
                        1, "FIRST PAGE SENTINEL\n", 0
                    )
                result = self.operation(False)
                if case in {"submit-error", "ambiguous-submit"}:
                    status = 400 if case == "submit-error" else 500
                    result = {
                        "error": {"code": status, "message": "Controlled submit error"}
                    }
            elif "/operations/" in url.path:
                if url.path.endswith(":cancel"):
                    self.calls[-1]["cancel"] = True
                    self.cancelled = True
                    if case == "cancel-error":
                        status = 403
                        result = {
                            "error": {
                                "code": status,
                                "message": "Controlled cancellation failure",
                            }
                        }
                else:
                    self.polls += 1
                    result = self.operation(
                        case not in {"timeout", "cancel-error", "cancel-complete"}
                    )
            elif url.path.startswith("/upload/resumable/"):
                import struct

                import google_crc32c

                assert request.method == "PUT"
                self.uploaded.extend(request.body)
                payload = bytes(self.uploaded)
                self.input_count = len(PdfReader(io.BytesIO(payload)).pages)
                self.calls[-1]["input_sha256"] = hashlib.sha256(payload).hexdigest()
                self.objects[self.upload_name] = None
                result = {
                    "name": self.upload_name,
                    "bucket": "offline-bucket",
                    "generation": "1",
                    "crc32c": base64.b64encode(
                        struct.pack(">I", google_crc32c.value(payload))
                    ).decode(),
                }
            elif url.path.startswith("/upload/") and parse_qs(url.query).get(
                "uploadType"
            ) == ["resumable"]:
                self.upload_name = json.loads(body)["name"]
            elif url.path.startswith("/upload/"):
                # The real storage SDK supplies a multipart PDF upload.
                assert "%PDF-" in body
                query = parse_qs(url.query)
                name = query.get("name", [None])[0]
                if name is None:
                    for line in body.splitlines():
                        if line.startswith("{"):
                            name = json.loads(line)["name"]
                            break
                assert name
                mime = request.headers["Content-Type"]
                if isinstance(mime, str):
                    mime = mime.encode()
                message = BytesParser().parsebytes(
                    b"Content-Type: " + mime + b"\r\n\r\n" + request.body
                )
                payload = next(
                    part.get_payload(decode=True)
                    for part in message.walk()
                    if part.get_content_type() == "application/pdf"
                )
                self.input_count = len(PdfReader(io.BytesIO(payload)).pages)
                self.calls[-1]["input_sha256"] = hashlib.sha256(payload).hexdigest()
                self.objects[name] = None
                result = {"name": name, "bucket": "offline-bucket", "generation": "1"}
            elif "/o/" in url.path:
                name = unquote(url.path.split("/o/", 1)[1])
                if request.method == "DELETE":
                    if case == "delete-error":
                        status = 403
                        result = {
                            "error": {"code": 403, "message": "Controlled delete error"}
                        }
                    else:
                        self.objects.pop(name, None)
                        status = 204
                else:
                    result = self.objects[name]
            elif url.path.endswith("/o"):
                prefix = parse_qs(url.query)["prefix"][0]
                result = {
                    "items": [
                        {
                            "name": k,
                            "bucket": "offline-bucket",
                            "generation": "1",
                            "contentType": "application/json",
                        }
                        for k in sorted(self.objects)
                        if k.startswith(prefix)
                    ]
                }
            else:
                raise AssertionError(
                    f"Unexpected Google request: {request.method} {request.url}"
                )
            response = requests.Response()
            response.status_code = status
            response.url = request.url
            response.request = request
            response.headers["content-type"] = "application/json"
            if url.path.startswith("/upload/") and parse_qs(url.query).get(
                "uploadType"
            ) == ["resumable"]:
                response.headers["location"] = (
                    "https://storage.googleapis.com/upload/resumable/offline-upload"
                )
            response._content = json.dumps(result).encode() if status != 204 else b""
            response.raw = io.BytesIO(response._content)
            response.raw.headers = response.headers
            return response

    wire = Wire()
    transport = service.transports.DocumentProcessorServiceRestTransport(
        host="us-documentai.googleapis.com", credentials=AnonymousCredentials()
    )
    transport._session.mount("https://", wire)
    transport.operations_client.transport._session.mount("https://", wire)
    processor = documentai.DocumentProcessorServiceClient(transport=transport)
    session = AuthorizedSession(AnonymousCredentials())
    session.mount("https://", wire)
    objects = storage.Client(
        project="offline", credentials=AnonymousCredentials(), _http=session
    )
    return processor, objects, wire
