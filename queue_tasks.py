from celery import Celery
from typing import Dict
from utils.token_validator import TokenValidator


app = Celery('queue_tasks', broker='redis://localhost:6379/0')

# TODO: Set appropriate threshold values based on user's preferences and risk appetite
RISK_THRESHOLD = 0.7  # Example threshold for risk score

@app.task(bind=True, max_retries=3)
def process_token_alert(self, alert_data: Dict):
    """Process token alert through validation pipeline"""
    try:
        # Validate token
        validation_result = validate_token.delay(alert_data['contract_address'])
        
        if validation_result.get():
            # Check risk score
            risk_score = calculate_risk_score.delay(alert_data)
            
            if risk_score.get() < RISK_THRESHOLD:
                # Queue for trading
                execute_trade.delay(alert_data)
        
        return {"status": "processed", "contract": alert_data['contract_address']}
    
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@app.task
def execute_trade(contract_address: str):
    # Placeholder for logic to create a position on the given contract address
    print(f"Creating a position for contract address: {contract_address}")

@app.task
def validate_token(contract_address: str) -> bool:
    """Validate a token contract address.

    Args:
        contract_address (str): The contract address of the token to validate.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    validator = TokenValidator()
    validation_result = validator.validate_token(contract_address)
    is_valid = validation_result['is_valid']
    print(f"Token {contract_address} validation result: {is_valid}")
    return is_valid

@app.task
def calculate_risk_score(alert_data: Dict) -> float:
    """Calculate risk score for a token based on alert data.

    Args:
        alert_data (Dict): The alert data containing message text and other metadata.

    Returns:
        float: Risk score between 0 (low risk) and 1 (high risk).
    """
    validator = TokenValidator()
    risk_score = validator.calculate_risk_score(alert_data)
    return risk_score


