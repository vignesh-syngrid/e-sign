from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Document, Signature, SignedDocument, SignatureRequest, DocumentInvitation
from .notification_service import NotificationService


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'uploaded_at', 'send_invitation_button']
    list_filter = ['status', 'uploaded_at']
    search_fields = ['title', 'user__username']
    readonly_fields = ['id', 'uploaded_at']
    actions = ['send_invitation_action']
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
    
    def get_urls(self):
        from django.urls import path
        from .views import send_document_invitation_view
        
        urls = super().get_urls()
        custom_urls = [
            path('<uuid:document_id>/send-invitation/',
                 self.admin_site.admin_view(send_document_invitation_view),
                 name='esign_app_document_send_invitation'),
        ]
        return custom_urls + urls
    
    def send_invitation_action(self, request, queryset):
        """Bulk action to send invitations"""
        if len(queryset) == 1:
            # Single document - redirect to send invitation page
            document = queryset.first()
            return HttpResponseRedirect(
                reverse('admin:esign_app_document_send_invitation', args=[document.id])
            )
        else:
            # Multiple documents - show error message
            self.message_user(
                request, 
                "Please select only one document to send invitation. You can only send invitations one document at a time.", 
                messages.ERROR
            )
            return HttpResponseRedirect(reverse('admin:esign_app_document_changelist'))
    send_invitation_action.short_description = "📧 Send invitation for selected document"
    
    def send_invitation_button(self, obj):
        """Display a button to send invitation for each document"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('admin:esign_app_document_send_invitation', args=[obj.id])
        return format_html(
            '<a class="button" href="{}">📧 Send Invitation</a>',
            url
        )
    send_invitation_button.short_description = "Send Invitation"
    send_invitation_button.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        # Automatically set the user to the current admin user if not set
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'signature_type', 'created_at']
    list_filter = ['signature_type', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['id', 'created_at']
    
    def save_model(self, request, obj, form, change):
        # Automatically set the user to the current admin user if not set
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(SignedDocument)
class SignedDocumentAdmin(admin.ModelAdmin):
    list_display = ['document', 'signature_page', 'signed_at', 'download_link']
    list_filter = ['signed_at']
    readonly_fields = ['id', 'signed_at', 'download_link']
    
    def download_link(self, obj):
        """Display download link for the signed document"""
        url = reverse('download_signed_document', kwargs={'signed_doc_id': obj.id})
        return format_html(
            '<a href="{}" class="button" target="_blank">📥 Download</a>',
            url
        )
    download_link.short_description = "Download"
    download_link.allow_tags = True


@admin.register(SignatureRequest)
class SignatureRequestAdmin(admin.ModelAdmin):
    list_display = ['document', 'created_at']
    readonly_fields = ['id', 'created_at', 'extracted_text', 'llm_analysis']


@admin.register(DocumentInvitation)
class DocumentInvitationAdmin(admin.ModelAdmin):
    list_display = ['document', 'recipient_email', 'recipient_name', 'sent_at', 'is_accepted', 'expires_at']
    list_filter = ['is_accepted', 'sent_at', 'expires_at']
    search_fields = ['document__title', 'recipient_email', 'recipient_name']
    readonly_fields = ['id', 'invitation_token', 'sent_at', 'accepted_at']
    
    def has_add_permission(self, request):
        return False  # Invitations should be created through the notification service
