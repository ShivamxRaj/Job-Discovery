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
    Record a behavioral event with its associated user and optional details.
    
    Parameters:
        event_name (str): Name of the event to record.
        user_id (int): Identifier of the user associated with the event.
        details (dict, optional): Additional event data. Defaults to an empty dictionary.
    """
    event_payload = {
        "event": event_name,
        "user_id": user_id,
        "details": details or {}
    }
    # Log as JSON string for easy parsing later
    beta_logger.info(json.dumps(event_payload))
