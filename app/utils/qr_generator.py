"""
QR Code Generator Utility
"""

import time


def generate_qr_code(group_id: int) -> str:
    """
    Generate unique QR code for a group
    Format: RQ-{group_id}-{timestamp}
    
    Args:
        group_id: Group ID
        
    Returns:
        QR code string
    """
    timestamp = int(time.time() * 1000)  # Milliseconds
    return f"RQ-{group_id}-{timestamp}"