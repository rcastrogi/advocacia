"""
Serviço de conversão de arquivos para PDF.
Suporta: imagens (PNG, JPG, JPEG), TXT, DOCX, XLSX
"""

import io
import os
import subprocess
import tempfile
from typing import Tuple


def convert_to_pdf(file_data: bytes, filename: str) -> Tuple[bytes, str]:
    """
    Converte um arquivo para PDF.
    
    Args:
        file_data: Conteúdo do arquivo em bytes
        filename: Nome original do arquivo
        
    Returns:
        Tuple[bytes, str]: (dados do PDF, novo nome do arquivo com .pdf)
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    new_filename = f"{base_name}.pdf"
    
    # Se já é PDF, retorna sem conversão
    if ext == "pdf":
        return file_data, filename
    
    # Imagens
    if ext in ("png", "jpg", "jpeg", "gif", "bmp", "tiff"):
        return _convert_image_to_pdf(file_data, new_filename)
    
    # TXT
    if ext == "txt":
        return _convert_txt_to_pdf(file_data, new_filename)
    
    # DOCX
    if ext == "docx":
        return _convert_docx_to_pdf(file_data, new_filename)
    
    # DOC (Word antigo)
    if ext == "doc":
        return _convert_office_to_pdf(file_data, filename, new_filename)
    
    # Excel
    if ext in ("xlsx", "xls"):
        return _convert_office_to_pdf(file_data, filename, new_filename)
    
    # PowerPoint
    if ext in ("pptx", "ppt"):
        return _convert_office_to_pdf(file_data, filename, new_filename)
    
    # Formato não suportado - retorna original
    return file_data, filename


def _convert_image_to_pdf(image_data: bytes, new_filename: str) -> Tuple[bytes, str]:
    """Converte imagem para PDF usando Pillow"""
    try:
        from PIL import Image
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.utils import ImageReader
        
        # Abrir imagem
        img = Image.open(io.BytesIO(image_data))
        
        # Converter para RGB se necessário (para RGBA, CMYK, etc)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calcular dimensões mantendo proporção dentro de A4
        page_width, page_height = A4
        margin = 40  # margem de 40 pontos
        max_width = page_width - (2 * margin)
        max_height = page_height - (2 * margin)
        
        img_width, img_height = img.size
        
        # Calcular escala para caber na página
        scale = min(max_width / img_width, max_height / img_height, 1.0)
        new_width = img_width * scale
        new_height = img_height * scale
        
        # Centralizar na página
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2
        
        # Criar PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Salvar imagem temporária para ImageReader
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        c.drawImage(ImageReader(img_buffer), x, y, width=new_width, height=new_height)
        c.save()
        
        buffer.seek(0)
        return buffer.read(), new_filename
        
    except ImportError:
        # Fallback: retornar original se bibliotecas não disponíveis
        return image_data, new_filename.replace('.pdf', '.png')
    except Exception as e:
        print(f"Erro ao converter imagem para PDF: {e}")
        return image_data, new_filename.replace('.pdf', '.png')


def _convert_txt_to_pdf(txt_data: bytes, new_filename: str) -> Tuple[bytes, str]:
    """Converte TXT para PDF usando ReportLab"""
    try:
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        
        # Decodificar texto
        try:
            text = txt_data.decode('utf-8')
        except UnicodeDecodeError:
            text = txt_data.decode('latin-1')
        
        # Criar PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        page_width, page_height = A4
        margin = 2 * cm
        text_width = page_width - (2 * margin)
        
        # Configurar fonte
        c.setFont("Helvetica", 10)
        
        # Quebrar texto em linhas
        lines = text.split('\n')
        y = page_height - margin
        line_height = 14
        
        for line in lines:
            # Quebrar linhas longas
            while len(line) > 0:
                # Estimar caracteres por linha (aproximadamente)
                chars_per_line = int(text_width / 5)  # ~5 pontos por caractere
                
                if len(line) <= chars_per_line:
                    c.drawString(margin, y, line)
                    line = ""
                else:
                    # Encontrar ponto de quebra
                    break_point = line.rfind(' ', 0, chars_per_line)
                    if break_point == -1:
                        break_point = chars_per_line
                    
                    c.drawString(margin, y, line[:break_point])
                    line = line[break_point:].lstrip()
                
                y -= line_height
                
                # Nova página se necessário
                if y < margin:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = page_height - margin
        
        c.save()
        buffer.seek(0)
        return buffer.read(), new_filename
        
    except ImportError:
        return txt_data, new_filename.replace('.pdf', '.txt')
    except Exception as e:
        print(f"Erro ao converter TXT para PDF: {e}")
        return txt_data, new_filename.replace('.pdf', '.txt')


def _convert_docx_to_pdf(docx_data: bytes, new_filename: str) -> Tuple[bytes, str]:
    """Converte DOCX para PDF usando python-docx e ReportLab"""
    try:
        from docx import Document  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.enums import TA_JUSTIFY
        
        # Abrir DOCX
        doc = Document(io.BytesIO(docx_data))
        
        # Criar PDF com ReportLab
        buffer = io.BytesIO()
        pdf = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Estilo personalizado para texto normal
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY
        )
        
        # Estilo para títulos
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=14,
            leading=18,
            spaceAfter=12
        )
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                story.append(Spacer(1, 6))
                continue
            
            # Escapar caracteres especiais do HTML
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            
            # Verificar se é título (baseado no estilo)
            style_name = para.style.name if para.style else ''
            if 'Heading' in style_name or 'Title' in style_name:
                story.append(Paragraph(text, heading_style))
            else:
                story.append(Paragraph(text, normal_style))
        
        if story:
            pdf.build(story)
        else:
            # Documento vazio - criar página em branco
            c = canvas.Canvas(buffer, pagesize=A4)
            c.drawString(100, 700, "(Documento vazio)")
            c.save()
        
        buffer.seek(0)
        return buffer.read(), new_filename
        
    except ImportError:
        # Tentar conversão via LibreOffice como fallback
        return _convert_office_to_pdf(docx_data, 'temp.docx', new_filename)
    except Exception as e:
        print(f"Erro ao converter DOCX para PDF: {e}")
        return _convert_office_to_pdf(docx_data, 'temp.docx', new_filename)


def _convert_office_to_pdf(file_data: bytes, original_filename: str, new_filename: str) -> Tuple[bytes, str]:
    """
    Converte arquivos Office (DOC, XLS, PPT) para PDF usando LibreOffice.
    Requer LibreOffice instalado no servidor.
    """
    try:
        # Criar arquivo temporário
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "tmp"
        
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp_in:
            tmp_in.write(file_data)
            tmp_in_path = tmp_in.name
        
        try:
            # Diretório de saída
            tmp_dir = tempfile.mkdtemp()
            
            # Tentar diferentes caminhos do LibreOffice
            libreoffice_paths = [
                'libreoffice',  # Linux (PATH)
                'soffice',  # Alternativo
                '/usr/bin/libreoffice',
                '/usr/bin/soffice',
                '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # macOS
                r'C:\Program Files\LibreOffice\program\soffice.exe',  # Windows
                r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
            ]
            
            libreoffice_cmd = None
            for path in libreoffice_paths:
                try:
                    # Verificar se existe
                    result = subprocess.run(
                        [path, '--version'],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        libreoffice_cmd = path
                        break
                except (subprocess.SubprocessError, FileNotFoundError, OSError):
                    continue
            
            if not libreoffice_cmd:
                print("LibreOffice não encontrado - retornando arquivo original")
                return file_data, original_filename
            
            # Converter para PDF
            result = subprocess.run(
                [
                    libreoffice_cmd,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', tmp_dir,
                    tmp_in_path
                ],
                capture_output=True,
                timeout=60  # 60 segundos de timeout
            )
            
            if result.returncode != 0:
                print(f"Erro LibreOffice: {result.stderr.decode()}")
                return file_data, original_filename
            
            # Encontrar arquivo PDF gerado
            base_name = os.path.splitext(os.path.basename(tmp_in_path))[0]
            pdf_path = os.path.join(tmp_dir, f"{base_name}.pdf")
            
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Limpar arquivos temporários
                os.unlink(pdf_path)
                os.rmdir(tmp_dir)
                
                return pdf_data, new_filename
            else:
                print(f"PDF não gerado: {pdf_path}")
                return file_data, original_filename
                
        finally:
            # Limpar arquivo de entrada temporário
            if os.path.exists(tmp_in_path):
                os.unlink(tmp_in_path)
                
    except Exception as e:
        print(f"Erro na conversão Office para PDF: {e}")
        return file_data, original_filename


def is_pdf_conversion_available() -> dict:
    """
    Verifica quais conversões estão disponíveis no servidor.
    
    Returns:
        dict: Status de cada tipo de conversão
    """
    status = {
        'images': False,
        'txt': False,
        'docx': False,
        'office': False
    }
    
    # Verificar Pillow + ReportLab (imagens e TXT)
    try:
        from PIL import Image  # type: ignore # noqa: F401
        from reportlab.pdfgen import canvas  # type: ignore # noqa: F401
        status['images'] = True
        status['txt'] = True
    except ImportError:
        pass
    
    # Verificar python-docx
    try:
        from docx import Document  # type: ignore # noqa: F401
        status['docx'] = True
    except ImportError:
        pass
    
    # Verificar LibreOffice
    try:
        result = subprocess.run(
            ['libreoffice', '--version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            status['office'] = True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return status


# Extensões que podem ser convertidas para PDF
CONVERTIBLE_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff',  # Imagens
    'txt',  # Texto
    'doc', 'docx',  # Word
    'xls', 'xlsx',  # Excel
    'ppt', 'pptx',  # PowerPoint
    'pdf'  # Já é PDF
}
