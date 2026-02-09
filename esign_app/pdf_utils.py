import os
from typing import Dict, List, Tuple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from io import BytesIO
import PIL.Image


class PDFProcessor:
    @staticmethod
    def get_pdf_info(pdf_path: str) -> Dict:
        """Get basic information about a PDF file"""
        try:
            reader = PdfReader(pdf_path)
            doc = fitz.open(pdf_path)  # Using PyMuPDF for more detailed info
            
            return {
                'num_pages': len(reader.pages),
                'page_width': doc[0].rect.width if len(doc) > 0 else 612,  # Default to letter width
                'page_height': doc[0].rect.height if len(doc) > 0 else 792,  # Default to letter height
                'has_images': any('/XObject' in page['/Resources'] for page in reader.pages if '/Resources' in page),
                'extension': 'pdf'
            }
        except Exception as e:
            print(f"Error getting PDF info: {e}")
            return {'num_pages': 1, 'extension': 'pdf'}
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> Dict[int, str]:
        """
        Extract text content from PDF organized by pages
        """
        try:
            doc = fitz.open(pdf_path)  # Using PyMuPDF for better text extraction
            pages_dict = {}
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Only add pages with substantial content
                if text.strip():
                    # Clean up the text a bit
                    cleaned_text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
                    pages_dict[page_num + 1] = cleaned_text
            
            doc.close()
            return pages_dict
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return {1: "Error extracting PDF content"}
    
    @staticmethod
    def add_signature_to_pdf(
        input_pdf_path: str,
        output_pdf_path: str,
        signature_image_path: str,
        page_number: int,
        x: float,
        y: float,
        label_text: str = "Signature",
        signature_width: int = 150,
        signature_height: int = 50
    ) -> bool:
        """
        Add signature and its label to specific page of PDF
        (Updated method to include label text)
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path to save signed PDF
            signature_image_path: Path to signature image
            page_number: Page to add signature (1-indexed)
            x, y: Position coordinates (PDF coordinate system - bottom left origin)
            label_text: Text to display as label near the signature
            signature_width, signature_height: Signature dimensions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if signature file exists
            import os
            if not os.path.exists(signature_image_path):
                print(f"ERROR: Signature file not found at {signature_image_path}")
                return False
            
            # Read original PDF
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            
            # Get page dimensions
            target_page = reader.pages[page_number - 1]
            mediabox = target_page.mediabox
            page_width = float(mediabox.width)
            page_height = float(mediabox.height)
            
            # Create signature overlay with both signature and label
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            
            # Add signature image at the exact x,y coordinates
            # Note: In PDF coordinate system, (0,0) is bottom-left corner
            try:
                can.drawImage(
                    signature_image_path,
                    x, y,
                    width=signature_width,
                    height=signature_height,
                    mask='auto'  # Preserve transparency
                )
            except Exception as e:
                print(f"Error adding signature image: {e}")
            
            # Add label text near the signature at the exact position
            can.setFont("Helvetica", 10)  # Use standard font
            can.setFillColorRGB(0, 0, 0)  # Black color
            
            # Position label relative to signature at the exact coordinates
            label_x = x + (signature_width / 2) - 20  # Center the label below the signature
            label_y = y - 15  # Place it 15 units below the signature
            can.drawString(label_x, label_y, label_text)
            
            can.save()
            packet.seek(0)
            
            # Read overlay
            overlay_reader = PdfReader(packet)
            overlay_page = overlay_reader.pages[0]
            
            # Merge pages
            for i, page in enumerate(reader.pages):
                if i == page_number - 1:
                    # Merge signature and label onto target page
                    page.merge_page(overlay_page)
                writer.add_page(page)
            
            # Write output
            with open(output_pdf_path, 'wb') as output_file:
                writer.write(output_file)

            # Quick sanity-check: ensure file starts with %PDF
            try:
                with open(output_pdf_path, 'rb') as fcheck:
                    header = fcheck.read(4)
                    print(f"PDF output header bytes: {header}")
                    if not header.startswith(b'%PDF'):
                        print(f"ERROR: Output file does not start with %PDF: {output_pdf_path}")
                        return False
            except Exception as e:
                print(f"Error checking PDF header: {e}")
                return False

            return True
            
        except Exception as e:
            print(f"Error adding signature to PDF: {e}")
            return False
    
    @staticmethod
    def add_multiple_signatures_to_pdf(
        input_pdf_path: str,
        output_pdf_path: str,
        signatures_data: List[Dict],
        label_text: str = "Signature",
        signature_width: int = 150,
        signature_height: int = 50
    ) -> bool:
        """
        Add multiple signatures to PDF with specific coordinates and pages
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path to save signed PDF
            signatures_data: List of dicts containing signature data:
                [
                    {
                        'signature_image_path': str,
                        'page_number': int,
                        'x': float,
                        'y': float
                    },
                    ...
                ]
            label_text: Text to display as label near each signature
            signature_width, signature_height: Signature dimensions
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if all signature files exist
            for sig_data in signatures_data:
                if not os.path.exists(sig_data['signature_image_path']):
                    print(f"ERROR: Signature file not found at {sig_data['signature_image_path']}")
                    return False
            
            # Read original PDF
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            
            # Create a copy of all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Process each signature
            for sig_data in signatures_data:
                signature_image_path = sig_data.get('signature_image_path')
                page_number = sig_data.get('page', 1)
                x = sig_data.get('x', 0)
                y = sig_data.get('y', 0)
                
                # Validate required fields
                if not signature_image_path:
                    print(f"ERROR: Missing signature_image_path in signature data: {sig_data}")
                    continue
                
                # Get page dimensions
                target_page_index = page_number - 1
                if target_page_index >= len(writer.pages) or target_page_index < 0:
                    print(f"ERROR: Page {page_number} does not exist in the document")
                    continue
                
                target_page = writer.pages[target_page_index]
                mediabox = target_page.mediabox
                page_width = float(mediabox.width)
                page_height = float(mediabox.height)
                
                # Create signature overlay for this specific signature
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                
                # Add signature image at the exact x,y coordinates
                try:
                    can.drawImage(
                        signature_image_path,
                        x, y,
                        width=signature_width,
                        height=signature_height,
                        mask='auto'  # Preserve transparency
                    )
                except Exception as e:
                    print(f"Error adding signature image: {e}")
                
                # Add label text near the signature at the exact position
                can.setFont("Helvetica", 10)  # Use standard font
                can.setFillColorRGB(0, 0, 0)  # Black color
                
                # Position label relative to signature at the exact coordinates
                label_x = x + (signature_width / 2) - 20  # Center the label below the signature
                label_y = y - 15  # Place it 15 units below the signature
                can.drawString(label_x, label_y, label_text)
                
                can.save()
                packet.seek(0)
                
                # Read overlay
                overlay_reader = PdfReader(packet)
                overlay_page = overlay_reader.pages[0]
                
                # Merge signature and label onto target page
                target_page.merge_page(overlay_page)
            
            # Write final output
            with open(output_pdf_path, 'wb') as output_file:
                writer.write(output_file)

            # Quick sanity-check: ensure file starts with %PDF
            try:
                with open(output_pdf_path, 'rb') as fcheck:
                    header = fcheck.read(4)
                    print(f"PDF output header bytes: {header}")
                    if not header.startswith(b'%PDF'):
                        print(f"ERROR: Output file does not start with %PDF: {output_pdf_path}")
                        return False
            except Exception as e:
                print(f"Error checking PDF header: {e}")
                return False

            return True
        
        except Exception as e:
            print(f"Error adding multiple signatures to PDF: {e}")
            return False
    
    @staticmethod
    def add_signature_to_pdf_with_alignment(
        input_pdf_path: str,
        output_pdf_path: str,
        signature_image_path: str,
        page_number: int,
        label_text: str = "Signature",
        is_right_aligned: bool = False,
        signature_width: int = 150,
        signature_height: int = 50
    ) -> bool:
        """
        Add signature and its label to specific page of PDF with specific alignment
        
        Args:
            input_pdf_path: Path to input PDF
            output_pdf_path: Path to save signed PDF
            signature_image_path: Path to signature image
            page_number: Page to add signature (1-indexed)
            label_text: Text to display as label below the signature
            is_right_aligned: Whether to align signature and label to the right side
            signature_width, signature_height: Signature dimensions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if signature file exists
            import os
            if not os.path.exists(signature_image_path):
                print(f"ERROR: Signature file not found at {signature_image_path}")
                return False
            
            # Read original PDF
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            
            # Get page dimensions
            target_page = reader.pages[page_number - 1]
            mediabox = target_page.mediabox
            page_width = float(mediabox.width)
            page_height = float(mediabox.height)
            
            # Calculate x position based on alignment for both signature and label
            if is_right_aligned:
                x = page_width - signature_width - 50  # 50px right margin
            else:
                x = 50  # 50px left margin
            
            # Place near the bottom of the page (in PDF coordinates, y=0 is bottom)
            y = 50  # 50px from bottom
            
            # Create signature overlay with both signature and label
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            
            # Add signature image
            try:
                can.drawImage(
                    signature_image_path,
                    x, y,
                    width=signature_width,
                    height=signature_height,
                    mask='auto'  # Preserve transparency
                )
            except Exception as e:
                print(f"Error adding signature image: {e}")
            
            # Add label text below the signature
            can.setFont("Helvetica", 10)  # Use standard font
            can.setFillColorRGB(0, 0, 0)  # Black color
            label_x = x + (signature_width / 2) - 20  # Center the label below the signature
            label_y = y - 15  # Place it 15 units below the signature
            can.drawString(label_x, label_y, label_text)
            
            can.save()
            packet.seek(0)
            
            # Read overlay
            overlay_reader = PdfReader(packet)
            overlay_page = overlay_reader.pages[0]
            
            # Merge pages
            for i, page in enumerate(reader.pages):
                if i == page_number - 1:
                    # Merge signature and label onto target page
                    page.merge_page(overlay_page)
                writer.add_page(page)
            
            # Write output
            with open(output_pdf_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True
            
        except Exception as e:
            print(f"Error adding signature to PDF: {e}")
            return False

    @staticmethod
    def add_signature_to_pdf_end(
        input_pdf_path: str,
        output_pdf_path: str,
        signature_image_path: str,
        is_right_aligned: bool = False,
        label_text: str = "Signature",
        signature_width: int = 150,
        signature_height: int = 50
    ) -> bool:
        """
        Place a signature at the end (last page) of the PDF.
        """
        try:
            # Read original PDF to determine last page
            reader = PdfReader(input_pdf_path)
            num_pages = len(reader.pages)
            if num_pages == 0:
                print("PDF has no pages")
                return False

            last_page_number = num_pages

            # Delegate to alignment-based helper which places near page bottom
            return PDFProcessor.add_signature_to_pdf_with_alignment(
                input_pdf_path=input_pdf_path,
                output_pdf_path=output_pdf_path,
                signature_image_path=signature_image_path,
                page_number=last_page_number,
                label_text=label_text,
                is_right_aligned=is_right_aligned,
                signature_width=signature_width,
                signature_height=signature_height
            )
        except Exception as e:
            print(f"Error placing signature at PDF end: {e}")
            return False