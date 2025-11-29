"""
Notification Service for CrisisWatch.
Handles sending alerts via SMS, Email, Webhook, and other channels.
"""

import httpx
from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from models.schemas import FactCheckResult, VerdictType, SeverityLevel
from config import get_settings


class NotificationChannel(str, Enum):
    """Available notification channels."""
    SMS = "sms"
    EMAIL = "email"
    WEBHOOK = "webhook"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    TELEGRAM = "telegram"


class NotificationPayload(BaseModel):
    """Payload for notifications."""
    claim_id: str
    claim_text: str
    verdict: str
    severity: str
    correction: Optional[str] = None
    explanation_short: str
    source_url: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class NotificationResult(BaseModel):
    """Result of a notification attempt."""
    channel: NotificationChannel
    success: bool
    message: str
    recipient: Optional[str] = None
    sent_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BaseNotificationProvider(ABC):
    """Abstract base class for notification providers."""
    
    channel: NotificationChannel
    
    @abstractmethod
    async def send(
        self,
        payload: NotificationPayload,
        recipient: str,
        **kwargs,
    ) -> NotificationResult:
        """Send a notification."""
        pass
    
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass


class SMSProvider(BaseNotificationProvider):
    """
    SMS notification provider.
    
    Supports:
    - Twilio
    - TextLocal (India)
    - MSG91 (India)
    """
    
    channel = NotificationChannel.SMS
    
    def __init__(self):
        self.settings = get_settings()
        # These would be loaded from settings in production
        self._twilio_sid = getattr(self.settings, 'twilio_account_sid', '')
        self._twilio_token = getattr(self.settings, 'twilio_auth_token', '')
        self._twilio_from = getattr(self.settings, 'twilio_phone_number', '')
    
    @property
    def is_configured(self) -> bool:
        return bool(self._twilio_sid and self._twilio_token and self._twilio_from)
    
    async def send(
        self,
        payload: NotificationPayload,
        recipient: str,
        **kwargs,
    ) -> NotificationResult:
        """
        Send SMS notification.
        
        Args:
            payload: Notification content
            recipient: Phone number (with country code)
        """
        if not self.is_configured:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="SMS provider not configured",
                recipient=recipient,
            )
        
        # Format message for SMS (160 char limit ideally)
        message = self._format_sms(payload)
        
        try:
            # Twilio API call (stubbed for now)
            # In production, use twilio library:
            # from twilio.rest import Client
            # client = Client(self._twilio_sid, self._twilio_token)
            # message = client.messages.create(body=message, from_=self._twilio_from, to=recipient)
            
            # Stub implementation
            print(f"[SMS] Would send to {recipient}: {message[:50]}...")
            
            return NotificationResult(
                channel=self.channel,
                success=True,
                message="SMS sent successfully (stub)",
                recipient=recipient,
            )
            
        except Exception as e:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message=f"SMS failed: {str(e)}",
                recipient=recipient,
            )
    
    def _format_sms(self, payload: NotificationPayload) -> str:
        """Format payload for SMS."""
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "ℹ️",
            "low": "📝",
        }
        emoji = severity_emoji.get(payload.severity, "📢")
        
        if payload.correction:
            return f"{emoji} CrisisWatch Alert: {payload.correction}"
        else:
            return f"{emoji} CrisisWatch: Claim rated {payload.verdict.upper()}. {payload.explanation_short[:80]}"


class EmailProvider(BaseNotificationProvider):
    """
    Email notification provider.
    
    Supports:
    - SendGrid
    - SMTP
    - AWS SES
    """
    
    channel = NotificationChannel.EMAIL
    
    def __init__(self):
        self.settings = get_settings()
        self._sendgrid_key = getattr(self.settings, 'sendgrid_api_key', '')
        self._from_email = getattr(self.settings, 'notification_email_from', 'alerts@crisiswatch.dev')
    
    @property
    def is_configured(self) -> bool:
        return bool(self._sendgrid_key)
    
    async def send(
        self,
        payload: NotificationPayload,
        recipient: str,
        subject: Optional[str] = None,
        **kwargs,
    ) -> NotificationResult:
        """
        Send email notification.
        
        Args:
            payload: Notification content
            recipient: Email address
            subject: Email subject (optional)
        """
        if not self.is_configured:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="Email provider not configured",
                recipient=recipient,
            )
        
        subject = subject or f"CrisisWatch Alert: {payload.severity.upper()} - Misinformation Detected"
        html_body = self._format_email_html(payload)
        
        try:
            # SendGrid API call (stubbed)
            # In production:
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            # sg = SendGridAPIClient(self._sendgrid_key)
            # mail = Mail(from_email=self._from_email, to_emails=recipient, subject=subject, html_content=html_body)
            # sg.send(mail)
            
            print(f"[EMAIL] Would send to {recipient}: {subject}")
            
            return NotificationResult(
                channel=self.channel,
                success=True,
                message="Email sent successfully (stub)",
                recipient=recipient,
            )
            
        except Exception as e:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message=f"Email failed: {str(e)}",
                recipient=recipient,
            )
    
    def _format_email_html(self, payload: NotificationPayload) -> str:
        """Format payload as HTML email."""
        severity_colors = {
            "critical": "#DC2626",
            "high": "#F59E0B",
            "medium": "#3B82F6",
            "low": "#10B981",
        }
        color = severity_colors.get(payload.severity, "#6B7280")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 20px; text-align: center;">
                <h1>🛡️ CrisisWatch Alert</h1>
                <p style="font-size: 18px;">Severity: {payload.severity.upper()}</p>
            </div>
            <div style="padding: 20px;">
                <h2>Claim Detected</h2>
                <blockquote style="border-left: 4px solid {color}; padding-left: 16px; font-style: italic;">
                    {payload.claim_text}
                </blockquote>
                
                <h3>Verdict: <span style="color: {color};">{payload.verdict.upper()}</span></h3>
                
                <h3>Explanation</h3>
                <p>{payload.explanation_short}</p>
                
                {"<h3>Correction</h3><p><strong>" + payload.correction + "</strong></p>" if payload.correction else ""}
                
                <hr style="margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">
                    This alert was generated by CrisisWatch at {payload.timestamp}.
                    <br>Claim ID: {payload.claim_id}
                </p>
            </div>
        </body>
        </html>
        """


class WebhookProvider(BaseNotificationProvider):
    """
    Webhook notification provider.
    
    Sends JSON payloads to configured endpoints.
    Useful for integrating with external systems.
    """
    
    channel = NotificationChannel.WEBHOOK
    
    def __init__(self):
        self.settings = get_settings()
    
    @property
    def is_configured(self) -> bool:
        # Webhooks are always "configured" - just need a URL
        return True
    
    async def send(
        self,
        payload: NotificationPayload,
        recipient: str,  # URL endpoint
        headers: Optional[dict] = None,
        **kwargs,
    ) -> NotificationResult:
        """
        Send webhook notification.
        
        Args:
            payload: Notification content
            recipient: Webhook URL
            headers: Optional HTTP headers
        """
        if not recipient.startswith(("http://", "https://")):
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="Invalid webhook URL",
                recipient=recipient,
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    recipient,
                    json=payload.model_dump(),
                    headers=headers or {"Content-Type": "application/json"},
                )
                response.raise_for_status()
            
            return NotificationResult(
                channel=self.channel,
                success=True,
                message=f"Webhook delivered (status {response.status_code})",
                recipient=recipient,
            )
            
        except httpx.HTTPStatusError as e:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message=f"Webhook failed: HTTP {e.response.status_code}",
                recipient=recipient,
            )
        except Exception as e:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message=f"Webhook failed: {str(e)}",
                recipient=recipient,
            )


class SlackProvider(BaseNotificationProvider):
    """Slack notification provider using incoming webhooks."""
    
    channel = NotificationChannel.SLACK
    
    def __init__(self):
        self.settings = get_settings()
        self._webhook_url = getattr(self.settings, 'slack_webhook_url', '')
    
    @property
    def is_configured(self) -> bool:
        return bool(self._webhook_url)
    
    async def send(
        self,
        payload: NotificationPayload,
        recipient: str = "",  # Channel name (optional, uses webhook default)
        **kwargs,
    ) -> NotificationResult:
        """Send Slack notification."""
        if not self.is_configured:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="Slack webhook not configured",
                recipient=recipient,
            )
        
        slack_payload = self._format_slack_blocks(payload)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self._webhook_url,
                    json=slack_payload,
                )
                response.raise_for_status()
            
            return NotificationResult(
                channel=self.channel,
                success=True,
                message="Slack message sent",
                recipient=recipient or "default channel",
            )
            
        except Exception as e:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message=f"Slack failed: {str(e)}",
                recipient=recipient,
            )
    
    def _format_slack_blocks(self, payload: NotificationPayload) -> dict:
        """Format as Slack Block Kit message."""
        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "ℹ️",
            "low": "📝",
        }
        emoji = severity_emoji.get(payload.severity, "📢")
        
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} CrisisWatch Alert - {payload.severity.upper()}",
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Claim:*\n>{payload.claim_text[:200]}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Verdict:*\n{payload.verdict.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{payload.severity.upper()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Explanation:*\n{payload.explanation_short[:300]}"
                    }
                },
            ]
        }


class NotificationService:
    """
    Main notification service that orchestrates sending across channels.
    """
    
    def __init__(self):
        self.providers = {
            NotificationChannel.SMS: SMSProvider(),
            NotificationChannel.EMAIL: EmailProvider(),
            NotificationChannel.WEBHOOK: WebhookProvider(),
            NotificationChannel.SLACK: SlackProvider(),
        }
    
    def create_payload(self, result: FactCheckResult, claim_id: str) -> NotificationPayload:
        """Create notification payload from fact-check result."""
        return NotificationPayload(
            claim_id=claim_id,
            claim_text=result.claim.text,
            verdict=result.verdict.value,
            severity=result.severity.value,
            correction=result.correction,
            explanation_short=result.explanation[:500] if result.explanation else "",
        )
    
    async def send(
        self,
        channel: NotificationChannel,
        payload: NotificationPayload,
        recipient: str,
        **kwargs,
    ) -> NotificationResult:
        """
        Send notification via specified channel.
        
        Args:
            channel: Notification channel to use
            payload: Notification content
            recipient: Channel-specific recipient (phone, email, URL, etc.)
            **kwargs: Additional channel-specific options
        """
        provider = self.providers.get(channel)
        if not provider:
            return NotificationResult(
                channel=channel,
                success=False,
                message=f"Unknown channel: {channel}",
                recipient=recipient,
            )
        
        return await provider.send(payload, recipient, **kwargs)
    
    async def broadcast(
        self,
        payload: NotificationPayload,
        recipients: dict[NotificationChannel, list[str]],
    ) -> list[NotificationResult]:
        """
        Broadcast notification to multiple channels/recipients.
        
        Args:
            payload: Notification content
            recipients: Dict mapping channels to list of recipients
            
        Returns:
            List of NotificationResult for each send attempt
        """
        results = []
        
        for channel, channel_recipients in recipients.items():
            for recipient in channel_recipients:
                result = await self.send(channel, payload, recipient)
                results.append(result)
        
        return results
    
    def get_configured_channels(self) -> list[NotificationChannel]:
        """Get list of channels that are properly configured."""
        return [
            channel for channel, provider in self.providers.items()
            if provider.is_configured
        ]


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get singleton notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
