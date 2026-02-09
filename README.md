# E-Signature Document Management System

A comprehensive Django-based web application for managing digital document signing with multi-page support, email invitations, and admin oversight.

## 🚀 Features

### Core Functionality
- **Document Upload**: Support for DOCX and PDF file formats
- **Digital Signatures**: Draw or upload signature images
- **Multi-page Support**: Place signatures on any page of multi-page documents
- **Email Invitations**: Send secure document signing invitations via email
- **Admin Dashboard**: Comprehensive admin interface for document management
- **Real-time Preview**: Document preview before signing
- **Format Preservation**: Maintains original DOCX formatting during signing

### Technical Capabilities
- **Per-page Signature Placement**: Customize signature position on any document page
- **Secure Token System**: Time-limited invitation tokens with single-use validation
- **Responsive Design**: Works across desktop and mobile devices
- **File Management**: Automatic cleanup of orphaned files
- **Notification System**: Email alerts for admin activities

## 🛠️ Tech Stack

- **Backend**: Django 4.2.7
- **Database**: SQLite3 (development) / PostgreSQL (production ready)
- **Frontend**: HTML5, CSS3, JavaScript
- **Document Processing**: 
  - `python-docx` for DOCX manipulation
  - `PyPDF2` and `PyMuPDF` for PDF processing
  - `reportlab` for PDF generation
- **Image Processing**: Pillow (PIL)
- **Email**: SMTP integration with Gmail support

## 📁 Project Structure

```
esignature_project/
├── esign_app/                    # Main application
│   ├── management/
│   │   └── commands/
│   │       └── cleanup_orphaned_files.py
│   ├── migrations/               # Database migrations
│   ├── static/
│   │   └── admin/
│   │       └── css/
│   │           └── custom_admin.css
│   ├── templates/
│   │   ├── admin/
│   │   │   └── send_invitation.html
│   │   ├── emails/
│   │   │   └── document_invitation.html
│   │   ├── base.html
│   │   ├── create_signature.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── sign_document.html
│   │   └── upload_document.html
│   ├── admin.py                  # Django admin configuration
│   ├── apps.py
│   ├── docx_utils.py            # DOCX processing utilities
│   ├── llm_service.py           # Language model integration (disabled)
│   ├── models.py                # Database models
│   ├── notification_service.py  # Email notification system
│   ├── pdf_utils.py             # PDF processing utilities
│   ├── urls.py                  # URL routing
│   └── views.py                 # View functions
├── esignature_project/          # Django project settings
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── media/                       # User uploaded files
│   ├── documents/
│   ├── signatures/
│   └── signed_documents/
├── staticfiles/                 # Collected static files
├── db.sqlite3                  # Database file
├── manage.py                   # Django management script
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd c:\Users\Acer\Downloads\esignature_project
   ```

2. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a superuser (admin account):**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - Main site: `http://127.0.0.1:8000/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

## 🔧 Configuration

### Email Settings
Configure email in `esignature_project/settings.py`:

```python
# Gmail SMTP configuration (development)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'
```

### Security Settings
For production deployment:
```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECRET_KEY = 'your-production-secret-key'
```

## 📖 Usage Guide

### For Regular Users

1. **Login**: Access the system with your credentials
2. **Upload Document**: Navigate to upload section and select DOCX/PDF file
3. **Create Signature**: Either draw a signature or upload an image
4. **Sign Document**: Place your signature on the desired page/location
5. **Download**: Access your signed documents from the dashboard

### For Administrators

1. **Admin Access**: Log into `/admin/` with superuser credentials
2. **Document Management**: 
   - View all uploaded documents
   - Send email invitations to users
   - Monitor document status
3. **User Management**: Manage user accounts and permissions
4. **System Maintenance**: 
   - Clean up orphaned files using management commands
   - Monitor system activity through notifications

### Sending Invitations

Administrators can send document signing invitations directly from the admin panel:
1. Navigate to Documents section in admin
2. Click "📧 Send Invitation" button next to any document
3. Enter recipient email and optional name
4. System sends professional email with secure signing link

## 🛠️ Management Commands

### Cleanup Orphaned Files
Remove unused signature and document files:
```bash
python manage.py cleanup_orphaned_files
```

## 📊 Database Models

### Key Models
- **Document**: Uploaded documents with metadata
- **Signature**: User signature images (drawn or uploaded)
- **SignedDocument**: Completed signed documents with positioning data
- **DocumentInvitation**: Email invitations with token tracking
- **SignatureRequest**: LLM-based signature placement suggestions (disabled)

## 🔒 Security Features

- **Token-based Invitations**: Secure, time-limited signing links
- **Single-use Tokens**: Each invitation can only be used once
- **Session Management**: Secure user authentication
- **File Validation**: Strict file type checking for uploads
- **Admin-only Access**: Protected administrative functions

## 🎨 Customization

### Admin Styling
Customize admin interface by modifying:
- `esign_app/static/admin/css/custom_admin.css`
- Template files in `esign_app/templates/admin/`

### Email Templates
Modify email appearance by editing:
- `esign_app/templates/emails/document_invitation.html`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

**Email Not Sending:**
- Verify SMTP settings in `settings.py`
- Check Gmail app password configuration
- Ensure `EMAIL_HOST_PASSWORD` is correctly set

**Document Processing Errors:**
- Verify file format is DOCX or PDF
- Check file size limitations (configured in settings)
- Ensure required Python packages are installed

**Static Files Not Loading:**
```bash
python manage.py collectstatic
```

## 📞 Support

For issues or questions:
- Check the Django logs for error messages
- Review the admin notification system
- Verify all dependencies are properly installed

## 📄 License

This project is proprietary software developed for document management purposes.

## 🔄 Version History

- **v1.0**: Initial release with core document signing functionality
- **v1.1**: Added email invitation system and admin enhancements
- **v1.2**: Implemented multi-page signature placement and format preservation

---

*Built with Django 4.2.7 | Python 3.11*
