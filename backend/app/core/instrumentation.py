import logging
import json

# Configure a specific logger for Beta 0 behavioral events
beta_logger = logging.getLogger("beta_events")
beta_logger.setLevel(logging.INFO)

# Optional: Add a file handler to store these events separately for analysis
# handler = logging.FileHandler("beta_events.log")
# handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
# beta_logger.addHandler(handler)

def log_event(event_name: str, user_id: int, details: dict = None):
    """
    Log a behavioral event for Beta 0 runtime evidence collection.
    
    Expected events:
    - Recommendation Viewed
    - Recommendation Clicked
    - Job Saved
    - Apply Clicked
    - Resume Uploaded
    - Resume Parse Failed
    - Recommendation Generated
    - Explanation Displayed
    - Explanation Hidden (confidence gate)
    """
    event_payload = {
        "event": event_name,
        "user_id": user_id,
        "details": details or {}
    }
    # Log as JSON string for easy parsing later
    beta_logger.info(json.dumps(event_payload))
