"""
Amazon Bedrock integration — optional.
Set BEDROCK_REGION and BEDROCK_MODEL_ID in .env to enable.
Falls back to deterministic extraction if credentials are not configured.
"""
from __future__ import annotations

import os
import json
import logging

logger = logging.getLogger(__name__)


def is_bedrock_configured() -> bool:
    """Returns True only when AWS credentials and region are explicitly set."""
    region = os.environ.get("BEDROCK_REGION", "").strip()
    return bool(region)


def extract_with_bedrock(text: str) -> dict:
    """
    Attempt LLM-assisted extraction using Amazon Bedrock Claude.
    Returns a dict with extracted invoice fields.
    Raises RuntimeError if Bedrock is not configured or the call fails.
    """
    if not is_bedrock_configured():
        raise RuntimeError("Bedrock not configured — set BEDROCK_REGION in .env")

    try:
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
    except ImportError:
        raise RuntimeError("boto3 not installed. Run: pip install boto3")

    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    prompt = f"""Extract invoice data from the following text as valid JSON only.
Return ONLY a JSON object with these keys (use null for missing values):
vendor_name, vendor_tax_id, invoice_number, invoice_date, due_date,
po_number, currency, subtotal, tax_amount, discount_amount, shipping_amount,
grand_total, payment_terms.

Invoice text:
{text[:6000]}

JSON:"""

    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        })
        response = client.invoke_model(modelId=model_id, body=body)
        raw = json.loads(response["body"].read())
        content = raw.get("content", [{}])[0].get("text", "{}")

        # Extract JSON block from response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {}

    except Exception as exc:
        logger.warning("Bedrock extraction failed: %s", exc)
        raise RuntimeError(f"Bedrock call failed: {exc}") from exc
