"""Databricks ai_parse_document backend for pdfsmith.

Databricks provides document parsing via SQL warehouse and ai_parse_document function.

Requirements:
    - databricks-sdk

Configuration:
    Set DATABRICKS_HOST (workspace URL), DATABRICKS_CLIENT_ID and
    DATABRICKS_CLIENT_SECRET (OAuth M2M credentials).

Cost: ~$3.00 per 1,000 pages (estimated, based on SQL warehouse DBU consumption)
Limits: Varies by warehouse configuration
"""

import base64
import json
from pathlib import Path

try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementState

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from pdfsmith.backends.registry import BaseBackend


class DatabricksBackend(BaseBackend):
    """Databricks ai_parse_document backend for pdfsmith."""

    name = "databricks"

    def __init__(self) -> None:
        """Initialize Databricks backend."""
        if not AVAILABLE:
            raise ImportError(
                "databricks-sdk is required for Databricks parser. "
                "Install with: pip install databricks-sdk"
            )

        import os

        host = os.getenv("DATABRICKS_HOST")
        client_id = os.getenv("DATABRICKS_CLIENT_ID")
        client_secret = os.getenv("DATABRICKS_CLIENT_SECRET")
        warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")

        if not host:
            raise RuntimeError(
                "DATABRICKS_HOST must be set. "
                "Format: https://<workspace-id>.cloud.databricks.com"
            )

        if not client_id or not client_secret:
            raise RuntimeError(
                "DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET must be set. "
                "Create a service principal in your Databricks workspace."
            )

        # Initialize SDK client (uses OAuth M2M automatically)
        self.client = WorkspaceClient()

        # Auto-detect warehouse if not specified
        if not warehouse_id:
            warehouse_id = self._get_warehouse_id()

        self.warehouse_id = warehouse_id

    def _get_warehouse_id(self) -> str:
        """Get SQL warehouse ID, preferring serverless."""
        warehouses = list(self.client.warehouses.list())
        if not warehouses:
            raise ValueError(
                "No SQL warehouses found. "
                "Create a serverless SQL warehouse in Databricks."
            )

        # Prefer serverless
        for wh in warehouses:
            if wh.name and "serverless" in wh.name.lower() and wh.id:
                return wh.id

        # Use first available
        if warehouses[0].id:
            return warehouses[0].id

        raise ValueError("No usable SQL warehouse found")

    def parse(self, pdf_path: Path) -> str:
        """Parse PDF to markdown using Databricks ai_parse_document.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown text

        Raises:
            RuntimeError: If SQL execution fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Read and encode PDF
        pdf_bytes = pdf_path.read_bytes()
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Execute SQL with ai_parse_document
        sql = f"""
        SELECT ai_parse_document('{pdf_base64}', 'base64') as result
        """

        try:
            # Execute statement
            statement = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=sql,
                wait_timeout="30s",
            )

            # Wait for completion
            if statement.status and statement.status.state == StatementState.SUCCEEDED:
                # Extract result
                if statement.result and statement.result.data_array:
                    result_json = statement.result.data_array[0][0]
                    return self._parse_result(result_json)
                else:
                    return ""
            else:
                error_msg = (
                    statement.status.error.message
                    if statement.status and statement.status.error
                    else "Unknown error"
                )
                raise RuntimeError(f"Databricks SQL execution failed: {error_msg}")

        except Exception as e:
            raise RuntimeError(f"Databricks parsing failed: {e}") from e

    def _parse_result(self, result_json: str) -> str:
        """Parse ai_parse_document JSON result to markdown."""
        try:
            result = json.loads(result_json)

            # Extract text from structured result
            text_blocks = []

            if "elements" in result:
                for element in result["elements"]:
                    if "text" in element:
                        text_blocks.append(element["text"])

            return "\n\n".join(text_blocks).strip()

        except json.JSONDecodeError:
            # If not JSON, return as-is
            return result_json
