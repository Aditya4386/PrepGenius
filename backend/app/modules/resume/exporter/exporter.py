"""
exporter.py — Export resume to ATS-friendly PDF using ReportLab.
"""

from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib import colors


# Color scheme
DARK_BLUE = HexColor("#1a3c5e")
MEDIUM_BLUE = HexColor("#2c5f8a")
LIGHT_GRAY = HexColor("#f5f5f5")
DARK_GRAY = HexColor("#333333")
MEDIUM_GRAY = HexColor("#666666")
ACCENT_BLUE = HexColor("#3498db")


def create_resume_pdf(resume_text: str, filename: str = "resume.pdf") -> bytes:
    """
    Create an ATS-friendly single-column PDF resume from text.

    Args:
        resume_text: Plain text resume with section headers
        filename: Output filename

    Returns:
        PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name='ResumeName',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=DARK_BLUE,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='ResumeContact',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=MEDIUM_GRAY,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=DARK_BLUE,
        spaceBefore=16,
        spaceAfter=6,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='SectionLine',
        parent=styles['Normal'],
        fontSize=1,
        leading=1,
        spaceBefore=0,
        spaceAfter=4,
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=DARK_GRAY,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
        leftIndent=0,
        rightIndent=0,
        firstLineIndent=0,
    ))

    styles.add(ParagraphStyle(
        name='BulletPoint',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=DARK_GRAY,
        spaceAfter=2,
        leftIndent=20,
        bulletIndent=8,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        name='SubBulletPoint',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=MEDIUM_GRAY,
        spaceAfter=1,
        leftIndent=36,
        bulletIndent=24,
        fontName='Helvetica',
    ))

    story = []

    # Parse resume text into sections
    sections = parse_resume_sections(resume_text)

    # Build story
    first_section = True
    for section_name, content in sections:
        if first_section and section_name.lower() in ['contact information', 'contact']:
            # Handle name and contact specially
            lines = content.strip().split('\n')
            if lines:
                story.append(Paragraph(lines[0].strip(), styles['ResumeName']))
                for line in lines[1:]:
                    if line.strip():
                        story.append(Paragraph(line.strip(), styles['ResumeContact']))
            first_section = False
            continue

        # Section header
        story.append(Paragraph(section_name.upper(), styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_BLUE, spaceAfter=6))
        story.append(Spacer(1, 4))

        # Section content
        content_elements = format_section_content(content, styles)
        story.extend(content_elements)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def parse_resume_sections(resume_text: str) -> list:
    """Parse resume text into (section_name, content) pairs."""
    sections = []
    current_section = None
    current_content = []

    lines = resume_text.split('\n')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if line is a section header (all caps or ends with colon, or known section)
        is_header = False
        section_keywords = [
            'contact', 'summary', 'objective', 'education', 'skills',
            'technical skills', 'projects', 'experience', 'work experience',
            'internship', 'achievements', 'certifications', 'publications',
            'volunteer', 'leadership', 'activities'
        ]

        lower_stripped = stripped.lower().rstrip(':')
        for kw in section_keywords:
            if lower_stripped == kw or lower_stripped.startswith(kw + ' ') or stripped.isupper():
                if len(stripped) < 50:  # Reasonable header length
                    is_header = True
                    break

        if is_header and current_section is not None:
            # Save previous section
            sections.append((current_section, '\n'.join(current_content)))
            current_content = []

        if is_header:
            current_section = stripped.rstrip(':')
        else:
            current_content.append(line)

    # Don't forget the last section
    if current_section is not None:
        sections.append((current_section, '\n'.join(current_content)))

    return sections


def format_section_content(content: str, styles) -> list:
    """Format section content into reportlab flowables."""
    elements = []
    lines = content.strip().split('\n')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for bullet points
        if stripped.startswith(('•', '-', '*', '·', '▸', '►', '→', '‣')):
            bullet_text = stripped.lstrip('•-*·▸►→‣ ').strip()
            elements.append(Paragraph(f"• {bullet_text}", styles['BulletPoint']))
        elif stripped.startswith(('  -', '  *', '    -', '    *', '\t-', '\t*')):
            # Sub-bullet
            bullet_text = stripped.lstrip(' -*\t').strip()
            elements.append(Paragraph(f"◦ {bullet_text}", styles['SubBulletPoint']))
        else:
            # Regular paragraph
            elements.append(Paragraph(stripped, styles['BodyText2']))

    return elements


def create_simple_resume_pdf(
    name: str,
    contact_lines: list,
    sections: dict,
    filename: str = "resume.pdf"
) -> bytes:
    """
    Create resume from structured data (alternative to text parsing).

    Args:
        name: Full name
        contact_lines: List of contact info lines (email, phone, LinkedIn, GitHub)
        sections: Dict of section_name -> content (string or list of strings)
        filename: Output filename

    Returns:
        PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Reuse styles from above
    styles.add(ParagraphStyle(
        name='ResumeName',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=DARK_BLUE,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='ResumeContact',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=MEDIUM_GRAY,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=DARK_BLUE,
        spaceBefore=16,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=DARK_GRAY,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
        fontName='Helvetica',
    ))

    styles.add(ParagraphStyle(
        name='BulletPoint',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=DARK_GRAY,
        spaceAfter=2,
        leftIndent=20,
        bulletIndent=8,
        fontName='Helvetica',
    ))

    story = []

    # Name
    story.append(Paragraph(name, styles['ResumeName']))

    # Contact info
    contact_text = " | ".join(contact_lines)
    story.append(Paragraph(contact_text, styles['ResumeContact']))

    # Sections in order
    section_order = [
        'Professional Summary',
        'Education',
        'Technical Skills',
        'Projects',
        'Work Experience',
        'Internships',
        'Achievements',
        'Certifications',
    ]

    for section_name in section_order:
        if section_name in sections and sections[section_name]:
            content = sections[section_name]
            story.append(Paragraph(section_name.upper(), styles['SectionHeader']))
            story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_BLUE, spaceAfter=6))
            story.append(Spacer(1, 4))

            if isinstance(content, list):
                for item in content:
                    if isinstance(item, str):
                        if item.strip().startswith(('•', '-', '*')):
                            story.append(Paragraph(f"• {item.strip().lstrip('•-* ').strip()}", styles['BulletPoint']))
                        else:
                            story.append(Paragraph(item.strip(), styles['BodyText2']))
            else:
                for line in str(content).split('\n'):
                    if line.strip():
                        if line.strip().startswith(('•', '-', '*')):
                            story.append(Paragraph(f"• {line.strip().lstrip('•-* ').strip()}", styles['BulletPoint']))
                        else:
                            story.append(Paragraph(line.strip(), styles['BodyText2']))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()