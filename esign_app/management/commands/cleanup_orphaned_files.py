import os
from django.core.management.base import BaseCommand
from esign_app.models import SignedDocument
from django.conf import settings

class Command(BaseCommand):
    help = 'Clean up orphaned signed document files'

    def handle(self, *args, **options):
        # Get all signed document files in the database
        signed_files = set()
        for doc in SignedDocument.objects.all():
            signed_files.add(doc.signed_file.name)
        
        # Get all files in the signed_documents directory
        signed_documents_dir = os.path.join(settings.MEDIA_ROOT, 'signed_documents')
        if os.path.exists(signed_documents_dir):
            all_files = set(os.listdir(signed_documents_dir))
            
            # Find orphaned files
            orphaned_files = all_files - {os.path.basename(f) for f in signed_files}
            
            if orphaned_files:
                self.stdout.write(
                    self.style.WARNING(f'Found {len(orphaned_files)} orphaned files:')
                )
                for file in orphaned_files:
                    self.stdout.write(f'  {file}')
                
                # Ask for confirmation
                confirm = input('Delete these files? (y/N): ')
                if confirm.lower() == 'y':
                    for file in orphaned_files:
                        file_path = os.path.join(signed_documents_dir, file)
                        os.remove(file_path)
                        self.stdout.write(
                            self.style.SUCCESS(f'Deleted {file}')
                        )
                else:
                    self.stdout.write('No files deleted.')
            else:
                self.stdout.write(
                    self.style.SUCCESS('No orphaned files found.')
                )
        else:
            self.stdout.write(
                self.style.WARNING('Signed documents directory does not exist.')
            )