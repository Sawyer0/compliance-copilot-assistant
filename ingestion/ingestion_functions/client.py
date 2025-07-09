"""Inngest client configuration."""

import os
import logging
import inngest

# Create Inngest client for dev mode
inngest_client = inngest.Inngest(
    app_id="compliance-ingestion",
    logger=logging.getLogger("inngest"),
) 