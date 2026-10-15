"""Real SDK offline wire adapters for OCR contract verification."""

import base64
import json
import struct
import zlib


def first_png_pixel(data):
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[25] == 2, "Expected RGB from the page renderer"
    width, height = struct.unpack(">II", data[16:24])
    assert max(width, height) <= 10000
    offset = 8
    chunks = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        if data[offset + 4 : offset + 8] == b"IDAT":
            chunks.append(data[offset + 8 : offset + 8 + length])
        offset += length + 12
    raw = zlib.decompress(b"".join(chunks))
    # The first pixel has zero left/upper predictors for every standard PNG filter.
    return tuple(raw[1:4])


def aws_client(case="complete"):
    import boto3
    from botocore.awsrequest import AWSResponse

    class Raw:
        def __init__(self, data):
            self.data = data

        def stream(self, *a, **kw):
            yield self.data

    class Transport:
        def __init__(self):
            self.calls = []
            self.closed = False

        def send(self, request):
            assert request.headers["X-Amz-Target"] == b"Textract.DetectDocumentText"
            body = json.loads(request.body)
            data = base64.b64decode(body["Document"]["Bytes"], validate=True)
            color = first_png_pixel(data)
            self.calls.append(dict(color=color, byte_count=len(data)))
            if case in {"late-error", "late-and-close-error"} and len(self.calls) == 2:
                status = 400
                response = {
                    "__type": "InvalidParameterException",
                    "Message": "Controlled second-page rejection",
                }
            else:
                status = 200
                blocks = [{"BlockType": "PAGE", "Id": "offline-page", "Page": 1}]
                text = {
                    (255, 0, 0): "FIRST PAGE SENTINEL",
                    (0, 0, 255): "FINAL PAGE SENTINEL",
                }.get(color)
                if text:
                    blocks.append(
                        {
                            "BlockType": "LINE",
                            "Id": "offline-line",
                            "Text": text,
                            "Page": 1,
                        }
                    )
                response = {"DocumentMetadata": {"Pages": 1}, "Blocks": blocks}
                if case == "missing-pages":
                    response["Blocks"] = []
                if case == "missing-text":
                    response["Blocks"].append(
                        {"BlockType": "LINE", "Id": "invalid-line", "Page": 1}
                    )
            return AWSResponse(
                request.url,
                status,
                {
                    "content-type": "application/x-amz-json-1.1",
                    "x-amzn-requestid": f"offline-request-{len(self.calls)}",
                },
                Raw(json.dumps(response).encode()),
            )

        def close(self):
            self.closed = True
            if case in {
                "close-error",
                "late-and-close-error",
                "failed-and-delete-error",
                "timeout-and-close-error",
            }:
                raise OSError("Controlled AWS close failure")

    client = boto3.session.Session().client(
        "textract",
        region_name="us-east-1",
        aws_access_key_id="offline-key",
        aws_secret_access_key="offline-secret",
    )
    transport = Transport()
    client._endpoint.http_session = transport
    return client, transport


def azure_client(case="complete"):
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    from azure.core.pipeline.transport import HttpResponse, HttpTransport
    from azure.core.utils import case_insensitive_dict

    class Response(HttpResponse):
        def __init__(self, request, status, data, headers=None):
            super().__init__(request, None)
            self.status_code = status
            self.headers = case_insensitive_dict(
                {"content-type": "application/json", **(headers or {})}
            )
            self.content_type = "application/json"
            self._body = json.dumps(data).encode()
            self.closed = False

        def body(self):
            return self._body

        def read(self):
            return self._body

        def json(self):
            return json.loads(self._body)

        def stream_download(self, *a, **kw):
            yield self._body

        def iter_bytes(self, *a, **kw):
            yield self._body

        def close(self):
            self.closed = True

    class Transport(HttpTransport):
        def __init__(self):
            self.calls = []
            self.closed = False
            self.polls = 0

        def open(self):
            pass

        def close(self):
            self.closed = True
            if case in {
                "close-error",
                "late-and-close-error",
                "failed-and-delete-error",
                "timeout-and-close-error",
            }:
                raise OSError("Controlled Azure close failure")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.close()

        def send(self, request, **kw):
            body = request.body
            if hasattr(body, "read"):
                body = body.read()
            self.calls.append(dict(method=request.method, url=request.url, body=body))
            if request.method == "POST":
                assert body.startswith(b"%PDF-")
                assert request.headers["Content-Type"] == "application/octet-stream"
                model = (
                    "prebuilt-layout"
                    if "prebuilt-layout" in request.url
                    else "prebuilt-read"
                )
                self.model = model
                self.format = (
                    "markdown"
                    if "outputContentFormat=markdown" in request.url
                    else "text"
                )
                location = f"https://offline.azure.invalid/documentintelligence/documentModels/{model}/analyzeResults/offline-job?api-version=2024-11-30"
                if case == "wrong-location":
                    location = location.replace(
                        "offline.azure.invalid", "unowned.invalid"
                    )
                return Response(
                    request,
                    202,
                    {},
                    {"Operation-Location": location, "Retry-After": "0"},
                )
            if request.method == "DELETE":
                if case in {"delete-error", "failed-and-delete-error"}:
                    return Response(
                        request,
                        403,
                        {
                            "error": {
                                "code": "Forbidden",
                                "message": "Controlled deletion failure",
                            }
                        },
                    )
                return Response(request, 204, {})
            self.polls += 1
            if case in {"timeout", "timeout-and-close-error"} or (
                case == "running" and self.polls == 1
            ):
                return Response(request, 200, {"status": "running"})
            if case in {"failed", "failed-and-delete-error"}:
                return Response(
                    request,
                    200,
                    {
                        "status": "failed",
                        "error": {
                            "code": "InvalidContent",
                            "message": "Controlled parse failure",
                        },
                    },
                )
            pages = [
                {
                    "pageNumber": 1,
                    "width": 612,
                    "height": 792,
                    "unit": "point",
                    "spans": [],
                },
                {
                    "pageNumber": 2,
                    "width": 612,
                    "height": 792,
                    "unit": "point",
                    "spans": [],
                },
            ]
            content = "FIRST PAGE SENTINEL\nFINAL PAGE SENTINEL"
            if self.format == "markdown":
                content = "# FIRST PAGE SENTINEL\n\nFINAL PAGE SENTINEL"
            if case == "missing-pages":
                pages = pages[:1]
            if case == "blank":
                content = ""
            if case == "missing-text":
                content = None
            result = {
                "apiVersion": "2024-11-30",
                "modelId": self.model,
                "stringIndexType": "unicodeCodePoint",
                "contentFormat": self.format,
                "content": content,
                "pages": pages,
            }
            return Response(
                request, 200, {"status": "succeeded", "analyzeResult": result}
            )

    transport = Transport()
    client = DocumentIntelligenceClient(
        "https://offline.azure.invalid",
        AzureKeyCredential("offline-key"),
        transport=transport,
        retry_total=0,
        polling_interval=0,
    )
    return client, transport
