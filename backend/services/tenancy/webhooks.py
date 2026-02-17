import logging

class WebhookDispatcher:
    def __init__(self):
        self.logger = logging.getLogger("CozyWebhooks")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def dispatch_event(self, event_name: str, payload: dict, partner_id: str = "B2B_PARTNER_X"):
        """
        Simulates pushing an event to a B2B partner's webhook endpoint.
        """
        # In real app: Validates URL, Signs payload (HMAC), POSTs with retries.
        # MVP: Log it.
        
        self.logger.info(f"✈️  [WEBHOOK] Dispatching '{event_name}' to {partner_id}")
        self.logger.info(f"    Payload: {payload}")
        
        # Validation simulation
        if not event_name or not payload:
            self.logger.error("    Failed: Invalid event data.")
            return False
            
        return True
