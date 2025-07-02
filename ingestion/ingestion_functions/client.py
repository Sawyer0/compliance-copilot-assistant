"""Inngest client configuration."""

import logging
import inngest

# Create Inngest client
inngest_client = inngest.Inngest(
    app_id="compliance-ingestion",
    logger=logging.getLogger("inngest"),
) 