from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import uuid
from datetime import timedelta
from django.utils import timezone

def validate_document_file(value):
    import os
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.docx', '.pdf']
    if ext not in valid_extensions:
        raise ValidationError(f'Unsupported file extension: {ext}. Only DOCX and PDF files are allowed.')

class Document(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    original_file = models.FileField(upload_to='documents/', validators=[validate_document_file])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('signed', 'Signed'),
        ],
        default='pending'
    )
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title


class Signature(models.Model):
    """Model for signatures"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    signature_type = models.CharField(
        max_length=20,
        choices=[
            ('drawn', 'Drawn'),
            ('uploaded', 'Uploaded'),
        ]
    )
    signature_image = models.ImageField(upload_to='signatures/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Signature {self.id} - {self.signature_type}"


class SignedDocument(models.Model):
    """Model for signed documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signed_documents')
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE, related_name='signed_documents')
    signed_file = models.FileField(upload_to='signed_documents/')
    signature_position_x = models.FloatField()
    signature_position_y = models.FloatField()
    signature_page = models.IntegerField(default=1)
    signed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-signed_at']
    
    def __str__(self):
        return f"Signed: {self.document.title}"


class SignatureRequest(models.Model):
    """Model for tracking signature placement requests analyzed by LLM"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signature_requests')
    extracted_text = models.TextField()
    suggested_position = models.JSONField(null=True, blank=True)
    llm_analysis = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Signature Request for {self.document.title}"


class DocumentInvitation(models.Model):
    """Model for tracking document email invitations sent to users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='invitations')
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=255, blank=True)
    invitation_token = models.UUIDField(default=uuid.uuid4, editable=False)
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Invitation for {self.document.title} to {self.recipient_email}"
    
    def save(self, *args, **kwargs):
        # Set expiration to 7 days from now if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def get_sign_url(self):
        from django.urls import reverse
        return reverse('sign_invited_document', kwargs={
            'document_id': self.document.id,
            'invitation_token': self.invitation_token
        })


