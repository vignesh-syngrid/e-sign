from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import DocumentInvitation

import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications to super admins about user activities"""
    
    @staticmethod
    def get_super_admin_emails():
        """Get email addresses of all super admin users and additional notification emails"""
        # Get super admin emails
        super_admins = User.objects.filter(is_superuser=True, email__isnull=False).exclude(email='')
        emails = [admin.email for admin in super_admins]
        
        # Add additional notification emails if configured
        additional_emails = getattr(settings, 'SUPER_ADMIN_ADDITIONAL_EMAILS', [])
        emails.extend(additional_emails)
        
        # Remove duplicates
        return list(set(emails))
    
    @staticmethod
    def send_notification_to_super_admins(subject, message, activity_type=None, user=None, document=None):
        """
        Send email notification to all super admins
        
        Args:
            subject (str): Email subject
            message (str): Email message body
            activity_type (str): Type of activity for logging
            user (User): User who performed the activity
            document (Document): Related document (optional)
        """
        if not getattr(settings, 'SUPER_ADMIN_NOTIFICATIONS_ENABLED', True):
            logger.info("Super admin notifications are disabled")
            return False
        
        super_admin_emails = NotificationService.get_super_admin_emails()
        
        if not super_admin_emails:
            logger.warning("No super admin emails found for notifications")
            return False
        
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        try:
            # Send email to all super admins
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=super_admin_emails,
                fail_silently=False
            )
            
            # Notification sent successfully
            
            logger.info(f"Notification sent to {len(super_admin_emails)} super admin(s): {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    @staticmethod
    def notify_user_login(user):
        """Notify super admins when a user logs in"""
        if user.is_superuser:
            # Don't notify for super admin logins to avoid spam
            return
            
        subject = f"User Login: {user.username}"
        message = f"""
User Login Notification
======================

User: {user.username}
Email: {user.email or 'Not provided'}
Login Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

This is an automated notification that a user has logged into the eSignature system.
        """.strip()
        
        NotificationService.send_notification_to_super_admins(
            subject=subject,
            message=message,
            activity_type='user_login',
            user=user
        )
    
    @staticmethod
    def notify_document_signed(user, document):
        """Notify super admins when a document is signed"""
        subject = f"Document Signed: {document.title}"
        message = f"""
Document Signed Notification
===========================

User: {user.username}
Document: {document.title}
Signed Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

The document has been successfully signed by the user.
        """.strip()
        
        NotificationService.send_notification_to_super_admins(
            subject=subject,
            message=message,
            activity_type='document_signed',
            user=user,
            document=document
        )
    
    @staticmethod
    def notify_document_uploaded(user, document):
        """Notify super admins when a document is uploaded"""
        subject = f"Document Uploaded: {document.title}"
        message = f"""
Document Upload Notification
===========================

User: {user.username}
Document: {document.title}
Upload Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

A new document has been uploaded to the system.
        """.strip()
        
        NotificationService.send_notification_to_super_admins(
            subject=subject,
            message=message,
            activity_type='document_uploaded',
            user=user,
            document=document
        )
    
    @staticmethod
    def notify_signature_created(user):
        """Notify super admins when a signature is created"""
        subject = f"Signature Created: {user.username}"
        message = f"""
Signature Creation Notification
==============================

User: {user.username}
Creation Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

A new signature has been created by the user.
        """.strip()
        
        NotificationService.send_notification_to_super_admins(
            subject=subject,
            message=message,
            activity_type='signature_created',
            user=user
        )
    
    @staticmethod
    def notify_document_deleted(user, document_title):
        """Notify super admins when a document is deleted"""
        subject = f"Document Deleted: {document_title}"
        message = f"""
Document Deletion Notification
=============================

User: {user.username}
Document: {document_title}
Deletion Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

A document has been deleted from the system.
        """.strip()
        
        NotificationService.send_notification_to_super_admins(
            subject=subject,
            message=message,
            activity_type='document_deleted',
            user=user
        )
    
    @staticmethod
    def notify_signature_deleted(user, signature_id):
        """Notify super admins when a signature is deleted"""
        subject = f"Signature Deleted: {signature_id}"
        message = f"""
Signature Deletion Notification
==============================

User: {user.username}
Signature ID: {signature_id}
Deletion Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

A signature has been deleted from the system.
        """.strip()
        
        NotificationService.send_notification_to_super_admins(
            subject=subject,
            message=message,
            activity_type='signature_deleted',
            user=user
        )

    @staticmethod
    def send_document_invitation(document, recipient_email, recipient_name, sent_by_user):
        """
        Send email invitation to user to sign a document
        
        Args:
            document (Document): The document to be signed
            recipient_email (str): Email address of recipient
            recipient_name (str): Name of recipient
            sent_by_user (User): Admin user sending the invitation
        
        Returns:
            DocumentInvitation object if successful, None if failed
        """
        try:
            # Create invitation record
            invitation = DocumentInvitation.objects.create(
                document=document,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                sent_by=sent_by_user
            )
            
            # Generate sign URL
            sign_url = invitation.get_sign_url()
            
            # Create full URL (assuming site domain is configured)
            from django.contrib.sites.shortcuts import get_current_site
            
            try:
                # Try to get current site
                site = get_current_site(None)
                full_sign_url = f"{settings.SITE_URL}{sign_url}" if hasattr(settings, 'SITE_URL') else f"http://{site.domain}{sign_url}"
            except:
                # Fallback to localhost
                full_sign_url = f"http://localhost:8000{sign_url}"
            
            # Prepare email content
            context = {
                'recipient_name': recipient_name or recipient_email,
                'document_title': document.title,
                'sender_name': sent_by_user.get_full_name() or sent_by_user.username,
                'sign_url': full_sign_url,
                'expiration_date': invitation.expires_at.strftime('%B %d, %Y'),
                'site_name': getattr(settings, 'SITE_NAME', 'E-Signature System')
            }
            
            # Render email templates
            html_message = render_to_string('emails/document_invitation.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email
            subject = f"Document Signing Invitation: {document.title}"
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Document invitation sent to {recipient_email} for document {document.title}")
            return invitation
            
        except Exception as e:
            logger.error(f"Failed to send document invitation: {str(e)}")
            return None

# Import timezone here to avoid circular imports
from django.utils import timezone
