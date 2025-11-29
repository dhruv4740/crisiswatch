"""
WhatsApp Gateway Tool for CrisisWatch.
Receives and processes messages forwarded from WhatsApp.
"""

import hashlib
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from tools.base import BaseTool
from config import get_settings


class WhatsAppMessage(BaseModel):
    """Represents a WhatsApp message."""
    id: str
    text: str
    sender_phone: str  # Hashed for privacy
    timestamp: datetime
    is_forwarded: bool = False
    forward_count: Optional[int] = None  # If available from Business API
    media_type: Optional[str] = None  # image, video, audio, document
    group_name: Optional[str] = None
    language: str = "en"
    
    @property
    def virality_indicator(self) -> str:
        """Indicate potential virality based on forwarding."""
        if self.forward_count:
            if self.forward_count >= 5:
                return "high"
            elif self.forward_count >= 2:
                return "medium"
        if self.is_forwarded:
            return "medium"
        return "low"


class WhatsAppGatewayTool(BaseTool):
    """
    WhatsApp message gateway for receiving crisis-related messages.
    
    Integration options:
    1. WhatsApp Business API (requires Facebook Business verification)
    2. Webhook receiver for tip-line messages
    3. Manual submission through web form
    
    For hackathon demo, provides mock message handling.
    
    In production, this would integrate with:
    - Twilio WhatsApp API
    - Meta WhatsApp Business Platform
    - Open-source bridges (Baileys, whatsapp-web.js)
    """
    
    name = "whatsapp_gateway"
    description = "Receive and process WhatsApp messages for fact-checking"
    
    # Keywords that indicate potential misinformation
    MISINFO_INDICATORS = [
        "forward", "share", "urgent", "breaking",
        "confirmed", "100%", "guaranteed",
        "government said", "sources say", "insider",
        "before deleted", "viral", "shocking",
        # Hindi
        "forward karo", "share karo", "sach hai",
        "government ne kaha", "pakka", "confirmed",
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self._webhook_secret = getattr(self.settings, 'whatsapp_webhook_secret', '')
        self._message_buffer: list[WhatsAppMessage] = []
    
    @property
    def is_available(self) -> bool:
        # Gateway is always available for receiving messages
        return True
    
    def receive_message(
        self,
        text: str,
        sender_phone: str,
        timestamp: Optional[datetime] = None,
        is_forwarded: bool = False,
        group_name: Optional[str] = None,
    ) -> WhatsAppMessage:
        """
        Process an incoming WhatsApp message.
        
        Args:
            text: Message text content
            sender_phone: Sender's phone number (will be hashed)
            timestamp: Message timestamp
            is_forwarded: Whether message is forwarded
            group_name: Group name if from a group
            
        Returns:
            WhatsAppMessage object
        """
        # Hash phone number for privacy
        hashed_phone = hashlib.sha256(sender_phone.encode()).hexdigest()[:12]
        
        message = WhatsAppMessage(
            id=hashlib.sha256(f"{sender_phone}{text}{datetime.now()}".encode()).hexdigest()[:16],
            text=text,
            sender_phone=hashed_phone,
            timestamp=timestamp or datetime.now(),
            is_forwarded=is_forwarded or self._detect_forwarded(text),
            group_name=group_name,
            language=self._detect_language(text),
        )
        
        self._message_buffer.append(message)
        return message
    
    def get_pending_messages(self, limit: int = 50) -> list[WhatsAppMessage]:
        """
        Get pending messages for processing.
        
        Args:
            limit: Maximum messages to return
            
        Returns:
            List of WhatsAppMessage objects
        """
        messages = self._message_buffer[:limit]
        self._message_buffer = self._message_buffer[limit:]
        return messages
    
    def prioritize_messages(
        self,
        messages: list[WhatsAppMessage],
    ) -> list[WhatsAppMessage]:
        """
        Prioritize messages for fact-checking.
        
        Priority factors:
        1. Forwarded messages (higher virality risk)
        2. Contains misinformation indicators
        3. From groups (wider reach)
        
        Args:
            messages: List of messages to prioritize
            
        Returns:
            Sorted list with highest priority first
        """
        def priority_score(msg: WhatsAppMessage) -> int:
            score = 0
            
            # Forwarded messages get priority
            if msg.is_forwarded:
                score += 10
            if msg.forward_count and msg.forward_count >= 5:
                score += 20
            
            # Check for misinformation indicators
            text_lower = msg.text.lower()
            for indicator in self.MISINFO_INDICATORS:
                if indicator in text_lower:
                    score += 5
            
            # Group messages have wider reach
            if msg.group_name:
                score += 5
            
            return score
        
        return sorted(messages, key=priority_score, reverse=True)
    
    def _detect_forwarded(self, text: str) -> bool:
        """Detect if message appears to be forwarded."""
        # Common forwarding patterns
        patterns = [
            "forwarded as received",
            "fwd:",
            "fw:",
            "*forwarded*",
            "please forward",
            "share maximum",
            "send to all",
            # Hindi
            "aage bhejo",
            "sabko bhejo",
            "forward karo",
        ]
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in patterns)
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        # Count Devanagari characters
        devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        
        if devanagari_count > len(text) * 0.3:
            return "hi"
        return "en"
    
    def create_webhook_handler(self):
        """
        Create a webhook handler for receiving messages.
        
        This would be integrated with FastAPI in production:
        
        @app.post("/webhook/whatsapp")
        async def whatsapp_webhook(request: Request):
            gateway = WhatsAppGatewayTool()
            data = await request.json()
            message = gateway.receive_message(
                text=data["message"]["text"],
                sender_phone=data["from"],
                is_forwarded=data.get("forwarded", False),
            )
            return {"status": "received", "message_id": message.id}
        """
        pass
    
    def get_mock_messages(self) -> list[WhatsAppMessage]:
        """Get mock messages for demo purposes."""
        mock_data = [
            {
                "text": "🚨 URGENT: Government has ordered all banks to close for 2 weeks from Monday. Withdraw all your money NOW! Forwarded as received from bank manager.",
                "is_forwarded": True,
                "group_name": "Family Group",
            },
            {
                "text": "Breaking news: Drinking hot water with lemon and honey cures coronavirus in 24 hours. Doctor confirmed. Share to save lives! 🍋",
                "is_forwarded": True,
                "group_name": "Health Tips",
            },
            {
                "text": "दिल्ली में आज रात 3 बजे भूकंप आएगा। NASA ने confirm किया है। सभी को बाहर रहना चाहिए। Please forward to all family members.",
                "is_forwarded": True,
                "group_name": "Delhi NCR Updates",
            },
            {
                "text": "NDMA Update: Heavy rainfall expected in Mumbai over next 48 hours. Citizens advised to stay indoors. Helpline: 1070",
                "is_forwarded": False,
                "group_name": None,
            },
            {
                "text": "5G towers are spreading coronavirus! Many people living near towers are falling sick. Government is hiding this. EXPOSED!",
                "is_forwarded": True,
                "group_name": "Truth Seekers",
            },
        ]
        
        messages = []
        for i, data in enumerate(mock_data):
            messages.append(self.receive_message(
                text=data["text"],
                sender_phone=f"+91900000000{i}",
                is_forwarded=data["is_forwarded"],
                group_name=data.get("group_name"),
            ))
        
        return messages
