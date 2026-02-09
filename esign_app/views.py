from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie, csrf_exempt
from django.contrib.auth import authenticate, login as auth_login
from django.middleware.csrf import get_token
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from uuid import uuid4
from .models import Document, Signature, SignedDocument, SignatureRequest, DocumentInvitation
from .docx_utils import DOCXProcessor, SignaturePlacementHelper
from .llm_service import get_llm_service
from .notification_service import NotificationService
import os
import json
import base64
from PIL import Image
import io

@csrf_protect
def custom_login(request):
    """Custom login view with proper CSRF handling"""
    from django.contrib.auth.forms import AuthenticationForm
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            # Redirect to the page they were trying to access, or to home
            next_page = request.GET.get('next', '/')
            return redirect(next_page)
        else:
            # Invalid credentials
            from django.contrib import messages
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    # For GET requests or failed login attempts, show the login form
    context = {
        'form': form,
        'csrf_token': get_token(request)
    }
    return render(request, 'login.html', context)


@ensure_csrf_cookie
def get_csrf(request):
    """Return a JSON response with a fresh CSRF token and ensure cookie set."""
    return JsonResponse({'csrf': get_token(request)})

@login_required
def index(request):
    """Main dashboard view - requires login"""
    # Filter documents and signatures for the current user
    documents = Document.objects.filter(user=request.user)
    signatures = Signature.objects.filter(user=request.user)
    signed_documents = SignedDocument.objects.filter(document__user=request.user)
    
    context = {
        'documents': documents,
        'signatures': signatures,
        'signed_documents': signed_documents,
    }
    return render(request, 'index.html', context)

def create_signature(request):
    """Handle signature creation (drawn or uploaded)"""
    if request.method == 'POST':
        signature_type = request.POST.get('signature_type')
        
        if signature_type == 'drawn':
            # Handle drawn signature (base64 image data)
            signature_data = request.POST.get('signature_data')
            
            if not signature_data:
                return JsonResponse({
                    'success': False,
                    'error': 'No signature data provided'
                }, status=400)
            
            # Decode base64 image
            try:
                # Remove data URL prefix if present
                if 'base64,' in signature_data:
                    signature_data = signature_data.split('base64,')[1]
                
                image_data = base64.b64decode(signature_data)
                image = Image.open(io.BytesIO(image_data))
                
                # Save signature
                signature = Signature(signature_type='drawn')
                            
                # Create file name
                filename = f'signature_{signature.id}.png'
                signature.signature_image.save(
                    filename,
                    ContentFile(image_data),
                    save=True
                )
                            
                # Notify super admins about signature creation
                NotificationService.notify_signature_created(request.user)
                            
                return JsonResponse({
                    'success': True,
                    'signature_id': str(signature.id),
                    'signature_url': signature.signature_image.url
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error processing signature: {str(e)}'
                }, status=400)
        
        elif signature_type == 'uploaded':
            # Handle uploaded signature image
            if 'signature_file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No signature file provided'
                }, status=400)
            
            signature_file = request.FILES['signature_file']
            
            # Validate image file
            if not signature_file.content_type.startswith('image/'):
                return JsonResponse({
                    'success': False,
                    'error': 'Only image files are allowed'
                }, status=400)
            
            # Create signature
            signature = Signature.objects.create(
                signature_type='uploaded',
                signature_image=signature_file
            )
            
            # Notify super admins about signature creation
            NotificationService.notify_signature_created(request.user)
            
            return JsonResponse({
                'success': True,
                'signature_id': str(signature.id),
                'signature_url': signature.signature_image.url
            })
    
    context = {
        'csrf_token': get_token(request)
    }
    return render(request, 'create_signature.html', context)


@ensure_csrf_cookie
def upload_document(request):
    """Handle document upload"""
    if request.method == 'POST':
        if 'document' in request.FILES:
            uploaded_file = request.FILES['document']
            title = request.POST.get('title', uploaded_file.name)
            
            # Validate file type
            filename = uploaded_file.name.lower()
            if not (filename.endswith('.docx') or filename.endswith('.pdf')):
                return JsonResponse({
                    'success': False,
                    'error': 'Only DOCX and PDF files are allowed'
                }, status=400)
            
            # Create document
            document = Document.objects.create(
                title=title,
                original_file=uploaded_file,
                user=request.user
            )
            
            # Notify super admins about document upload
            NotificationService.notify_document_uploaded(request.user, document)
            
            return JsonResponse({
                'success': True,
                'title': document.title,
                'document_id': str(document.id),
                'redirect_url': reverse('sign_document', kwargs={'document_id': document.id})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No file provided'
            }, status=400)
    
    context = {
        'csrf_token': get_token(request)
    }
    return render(request, 'upload_document.html', context)


@ensure_csrf_cookie
@login_required
def sign_document(request, document_id):
    """View for signing a document"""
    document = get_object_or_404(Document, id=document_id)
    signatures = Signature.objects.all()
    
    file_path = document.original_file.path
    file_extension = file_path.lower().split('.')[-1]
    
    if file_extension == 'docx':
        from .docx_utils import DOCXProcessor
        doc_info = DOCXProcessor.get_docx_info(file_path)
        # Extract text from DOCX for preview
        sections_text = DOCXProcessor.extract_text_from_docx(file_path)
    elif file_extension == 'pdf':
        from .pdf_utils import PDFProcessor
        doc_info = PDFProcessor.get_pdf_info(file_path)
        # Extract text from PDF for preview
        sections_text = PDFProcessor.extract_text_from_pdf(file_path)
    else:
        # Default to basic info
        doc_info = {'extension': file_extension}
        sections_text = {}
    
    suggested_positions = []
        
    context = {
        'document': document,
        'signatures': signatures,
        'doc_info': doc_info,
        'file_extension': file_extension,
        'sections_text': sections_text,  # Pass extracted text for preview
        'suggested_positions': suggested_positions,
        'csrf_token': get_token(request)  # Add CSRF token to context
        # signature_request removed - no suggested positions used
    }
    
    return render(request, 'sign_document.html', context)


@login_required
@csrf_protect
def apply_signature(request):
    print(f"=== CSRF DEBUG INFO ===")
    print(f"Request method: {request.method}")
    print(f"CSRF token from header: {request.META.get('HTTP_X_CSRFTOKEN')}")
    print(f"CSRF cookie: {request.COOKIES.get('csrftoken')}")
    print(f"Session ID: {request.session.session_key}")
    print(f"User authenticated: {request.user.is_authenticated}")
    print(f"=======================")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            document_id = data.get('document_id')
            signature_id = data.get('signature_id')
            x = float(data.get('x', 0))
            y = float(data.get('y', 0))
            page_number = int(data.get('page', 1))
            
            # Get preview dimensions for coordinate mapping
            preview_width = data.get('preview_width', 800)
            preview_height = data.get('preview_height', 600)
            
            # Handle multiple signatures if provided
            signatures_data = data.get('signatures', [])
            if not signatures_data:
                # If no signatures array, create one with the main signature
                signatures_data = [{
                    'signature_id': signature_id,
                    'x': x,
                    'y': y,
                    'page': page_number
                }]
            
            document = get_object_or_404(Document, id=document_id)
            
            # Check if signature file exists
            main_signature_obj = get_object_or_404(Signature, id=signature_id)
            if not os.path.exists(main_signature_obj.signature_image.path):
                return JsonResponse({
                    'success': False,
                    'error': f'Signature file not found: {main_signature_obj.signature_image.name}'
                }, status=400)
            
            # Get all signatures involved
            all_signatures = []
            for sig_data in signatures_data:
                sig = get_object_or_404(Signature, id=sig_data['signature_id'])
                all_signatures.append({
                    'signature': sig,
                    'x': float(sig_data['x']),
                    'y': float(sig_data['y']),
                    'page': int(sig_data['page']),
                    'align': sig_data.get('align')  # 'left' or 'right' optional override
                })
            
            # Get the first signature for main processing (used for the main record)
            if all_signatures:
                first_signature_data = all_signatures[0]
                main_signature = first_signature_data['signature']
                x = first_signature_data['x']
                y = first_signature_data['y']
                page_number = first_signature_data['page']
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No signatures provided'
                }, status=400)
            
            # Determine file extension to decide processing method
            file_extension = document.original_file.path.lower().split('.')[-1]

            # If any signature requested page <= 0, interpret as 'end of document'
            if file_extension == 'pdf':
                from .pdf_utils import PDFProcessor
                try:
                    pdf_info = PDFProcessor.get_pdf_info(document.original_file.path)
                    doc_num_pages = pdf_info.get('num_pages', 1)
                except Exception:
                    doc_num_pages = 1
            elif file_extension == 'docx':
                from .docx_utils import DOCXProcessor
                try:
                    doc_info = DOCXProcessor.get_docx_info(document.original_file.path)
                    doc_num_pages = doc_info.get('num_pages', 1)
                except Exception:
                    doc_num_pages = 1
            else:
                doc_num_pages = 1

            # Normalize signatures page numbers: non-positive -> last page
            for sig in all_signatures:
                if 'page' in sig and int(sig['page']) <= 0:
                    sig['page'] = doc_num_pages
            
            # Create output filename with correct extension
            # For DOCX, we can create both PDF and DOCX versions
            if file_extension == 'docx':
                # Create DOCX (preserve original format) and optionally a PDF conversion
                docx_output_filename = f'signed_{document.id}_{main_signature_obj.id}_docx.docx'
                pdf_output_filename = f'signed_{document.id}_{main_signature_obj.id}.pdf'

                # Paths
                docx_output_path = os.path.join(settings.MEDIA_ROOT, 'signed_documents', docx_output_filename)
                pdf_output_path = os.path.join(settings.MEDIA_ROOT, 'signed_documents', pdf_output_filename)

                # Use the DOCX path as the primary output path for the database record
                output_path = docx_output_path
                output_filename = docx_output_filename

                # Store the original preview coordinates for DOCX format preservation
                stored_x, stored_y = x, y
            else:
                output_filename = f'signed_{document.id}_{main_signature_obj.id}.{file_extension}'
                output_path = os.path.join(settings.MEDIA_ROOT, 'signed_documents', output_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Initialize coordinate storage variables for non-DOCX files
            if file_extension != 'docx':
                stored_x = x  # Default to the first signature's x coordinate
                stored_y = y  # Default to the first signature's y coordinate
            
            # Apply signature based on file type
            if file_extension == 'docx':
                # Preserve original DOCX: create a signed DOCX rather than converting to PDF
                print("=== DOCX SIGNING (PRESERVE DOCX) ===")
                # Build DOCX signatures payload
                docx_signatures_data = []
                for sig in all_signatures:
                    sig_obj = sig['signature']
                    docx_signatures_data.append({
                        'signature_image_path': sig_obj.signature_image.path,
                        'page': sig.get('page', 1),
                        'x': sig.get('x', 0),
                        'y': sig.get('y', 0),
                        'align': sig.get('align')
                    })

                # Create signed DOCX
                print(f"Applying signatures to DOCX: {docx_output_path}")
                success = DOCXProcessor.add_multiple_signatures_to_docx(
                    docx_path=document.original_file.path,
                    signatures_data=docx_signatures_data,
                    output_path=docx_output_path
                )

                if success and os.path.exists(docx_output_path):
                    output_path = docx_output_path
                    output_filename = os.path.basename(docx_output_path)
                    print(f"Signed DOCX created: {output_path}")
                    if all_signatures:
                        first_sig_preview = all_signatures[0]
                        stored_x, stored_y = first_sig_preview['x'], first_sig_preview['y']
                        page_number = first_sig_preview['page']
                else:
                    print("Failed to create signed DOCX from original")
            elif file_extension == 'pdf':
                from .pdf_utils import PDFProcessor
                
                # Get PDF page dimensions
                doc_info = PDFProcessor.get_pdf_info(document.original_file.path)
                doc_num_pages = doc_info.get('num_pages', 1)
                page_width = doc_info.get('page_width', 612)
                page_height = doc_info.get('page_height', 792)
                
                print(f"=== PDF SIGNATURE POSITIONING DEBUG ===")
                print(f"Preview dimensions: {preview_width} x {preview_height}")
                print(f"PDF page dimensions: {page_width} x {page_height}")
                print(f"Number of signatures to place: {len(all_signatures)}")
                
                # Prepare signatures data for batch processing
                pdf_signatures_data = []
                for i, sig_data in enumerate(all_signatures):
                    signature = sig_data['signature']
                    x = sig_data['x']
                    y = sig_data['y']
                    page_number = sig_data['page']
                    
                    # Check if this is explicitly marked as an end position
                    is_end_position = sig_data.get('is_end_position', False)
                    
                    # Allow explicit alignment override from the client
                    explicit_align = sig_data.get('align')
                    
                    print(f"Processing signature {i+1}/{len(all_signatures)}: {signature.id}")
                    print(f"Input coordinates (preview): x={x}, y={y}, page={page_number}")
                    print(f"Is end position: {is_end_position}")
                    
                    if preview_width <= 0 or preview_height <= 0:
                        print(f"ERROR: Invalid preview dimensions: {preview_width} x {preview_height}")
                        # Fallback to reasonable defaults
                        preview_width = 800
                        preview_height = 1000
                        
                    scale_x = page_width / preview_width
                    scale_y = page_height / preview_height
                    print(f"Scaling factors: scale_x={scale_x}, scale_y={scale_y}")
                    
                    # Determine left/right alignment: explicit align overrides x
                    if explicit_align:
                        is_right_side = str(explicit_align).lower() == 'right'
                    else:
                        is_right_side = x > preview_width / 2
                    
                    if is_end_position:
                        # For explicitly marked end positions, place at guaranteed bottom of page
                        # Use fixed bottom margin placement
                        right_margin_offset = 200
                        left_margin_offset = 50
                        bottom_margin_offset = 30  # Very close to bottom (30 units)
                        
                        pdf_x = page_width - right_margin_offset if is_right_side else left_margin_offset
                        pdf_y = bottom_margin_offset  # Place very close to bottom of page
                        print(f"END POSITION: Guaranteed bottom placement on page {page_number}")
                        print(f"Final PDF coordinates: x={pdf_x}, y={pdf_y} (from bottom)")
                        
                        # Skip all the regular positioning adjustments for end positions
                        # This ensures the signature goes exactly where we want it
                    else:
                        # Regular positioning - enhanced coordinate mapping
                        
                        # Calculate scaling ratios
                        scale_x = page_width / preview_width
                        scale_y = page_height / preview_height
                        
                        print(f"Scale factors: X={scale_x:.4f}, Y={scale_y:.4f}")
                        
                        # Map preview coordinates to PDF coordinates
                        # Preview: (0,0) = top-left, PDF: (0,0) = bottom-left
                        raw_pdf_x = x * scale_x
                        raw_pdf_y = y * scale_y
                        
                        # Convert to PDF coordinate system (flip Y axis)
                        pdf_x = raw_pdf_x
                        pdf_y = page_height - raw_pdf_y
                        
                        print(f"Raw mapping: preview({x},{y}) -> PDF({raw_pdf_x:.2f},{raw_pdf_y:.2f})")
                        print(f"After Y-flip: PDF({pdf_x:.2f},{pdf_y:.2f})")
                        
                        # Apply fine-tuning adjustments based on empirical testing
                        # These corrections account for browser rendering quirks
                        if scale_x > 1.5:
                            # Large scaling - reduce over-correction
                            pdf_x = pdf_x + 5
                            pdf_y = pdf_y - 5
                        elif scale_x < 0.8:
                            # Small scaling - increase correction
                            pdf_x = pdf_x + 25
                            pdf_y = pdf_y - 15
                        else:
                            # Medium scaling - standard correction
                            pdf_x = pdf_x + 15
                            pdf_y = pdf_y - 10
                        
                        print(f"After adjustments: PDF({pdf_x:.2f},{pdf_y:.2f})")
                        
                        # Apply safety margins
                        margin = 25
                        signature_width = 150
                        signature_height = 50
                        
                        pdf_x = max(margin, min(pdf_x, page_width - signature_width - margin))
                        pdf_y = max(margin, min(pdf_y, page_height - signature_height - margin))
                        
                        print(f"Final coordinates after bounds check: PDF({pdf_x:.2f},{pdf_y:.2f})")
                        
                    # Add signature data to the list for batch processing
                    pdf_signatures_data.append({
                        'signature_image_path': signature.signature_image.path,
                        'page': page_number,
                        'x': pdf_x,
                        'y': pdf_y
                    })
                    
                    print(f"Target page: {page_number}")
                    print(f"=== END SIGNATURE {i+1} POSITIONING ===")
                
                # Apply all signatures in one operation using the batch method
                success = PDFProcessor.add_multiple_signatures_to_pdf(
                    input_pdf_path=document.original_file.path,
                    output_pdf_path=output_path,
                    signatures_data=pdf_signatures_data,
                    label_text="Signature",
                    signature_width=150,
                    signature_height=50
                )
                
                # Store coordinates for the first signature
                if pdf_signatures_data:
                    first_sig = pdf_signatures_data[0]
                    stored_x, stored_y = first_sig['x'], first_sig['y']
                    page_number = first_sig['page']
                
                print(f"=== END PDF POSITIONING ===")
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unsupported file type: {file_extension}'
                }, status=500)
            
            if success:
                # Ensure page_number is available for SignedDocument creation
                final_page_number = page_number if 'page_number' in locals() else 1
                signed_doc = SignedDocument.objects.create(
                    document=document,
                    signature=main_signature_obj,
                    signed_file=f'signed_documents/{output_filename}',
                    signature_position_x=stored_x,
                    signature_position_y=stored_y,
                    signature_page=final_page_number
                )
                
                # Update document status
                document.status = 'signed'
                document.save()

                # Notify super admins using the notification service
                NotificationService.notify_document_signed(request.user, document)

                # Redirect to index for all users
                redirect_url = reverse('index')

                return JsonResponse({
                    'success': True,
                    'message': f'{len(all_signatures)} signature(s) applied successfully!',
                    'signed_document_id': str(signed_doc.id),
                    'download_options': {
                        'pdf': f'/download/{signed_doc.id}/pdf/',
                        'docx': f'/download/{signed_doc.id}/docx/'
                    },
                    'redirect': redirect_url
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to apply signature(s)'
                }, status=500)
                
        except Exception as e:
            print(f"Exception in apply_signature: {str(e)}")
            import traceback
            traceback.print_exc()  
            return JsonResponse({
                'success': False,
                'error': f"Internal error: {str(e)}"
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


def serve_document_preview(request, document_id):
    """Serve document for preview in iframe - RESTORED for actual document preview"""
    document = get_object_or_404(Document, id=document_id)
    file_path = document.original_file.path
    file_extension = file_path.lower().split('.')[-1]
    
    if os.path.exists(file_path):
        # Determine content type based on file extension
        if file_extension == 'pdf':
            content_type = 'application/pdf'
        elif file_extension == 'docx':
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            content_type = 'application/octet-stream'
        
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type
        )
        
        # Set headers for inline display and allow embedding
        response["Content-Disposition"] = 'inline; filename="{}"'.format(os.path.basename(file_path))
        response["X-Frame-Options"] = "SAMEORIGIN"  # Allow embedding in same-origin iframes
        response["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response
    
    return HttpResponse('File not found', status=404)
# Alias for backward compatibility
get_document_preview = serve_document_preview


def download_signed_document(request, signed_doc_id, format=None):
    """Serve the stored signed file (preserve original format)."""
    try:
        signed_doc = SignedDocument.objects.get(id=signed_doc_id)
    except SignedDocument.DoesNotExist:
        return HttpResponse('Document not found', status=404)

    file_path = signed_doc.signed_file.path
    print(f"=== DOWNLOAD REQUEST DEBUG ===")
    print(f"  Signed document ID: {signed_doc_id}")
    print(f"  Stored file path: {file_path}")
    if not os.path.exists(file_path):
        print(f"Signed file not found: {file_path}")
        return HttpResponse('File not found', status=404)

    stored_ext = file_path.lower().split('.')[-1]
    base_title = signed_doc.document.title.replace(' ', '_')
    filename = f'signed_{base_title}.{stored_ext}'

    if stored_ext == 'pdf':
        content_type = 'application/pdf'
    elif stored_ext == 'docx':
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        content_type = 'application/octet-stream'

    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type=content_type
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    try:
        size = os.path.getsize(file_path)
        response['Content-Length'] = str(size)
        print(f"Serving stored signed file size: {size} bytes")
    except Exception:
        pass
    response['Content-Transfer-Encoding'] = 'binary'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def delete_document(request, document_id):
    """Delete a document and redirect to index."""
    document = get_object_or_404(Document, id=document_id)
    document.delete()
    return redirect('index')


def delete_signature(request, signature_id):
    """Delete a signature and redirect to index."""
    signature = get_object_or_404(Signature, id=signature_id)
    signature.delete()
    return redirect('index')


def sign_invited_document(request, document_id, invitation_token):
    """Handle document signing through email invitation"""
    document = get_object_or_404(Document, id=document_id)
    invitation = get_object_or_404(DocumentInvitation, 
                                 document=document, 
                                 invitation_token=invitation_token)
    
    # Check if invitation is expired
    if invitation.is_expired():
        messages.error(request, 'This invitation has expired.')
        return redirect('login')
    
    # Check if already accepted
    if invitation.is_accepted:
        messages.info(request, 'This invitation has already been used.')
        return redirect('login')
    
    # Mark as accepted
    invitation.is_accepted = True
    invitation.accepted_at = timezone.now()
    invitation.save()
    
    # If user is not logged in, redirect to login with next parameter
    if not request.user.is_authenticated:
        login_url = reverse('login') + f'?next={request.path}'
        return redirect(login_url)
    
    # Continue with normal signing process
    return sign_document(request, document_id)


def send_document_invitation_view(request, document_id):
    """Admin view to send document invitation"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('admin:index')
    
    document = get_object_or_404(Document, id=document_id)
    
    if request.method == 'POST':
        recipient_email = request.POST.get('recipient_email')
        recipient_name = request.POST.get('recipient_name', '')
        
        if not recipient_email:
            messages.error(request, 'Recipient email is required.')
            return render(request, 'admin/send_invitation.html', {'document': document})
        
        # Send invitation
        invitation = NotificationService.send_document_invitation(
            document=document,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            sent_by_user=request.user
        )
        
        if invitation:
            messages.success(request, f'Invitation sent successfully to {recipient_email}')
        else:
            messages.error(request, 'Failed to send invitation. Please check email configuration.')
        
        return redirect('admin:esign_app_document_changelist')
    
    return render(request, 'admin/send_invitation.html', {'document': document})