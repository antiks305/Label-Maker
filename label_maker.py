"""
Mother's Product Label Maker
----------------------------
A simple Windows desktop application for creating soap and lip gloss labels.

Features
- Fixed label dimensions for soap and lip gloss
- Product name field
- Ingredient checkboxes
- Save and reopen product recipes
- Print-ready US Letter PDF with multiple copies per sheet
- Solid black label border
- Clean layout with no dashed cut lines

Install dependencies in the VS Code terminal:
    py -m pip install PySide6 reportlab

Run:
    py label_maker.py
"""

import json
import math
import shutil
import sys
import tempfile
from pathlib import Path
from io import BytesIO

from PySide6.QtCore import Qt, QBuffer, QByteArray, QIODevice, QSize, QTimer
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
    QWidget, QInputDialog, QTabWidget
)
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtGui import QPageSize, QPageLayout

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


APP_DIR = Path.home() / "LabelMaker"
RECIPES_FILE = APP_DIR / "saved_labels.json"
INGREDIENTS_FILE = APP_DIR / "ingredients.json"
OUTPUT_DIR = APP_DIR / "PDFs"
LOGO_SETTINGS_FILE = APP_DIR / "logo_settings.json"

# Dimensions are the solid-border label dimensions, in inches.
PRODUCTS = {
    "Soap": {"width": 2.25, "height": 2.625},
    "Lip Gloss": {"width": 2.0, "height": 1.0},
}


# UI translations. Ingredient names and label artwork remain exactly as entered.
TRANSLATIONS = {
    "Soap & Lip Gloss Label Maker": "Creador de etiquetas para jabón y brillo labial",
    "Create a label, save its recipe, and generate a one-page US Letter PDF with a full sheet of labels.": "Crea una etiqueta, guarda su receta y genera un PDF tamaño carta de una página con una hoja completa de etiquetas.",
    "Product type:": "Tipo de producto:", "Product name:": "Nombre del producto:",
    "e.g. Lavender Oatmeal": "p. ej., lavanda y avena", "Enter amount, e.g. 4 or 5.5": "Introduce la cantidad, p. ej., 4 o 5,5",
    "Company logo — shared by Soap and Lip Gloss": "Logotipo de la empresa — compartido por jabón y brillo labial",
    "No logo selected": "No se ha seleccionado ningún logotipo", "Choose logo…": "Elegir logotipo…", "Remove logo": "Quitar logotipo",
    "The same logo is used for both products.": "Se usa el mismo logotipo para ambos productos.",
    "Ingredients — check all used in this product": "Ingredientes — marca todos los que se usan en este producto",
    "Search ingredients…": "Buscar ingredientes…", "Selected ingredients — print order (use arrows to reorder):": "Ingredientes seleccionados — orden de impresión (usa las flechas para reordenar):",
    "Move up": "Subir", "Move down": "Bajar", "Manage ingredient library": "Administrar biblioteca de ingredientes",
    "Saved labels": "Etiquetas guardadas", "Search soap labels…": "Buscar etiquetas de jabón…", "Search lip gloss labels…": "Buscar etiquetas de brillo labial…",
    "Soap Labels": "Etiquetas de jabón", "Lip Gloss Labels": "Etiquetas de brillo labial",
    "Save current label": "Guardar etiqueta actual", "Load selected": "Cargar seleccionada", "Delete selected": "Eliminar seleccionada",
    "Live label preview": "Vista previa de la etiqueta", "Preview updates as you edit the name, ingredients, quantity, or logo.": "La vista previa se actualiza al editar el nombre, los ingredientes, la cantidad o el logotipo.",
    "Content fits the label layout.": "El contenido cabe en el diseño de la etiqueta.", "Print": "Imprimir",
    "One full sheet per PDF: 9 soap labels or 21 lip gloss labels.": "Una hoja completa por PDF: 9 etiquetas de jabón o 21 de brillo labial.",
    "Print and export": "Imprimir y exportar", "Print Labels": "Imprimir etiquetas",
    "Save as PDF": "Guardar como PDF",
    "Create print-ready PDF": "Crear PDF listo para imprimir",
    "Print labels": "Imprimir etiquetas", "Print labels — preview": "Vista previa de impresión de etiquetas", "Preparing print job…": "Preparando impresión…",
    "Could not print labels": "No se pudieron imprimir las etiquetas",
    "Printing started": "Impresión iniciada",
    "No valid printer is available. Check that a printer is installed and ready.": "No hay una impresora válida disponible. Comprueba que haya una impresora instalada y lista.",
    "Could not start the print job. Check the selected printer and try again.": "No se pudo iniciar la impresión. Comprueba la impresora seleccionada e inténtalo de nuevo.",
    "The print preview was accepted. Check the printer queue to confirm the job is progressing.": "Se aceptó la vista previa de impresión. Comprueba la cola de impresión para confirmar que el trabajo continúa.",
    "For correct label dimensions, use US Letter paper and Actual Size / 100% scaling where available.": "Para conservar las dimensiones de las etiquetas, usa papel tamaño carta y escala Tamaño real / 100 % cuando esté disponible.",
    "The label sheet was sent to the selected printer. Check the printer dialog for Actual Size / 100% scaling if available.": "La hoja de etiquetas se envió a la impresora seleccionada. Comprueba que el diálogo de impresión use Tamaño real / 100 % si está disponible.",
    "Printing was cancelled.": "Se canceló la impresión.",
    "The PDF could not be loaded for printing.": "No se pudo cargar el PDF para imprimir.",
    "Print at Actual Size / 100% (turn off Fit to Page). Solid black border = label edge; no dashed cut lines are printed.": "Imprime en Tamaño real / 100 % (desactiva Ajustar a página). El borde negro sólido marca el borde de la etiqueta; no se imprimen líneas de corte discontinuas.",
    "Approximate soap weight (oz):": "Peso aproximado del jabón (oz):", "Net contents (mL):": "Contenido neto (mL):",
    "e.g. 4 or 4.5": "p. ej., 4 o 4,5", "e.g. 5 or 10": "p. ej., 5 o 10",
    "Preview unavailable": "Vista previa no disponible", "Selected: ": "Seleccionado: ",
    "Manage Ingredients": "Administrar ingredientes", "Ingredient list for:": "Lista de ingredientes para:",
    "Save": "Guardar", "Cancel": "Cancelar",
    "New ingredient name": "Nombre del ingrediente nuevo", "Add": "Añadir", "Remove selected": "Eliminar seleccionado",
    "Choose company logo": "Elegir logotipo de la empresa", "Image files (*.png *.jpg *.jpeg);;PNG files (*.png);;JPEG files (*.jpg *.jpeg)": "Archivos de imagen (*.png *.jpg *.jpeg);;Archivos PNG (*.png);;Archivos JPEG (*.jpg *.jpeg)",
    "Unsupported image": "Imagen no compatible", "Choose a valid PNG or JPG/JPEG image file.": "Elige un archivo de imagen PNG o JPG/JPEG válido.",
    "Only PNG and JPG/JPEG logo files are supported.": "Solo se admiten logotipos PNG y JPG/JPEG.",
    "Could not save logo": "No se pudo guardar el logotipo", "Could not remove logo": "No se pudo quitar el logotipo",
    "Product name required": "Se requiere el nombre del producto", "Enter a product name before saving.": "Introduce el nombre del producto antes de guardar.",
    "Saved": "Guardado", "The label recipe has been saved.": "Se ha guardado la receta de la etiqueta.",
    "Select a label": "Selecciona una etiqueta", "Choose a saved label first.": "Primero elige una etiqueta guardada.",
    "Delete saved label": "Eliminar etiqueta guardada", "this label": "esta etiqueta",
    "Save print-ready PDF": "Guardar PDF listo para imprimir", "PDF files (*.pdf)": "Archivos PDF (*.pdf)",
    "Could not create PDF": "No se pudo crear el PDF", "PDF created": "PDF creado",
    "PDF saved successfully.": "El PDF se ha guardado correctamente.", "Labels on this page:": "Etiquetas en esta página:",
    "Open the PDF and print using Actual Size / 100%.": "Abre el PDF e imprime usando Tamaño real / 100 %.",
}


def translated(text, language):
    if language != "Español":
        return text
    if text in TRANSLATIONS:
        return TRANSLATIONS[text]
    # Translate the product-specific search placeholders without affecting saved data.
    if text.startswith("Search ") and text.endswith(" labels…"):
        product = text[len("Search "):-len(" labels…")]
        return f"Buscar etiquetas de {'jabón' if product == 'soap' else 'brillo labial'}…"
    return text

# Editable starter lists. These are examples, not a verified recipe or
# a complete legally compliant ingredient declaration.
DEFAULT_INGREDIENTS = {
    "Soap": [
        "Olive oil", "Coconut oil", "Shea butter", "Castor oil",
        "Cocoa butter", "Distilled water", "Sodium hydroxide",
        "Fragrance oil", "Essential oil", "Colorant", "Mica"
    ],
    "Lip Gloss": [
        "Castor oil", "Jojoba oil", "Vitamin E", "Beeswax",
        "Shea butter", "Mica", "Flavor oil", "Sweet almond oil"
    ],
}

# Print layout settings, in inches.
PAGE_MARGIN = 0.35
LABEL_GAP = 0.22
# Keep a little invisible clearance around each label in the grid.
# No dashed cut lines are printed.
LABEL_CLEARANCE = 0.08
LABEL_BORDER_WIDTH = 0.8


def ensure_files():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INGREDIENTS_FILE.exists():
        INGREDIENTS_FILE.write_text(
            json.dumps(DEFAULT_INGREDIENTS, indent=2), encoding="utf-8"
        )
    if not RECIPES_FILE.exists():
        RECIPES_FILE.write_text("[]", encoding="utf-8")


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def fit_font_size(c, text, font_name, max_size, max_width, min_size=5.5):
    """Choose a font size that fits one line within max_width."""
    size = max_size
    while size > min_size and c.stringWidth(text, font_name, size) > max_width:
        size -= 0.25
    return max(size, min_size)


def wrap_text(c, text, font_name, font_size, max_width):
    """Wrap text using ReportLab measurements, including unusually long words."""
    words = str(text).split()
    if not words:
        return [""]

    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
            continue

        if current:
            lines.append(current)
            current = ""

        # A single unbroken word may be wider than the label. Split it by
        # character without changing the chosen font size.
        fragment = ""
        for char in word:
            candidate = fragment + char
            if fragment and c.stringWidth(candidate, font_name, font_size) > max_width:
                lines.append(fragment)
                fragment = char
            else:
                fragment = candidate
        current = fragment

    if current:
        lines.append(current)
    return lines


def draw_justified_line(c, text, x, y, max_width, font_name, font_size, justify=True):
    """Draw a line flush left and right by distributing extra space between words.

    The final line of a paragraph should pass justify=False so it keeps natural
    spacing rather than looking stretched.
    """
    text = str(text).strip()
    words = text.split()
    if not text:
        return
    c.setFont(font_name, font_size)
    if not justify or len(words) < 2:
        c.drawString(x, y, text)
        return

    natural_width = c.stringWidth(text, font_name, font_size)
    gaps = len(words) - 1
    extra_space = max(0.0, (max_width - natural_width) / gaps)
    # Avoid exaggerated gaps on short lines; fall back to ordinary left alignment.
    if extra_space > font_size * 2.5:
        c.drawString(x, y, text)
        return

    cursor_x = x
    for index, word in enumerate(words):
        c.drawString(cursor_x, y, word)
        cursor_x += c.stringWidth(word, font_name, font_size)
        if index < gaps:
            cursor_x += c.stringWidth(" ", font_name, font_size) + extra_space


def label_fit_warnings(product_type, name, ingredients, logo_path=None):
    """Return layout warnings for content that may not fit on the physical label."""
    dims = PRODUCTS[product_type]
    w = dims["width"] * inch
    h = dims["height"] * inch
    pad = 0.10 * inch
    inner_w = w - 2 * pad
    top = h - pad
    logo_bottom = top
    if logo_path and Path(logo_path).is_file():
        try:
            logo_image = ImageReader(str(logo_path))
            logo_w, logo_h = logo_image.getSize()
            if logo_w > 0 and logo_h > 0:
                logo_max_h = h * (0.27 if product_type == "Soap" else 0.24)
                logo_max_w = inner_w * 0.88
                scale = min(logo_max_w / logo_w, logo_max_h / logo_h)
                logo_bottom = h - pad - logo_h * scale - (0.035 * inch)
        except Exception:
            pass

    name = (name or "").strip() or product_type
    title_size = 14.0 if product_type == "Soap" else 8.5
    title_lines = wrap_text(_MEASURE_CANVAS, name, "Helvetica-Bold", title_size, inner_w)
    title_line_height = title_size * 1.12
    first_title_y = logo_bottom - title_size
    title_last_y = first_title_y - (len(title_lines) - 1) * title_line_height
    title_gap = 4 if product_type == "Soap" else 2
    ingredient_section_y = title_last_y - title_gap

    warning_font = 5.0 if product_type == "Soap" else 4.5
    quantity_font = 5.8 if product_type == "Soap" else 4.5
    bottom_text_y = pad
    ingredient_bottom = bottom_text_y + max(warning_font, quantity_font) + 1.0
    label_font = 7.2 if product_type == "Soap" else 5.2
    body_font = 6.8 if product_type == "Soap" else 5.0
    heading = "INGREDIENTS"
    heading_y = ingredient_section_y - label_font - (3 if product_type == "Soap" else 0)
    ingredient_text = ", ".join(ingredients) if ingredients else "No ingredients selected"
    warnings = []

    if product_type == "Lip Gloss":
        heading_y = ingredient_section_y - label_font
        heading_width = _MEASURE_CANVAS.stringWidth(heading, "Helvetica-Bold", label_font)
        first_line_width = max(1, inner_w - heading_width - 3.0)
        words = ingredient_text.split()
        first_line = ""
        remaining = list(words)
        while remaining:
            trial = (first_line + " " + remaining[0]).strip()
            if _MEASURE_CANVAS.stringWidth(trial, "Helvetica", body_font) <= first_line_width:
                first_line = trial
                remaining.pop(0)
            else:
                break
        continuation = wrap_text(_MEASURE_CANVAS, " ".join(remaining), "Helvetica", body_font, inner_w) if remaining else []
        if not first_line and words:
            continuation = wrap_text(_MEASURE_CANVAS, ingredient_text, "Helvetica", body_font, inner_w)
        line_height = body_font + 0.5
        max_continuations = max(0, int((heading_y - ingredient_bottom) // line_height))
        if len(continuation) > max_continuations:
            warnings.append(f"Ingredients exceed the Lip Gloss label by about {len(continuation) - max_continuations} line(s). Remove ingredients or shorten the product name.")
    else:
        lines = wrap_text(_MEASURE_CANVAS, ingredient_text, "Helvetica", body_font, inner_w)
        line_height = body_font + 1.2
        available_height = heading_y - ingredient_bottom - label_font - 2
        max_lines = max(0, int(available_height / line_height))
        if len(lines) > max_lines:
            warnings.append(f"Ingredients exceed the Soap label by about {len(lines) - max_lines} line(s). Remove ingredients or shorten the product name.")

    if ingredient_section_y < ingredient_bottom + label_font:
        warnings.append("The product name is too long to leave enough room for the ingredients. Shorten the name.")
    return warnings


# A tiny off-page canvas used only for accurate ReportLab text measurements.
_MEASURE_BUFFER = BytesIO()
_MEASURE_CANVAS = canvas.Canvas(_MEASURE_BUFFER, pagesize=letter)


def draw_label(c, x, y, product_type, name, ingredients, logo_path=None, quantity=""):
    """
    Draw one label at bottom-left (x, y). Only the solid black label border
    is printed; no dashed cut guides are drawn.
    """
    dims = PRODUCTS[product_type]
    w = dims["width"] * inch
    h = dims["height"] * inch
    # Solid black label border.
    c.saveState()
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(LABEL_BORDER_WIDTH)
    c.setDash()
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.restoreState()

    pad = 0.10 * inch
    inner_w = w - 2 * pad
    top = y + h - pad

    # Shared company logo: centered at the top and kept within about 27% of
    # the label height. PNG and JPEG/JPG files are supported.
    logo_bottom = top
    if logo_path and Path(logo_path).is_file():
        # Lip gloss now places the INGREDIENTS heading inline with the first
        # ingredient line, freeing vertical space for a more legible logo.
        logo_max_h = h * (0.27 if product_type == "Soap" else 0.24)
        logo_max_w = inner_w * 0.88
        try:
            logo_image = ImageReader(str(logo_path))
            logo_w, logo_h = logo_image.getSize()
            if logo_w > 0 and logo_h > 0:
                scale = min(logo_max_w / logo_w, logo_max_h / logo_h)
                draw_w = logo_w * scale
                draw_h = logo_h * scale
                logo_x = x + (w - draw_w) / 2
                logo_y = y + h - pad - draw_h
                c.drawImage(
                    logo_image, logo_x, logo_y, width=draw_w, height=draw_h,
                    preserveAspectRatio=True, mask="auto"
                )
                # Leave a small gap between the logo and the product name.
                logo_bottom = logo_y - (0.035 * inch)
        except Exception:
            # Do not prevent label printing if a saved image is unreadable.
            logo_bottom = top

    # Product name uses a fixed font size for its product type. Long names wrap
    # to additional centered lines instead of shrinking to fit one line.
    name = name.strip() or product_type
    title_size = 14.0 if product_type == "Soap" else 8.5
    title_lines = wrap_text(c, name, "Helvetica-Bold", title_size, inner_w)
    title_line_height = title_size * 1.12
    first_title_y = logo_bottom - title_size
    c.setFont("Helvetica-Bold", title_size)
    for index, title_line in enumerate(title_lines):
        c.drawCentredString(
            x + w / 2, first_title_y - index * title_line_height, title_line
        )
    title_last_y = first_title_y - (len(title_lines) - 1) * title_line_height

    # No divider is drawn between the product name and ingredients. The
    # ingredient section moves down with each additional title line.
    title_gap = 4 if product_type == "Soap" else 2
    ingredient_section_y = title_last_y - title_gap

    # Warning and quantity share the same bottom line.
    warning_font = 5.0 if product_type == "Soap" else 4.5
    quantity_font = 5.8 if product_type == "Soap" else 4.5
    warning_text = "If irritation occurs, discontinue use."
    bottom_text_y = y + pad
    c.setFont("Helvetica", warning_font)
    c.drawString(x + pad, bottom_text_y, warning_text)

    quantity = (quantity or "").strip()
    if product_type == "Soap":
        quantity_text = f"Approx. wt. {quantity} oz" if quantity else "Approx. wt. ____ oz"
    else:
        quantity_text = f"Net contents {quantity} mL" if quantity else "Net contents ____ mL"
    c.setFont("Helvetica-Bold", quantity_font)
    c.drawRightString(x + w - pad, bottom_text_y, quantity_text)

    # Ingredients section.
    label_font = 7.2 if product_type == "Soap" else 5.2
    body_font = 6.8 if product_type == "Soap" else 5.0
    heading = "INGREDIENTS"
    c.setFont("Helvetica-Bold", label_font)
    heading_gap = 3 if product_type == "Soap" else 1.5
    heading_y = ingredient_section_y - label_font - heading_gap

    ingredient_text = ", ".join(ingredients) if ingredients else "No ingredients selected"
    ingredient_bottom = bottom_text_y + max(warning_font, quantity_font) + 1.0

    if product_type == "Lip Gloss":
        # Keep ingredient text at a legible fixed size (never below 4.5 pt).
        # The heading shares the first line when there is room; remaining
        # ingredient text wraps across the full label width.
        heading_y = ingredient_section_y - label_font
        heading_width = c.stringWidth(heading, "Helvetica-Bold", label_font)
        inline_gap = 3.0
        first_line_width = max(1, inner_w - heading_width - inline_gap)
        words = ingredient_text.split()
        first_line = ""
        remaining = list(words)
        while remaining:
            trial = (first_line + " " + remaining[0]).strip()
            if c.stringWidth(trial, "Helvetica", body_font) <= first_line_width:
                first_line = trial
                remaining.pop(0)
            else:
                break

        # If even the first ingredient cannot fit beside the heading, place
        # it on the next line at the same font size instead of clipping it.
        continuation = wrap_text(c, " ".join(remaining), "Helvetica", body_font, inner_w) if remaining else []
        if not first_line and words:
            continuation = wrap_text(c, ingredient_text, "Helvetica", body_font, inner_w)

        line_height = body_font + 0.5
        c.setFont("Helvetica-Bold", label_font)
        c.drawString(x + pad, heading_y, heading)
        c.setFont("Helvetica", body_font)
        if first_line:
            c.drawString(x + pad + heading_width + inline_gap, heading_y, first_line)
        for index, line in enumerate(continuation, start=1):
            line_y = heading_y - index * line_height
            if line_y < ingredient_bottom:
                break
            draw_justified_line(
                c, line, x + pad, line_y, inner_w, "Helvetica", body_font,
                justify=(index < len(continuation))
            )
    else:
        c.setFont("Helvetica-Bold", label_font)
        c.drawString(x + pad, heading_y, heading)
        lines = wrap_text(c, ingredient_text, "Helvetica", body_font, inner_w)
        line_height = body_font + 1.2
        available_height = heading_y - ingredient_bottom - label_font - 2
        max_lines = max(0, int(available_height / line_height))
        c.setFont("Helvetica", body_font)
        body_y = heading_y - label_font - 2
        visible_lines = lines[:max_lines]
        for line_index, line in enumerate(visible_lines):
            if body_y < ingredient_bottom:
                break
            draw_justified_line(
                c, line, x + pad, body_y, inner_w, "Helvetica", body_font,
                justify=(line_index < len(visible_lines) - 1)
            )
            body_y -= line_height


def generate_pdf(path, product_type, name, ingredients, copies, logo_path=None, quantity=""):
    page_w, page_h = letter
    dims = PRODUCTS[product_type]
    label_w = dims["width"] * inch
    label_h = dims["height"] * inch
    # Reserve invisible clearance around labels to preserve the intended
    # 3 x 3 soap and 3 x 7 lip gloss layouts without printing cut lines.
    offset = LABEL_CLEARANCE * inch
    gap = LABEL_GAP * inch
    margin = PAGE_MARGIN * inch

    # Grid spacing includes invisible clearance; only label borders are printed.
    footprint_w = label_w + 2 * offset
    footprint_h = label_h + 2 * offset
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin

    cols = max(1, int((usable_w + gap) // (footprint_w + gap)))
    rows = max(1, int((usable_h + gap) // (footprint_h + gap)))
    per_page = cols * rows

    if footprint_w > usable_w or footprint_h > usable_h:
        raise ValueError("The label does not fit within the printable page margins.")

    # This app intentionally creates exactly one full sheet per PDF:
    # 9 soap labels (3 x 3) or 21 lip gloss labels (3 x 7).
    expected_per_page = 9 if product_type == "Soap" else 21
    if per_page != expected_per_page:
        raise ValueError(
            f"The current page layout fits {per_page} labels, but {product_type} should fit "
            f"{expected_per_page}. Check the label dimensions, margins, and spacing."
        )

    c = canvas.Canvas(str(path), pagesize=letter)
    c.setTitle(f"{product_type} labels - {name}")

    # Center the complete grid horizontally and vertically on the page.
    grid_w = cols * footprint_w + (cols - 1) * gap
    grid_h = rows * footprint_h + (rows - 1) * gap
    grid_left = (page_w - grid_w) / 2
    grid_bottom = (page_h - grid_h) / 2

    for i in range(per_page):
        row = i // cols
        col = i % cols
        # Start from the top row for intuitive page layout.
        outer_left = grid_left + col * (footprint_w + gap)
        outer_top = page_h - grid_bottom - row * (footprint_h + gap)
        x = outer_left + offset
        y = outer_top - footprint_h + offset
        draw_label(c, x, y, product_type, name, ingredients, logo_path=logo_path, quantity=quantity)

    c.save()
    return cols, rows, per_page


class LabelPreview(QLabel):
    """Displays a rasterized image of the exact ReportLab label layout."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_image = QPixmap()
        self.setMinimumSize(220, 220)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #eeeeee; border: 1px solid #cccccc;")
        self.setText("Preparing preview…")

    def set_preview_image(self, image):
        self._source_image = QPixmap.fromImage(image) if image is not None and not image.isNull() else QPixmap()
        self._refresh_scaled_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_scaled_image()

    def _refresh_scaled_image(self):
        if self._source_image.isNull():
            return
        self.setText("")
        self.setPixmap(self._source_image.scaled(
            max(1, self.contentsRect().width() - 20),
            max(1, self.contentsRect().height() - 20),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))


def render_label_preview(product_type, name, ingredients, quantity, logo_path, target_width=1200):
    """Render the shared ReportLab label function to an in-memory PDF, then to QImage.

    This deliberately calls draw_label(), the same layout function used for the
    print PDF, so font sizing, wrapping, logo placement, margins, and baselines match.
    The temporary PDF exists only in memory and is never written to the output folder.
    """
    dims = PRODUCTS[product_type]
    label_w = dims["width"] * inch
    label_h = dims["height"] * inch
    # A tiny temporary page margin prevents the border stroke from being clipped
    # by the PDF page edge. We crop that margin from the rendered image below.
    margin_pt = 1.5
    page_w = label_w + 2 * margin_pt
    page_h = label_h + 2 * margin_pt
    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=(page_w, page_h), pageCompression=1)
    pdf_canvas.setTitle(f"{product_type} label preview")
    draw_label(
        pdf_canvas, margin_pt, margin_pt, product_type, name, ingredients,
        logo_path=logo_path, quantity=quantity,
    )
    pdf_canvas.showPage()
    pdf_canvas.save()

    # Keep the QBuffer alive while QPdfDocument reads it.
    device = QBuffer()
    device.setData(QByteArray(pdf_buffer.getvalue()))
    if not device.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError("Could not open the in-memory label preview.")
    document = QPdfDocument()
    document.load(device)
    if document.status() != QPdfDocument.Status.Ready:
        error = document.error()
        document.close()
        device.close()
        raise RuntimeError(f"Qt could not render the label preview PDF (error: {error}).")

    target_height = max(1, round(target_width * page_h / page_w))
    rendered = document.render(0, QSize(target_width, target_height))
    document.close()
    device.close()
    if rendered.isNull():
        raise RuntimeError("The label preview image could not be rendered.")

    crop_x = round(margin_pt / page_w * rendered.width())
    crop_y = round(margin_pt / page_h * rendered.height())
    crop_w = max(1, round(label_w / page_w * rendered.width()))
    crop_h = max(1, round(label_h / page_h * rendered.height()))
    return rendered.copy(crop_x, crop_y, crop_w, crop_h)


class IngredientManager(QDialog):
    def __init__(self, ingredients, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Ingredients")
        self.resize(440, 430)
        self.ingredients = ingredients

        layout = QVBoxLayout(self)
        self.product_combo = QComboBox()
        self.product_combo.addItems(list(PRODUCTS.keys()))
        layout.addWidget(QLabel("Ingredient list for:"))
        layout.addWidget(self.product_combo)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        row = QHBoxLayout()
        self.new_ingredient = QLineEdit()
        self.new_ingredient.setPlaceholderText("New ingredient name")
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove selected")
        row.addWidget(self.new_ingredient, 1)
        row.addWidget(add_btn)
        layout.addLayout(row)
        layout.addWidget(remove_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        self.product_combo.currentTextChanged.connect(self.refresh_list)
        add_btn.clicked.connect(self.add_ingredient)
        remove_btn.clicked.connect(self.remove_ingredient)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for item in self.ingredients.get(self.product_combo.currentText(), []):
            self.list_widget.addItem(item)

    def add_ingredient(self):
        text = self.new_ingredient.text().strip()
        if not text:
            return
        product = self.product_combo.currentText()
        values = self.ingredients.setdefault(product, [])
        if text.casefold() not in {v.casefold() for v in values}:
            values.append(text)
            values.sort(key=str.casefold)
            self.new_ingredient.clear()
            self.refresh_list()

    def remove_ingredient(self):
        product = self.product_combo.currentText()
        selected = self.list_widget.currentItem()
        if selected:
            value = selected.text()
            self.ingredients[product] = [
                item for item in self.ingredients.get(product, []) if item != value
            ]
            self.refresh_list()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_files()
        self.language = "English"
        self.setWindowTitle(self.t("Soap & Lip Gloss Label Maker"))
        self.resize(1180, 780)

        self.ingredients_library = load_json(INGREDIENTS_FILE, DEFAULT_INGREDIENTS.copy())
        for product, items in DEFAULT_INGREDIENTS.items():
            self.ingredients_library.setdefault(product, items.copy())
        self.recipes = load_json(RECIPES_FILE, [])

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        intro = QLabel(
            "Create a label, save its recipe, and generate a one-page US Letter PDF with a full sheet of labels."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        top = QHBoxLayout()
        top.addWidget(QLabel("Product type:"))
        self.product_combo = QComboBox()
        self.product_combo.addItems(list(PRODUCTS.keys()))
        top.addWidget(self.product_combo)
        top.addStretch(1)
        self.language_label = QLabel("Language:")
        top.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Español"])
        top.addWidget(self.language_combo)
        self.size_label = QLabel()
        top.addWidget(self.size_label)
        root.addLayout(top)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Product name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Lavender Oatmeal")
        name_row.addWidget(self.name_edit, 1)
        root.addLayout(name_row)

        quantity_row = QHBoxLayout()
        self.quantity_label = QLabel()
        quantity_row.addWidget(self.quantity_label)
        self.quantity_edit = QLineEdit()
        self.quantity_edit.setPlaceholderText("Enter amount, e.g. 4 or 5.5")
        quantity_row.addWidget(self.quantity_edit, 1)
        root.addLayout(quantity_row)

        logo_group = QGroupBox("Company logo — shared by Soap and Lip Gloss")
        logo_layout = QHBoxLayout(logo_group)
        self.logo_preview = QLabel("No logo selected")
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setMinimumSize(150, 70)
        self.logo_preview.setMaximumSize(190, 90)
        self.logo_preview.setStyleSheet("border: 1px solid #bbb; background: white; color: #555;")
        logo_layout.addWidget(self.logo_preview)
        logo_buttons = QVBoxLayout()
        self.choose_logo_btn = QPushButton("Choose logo…")
        self.remove_logo_btn = QPushButton("Remove logo")
        self.logo_path_label = QLabel("The same logo is used for both products.")
        self.logo_path_label.setWordWrap(True)
        logo_buttons.addWidget(self.choose_logo_btn)
        logo_buttons.addWidget(self.remove_logo_btn)
        logo_buttons.addWidget(self.logo_path_label)
        logo_buttons.addStretch(1)
        logo_layout.addLayout(logo_buttons, 1)
        root.addWidget(logo_group)

        body = QHBoxLayout()
        ingredients_group = QGroupBox("Ingredients — check all used in this product")
        ingredients_layout = QVBoxLayout(ingredients_group)
        self.ingredient_search = QLineEdit()
        self.ingredient_search.setPlaceholderText("Search ingredients…")
        self.ingredient_search.setClearButtonEnabled(True)
        ingredients_layout.addWidget(self.ingredient_search)
        self.ingredient_scroll = QScrollArea()
        self.ingredient_scroll.setWidgetResizable(True)
        self.ingredient_panel = QWidget()
        self.ingredient_grid = QGridLayout(self.ingredient_panel)
        self.ingredient_scroll.setWidget(self.ingredient_panel)
        ingredients_layout.addWidget(self.ingredient_scroll, 3)

        ingredients_layout.addWidget(QLabel("Selected ingredients — print order (use arrows to reorder):"))
        self.selected_ingredient_list = QListWidget()
        self.selected_ingredient_list.setMaximumHeight(120)
        ingredients_layout.addWidget(self.selected_ingredient_list, 1)
        order_buttons = QHBoxLayout()
        self.move_ingredient_up_btn = QPushButton("Move up")
        self.move_ingredient_down_btn = QPushButton("Move down")
        order_buttons.addWidget(self.move_ingredient_up_btn)
        order_buttons.addWidget(self.move_ingredient_down_btn)
        ingredients_layout.addLayout(order_buttons)

        ingredient_buttons = QHBoxLayout()
        manage_btn = QPushButton("Manage ingredient library")
        ingredient_buttons.addWidget(manage_btn)
        ingredients_layout.addLayout(ingredient_buttons)
        body.addWidget(ingredients_group, 3)

        saved_group = QGroupBox("Saved labels")
        saved_layout = QVBoxLayout(saved_group)
        self.saved_tabs = QTabWidget()
        self.saved_lists = {}
        self.saved_searches = {}
        for product_type in PRODUCTS:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            search = QLineEdit()
            search.setPlaceholderText(f"Search {product_type.lower()} labels…")
            search.setClearButtonEnabled(True)
            label_list = QListWidget()
            tab_layout.addWidget(search)
            tab_layout.addWidget(label_list, 1)
            self.saved_tabs.addTab(tab, f"{product_type} Labels")
            self.saved_lists[product_type] = label_list
            self.saved_searches[product_type] = search
            search.textChanged.connect(lambda _text: self.refresh_saved_list())
            label_list.itemDoubleClicked.connect(lambda _item: self.load_selected_recipe())
        saved_layout.addWidget(self.saved_tabs, 1)
        save_btn = QPushButton("Save current label")
        load_btn = QPushButton("Load selected")
        delete_btn = QPushButton("Delete selected")
        saved_layout.addWidget(save_btn)
        saved_layout.addWidget(load_btn)
        saved_layout.addWidget(delete_btn)
        body.addWidget(saved_group, 2)

        preview_group = QGroupBox("Live label preview")
        preview_layout = QVBoxLayout(preview_group)
        self.label_preview = LabelPreview()
        preview_layout.addWidget(self.label_preview, 1)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(140)
        self._preview_timer.timeout.connect(self._render_label_preview_now)
        self._preview_cache_key = None
        preview_note = QLabel("Preview updates as you edit the name, ingredients, quantity, or logo.")
        preview_note.setWordWrap(True)
        preview_note.setStyleSheet("color: #555;")
        preview_layout.addWidget(preview_note)
        self.overflow_warning = QLabel()
        self.overflow_warning.setWordWrap(True)
        self.overflow_warning.setStyleSheet("color: #a33; font-weight: 600;")
        preview_layout.addWidget(self.overflow_warning)
        body.addWidget(preview_group, 2)
        root.addLayout(body, 1)

        print_group = QGroupBox("Print and export")
        print_layout = QHBoxLayout(print_group)
        print_layout.addWidget(QLabel("One full sheet per PDF: 9 soap labels or 21 lip gloss labels."), 1)
        self.direct_print_btn = QPushButton("Print Labels")
        self.save_pdf_btn = QPushButton("Save as PDF")
        print_layout.addWidget(self.direct_print_btn)
        print_layout.addWidget(self.save_pdf_btn)
        root.addWidget(print_group)

        note = QLabel(
            "Print at Actual Size / 100% (turn off Fit to Page). "
            "Solid black border = label edge; no dashed cut lines are printed."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #555;")
        root.addWidget(note)

        self.checkboxes = {}
        self._capture_original_ui_texts()
        self.language_combo.currentTextChanged.connect(self.set_language)
        self.product_combo.currentTextChanged.connect(self.on_product_changed)
        manage_btn.clicked.connect(self.manage_ingredients)
        save_btn.clicked.connect(self.save_current_recipe)
        load_btn.clicked.connect(self.load_selected_recipe)
        delete_btn.clicked.connect(self.delete_selected_recipe)
        self.direct_print_btn.clicked.connect(self.print_labels)
        self.save_pdf_btn.clicked.connect(self.create_pdf)
        self.choose_logo_btn.clicked.connect(self.choose_logo)
        self.remove_logo_btn.clicked.connect(self.remove_logo)
        self.ingredient_search.textChanged.connect(self.filter_ingredient_checkboxes)
        self.move_ingredient_up_btn.clicked.connect(lambda: self.move_selected_ingredient(-1))
        self.move_ingredient_down_btn.clicked.connect(lambda: self.move_selected_ingredient(1))
        self.name_edit.textChanged.connect(self.update_label_preview)
        self.quantity_edit.textChanged.connect(self.update_label_preview)

        self.logo_path = self.load_saved_logo_path()
        self.update_logo_preview()
        self.refresh_saved_list()
        self.rebuild_ingredient_checkboxes()
        self.update_size_label()
        self.update_label_preview()

    def _capture_original_ui_texts(self):
        """Remember original UI strings so switching languages is reversible."""
        for widget in self.findChildren(QWidget):
            if isinstance(widget, QLabel):
                widget.setProperty("_label_maker_en_text", widget.text())
            elif isinstance(widget, QGroupBox):
                widget.setProperty("_label_maker_en_text", widget.title())
            elif isinstance(widget, QPushButton):
                widget.setProperty("_label_maker_en_text", widget.text())
            elif isinstance(widget, QLineEdit):
                widget.setProperty("_label_maker_en_placeholder", widget.placeholderText())
        self._original_tab_texts = [self.saved_tabs.tabText(i) for i in range(self.saved_tabs.count())]

    def t(self, text):
        return translated(text, self.language)

    def set_language(self, language):
        self.language = language
        self.setWindowTitle(self.t("Soap & Lip Gloss Label Maker"))
        for widget in self.findChildren(QWidget):
            original = widget.property("_label_maker_en_text")
            if original is not None:
                value = translated(str(original), language)
                if isinstance(widget, QLabel):
                    widget.setText(value)
                elif isinstance(widget, QGroupBox):
                    widget.setTitle(value)
                elif isinstance(widget, QPushButton):
                    widget.setText(value)
            placeholder = widget.property("_label_maker_en_placeholder")
            if placeholder is not None and isinstance(widget, QLineEdit):
                widget.setPlaceholderText(translated(str(placeholder), language))
        self.language_label.setText("Idioma:" if language == "Español" else "Language:")
        self.product_combo.setItemText(0, "Jabón" if language == "Español" else "Soap")
        self.product_combo.setItemText(1, "Brillo labial" if language == "Español" else "Lip Gloss")
        for i, original in enumerate(self._original_tab_texts):
            self.saved_tabs.setTabText(i, translated(original, language))
        self.update_size_label()
        self.update_logo_preview()
        self._render_label_preview_now()

    def load_saved_logo_path(self):
        settings = load_json(LOGO_SETTINGS_FILE, {})
        filename = settings.get("filename", "") if isinstance(settings, dict) else ""
        if filename:
            candidate = APP_DIR / Path(filename).name
            if candidate.is_file():
                return candidate
        return None

    def update_logo_preview(self):
        if not self.logo_path or not self.logo_path.is_file():
            self.logo_preview.setPixmap(QPixmap())
            self.logo_preview.setText(self.t("No logo selected"))
            self.logo_path_label.setText(self.t("The same logo is used for both products."))
            self.remove_logo_btn.setEnabled(False)
            if hasattr(self, "label_preview"):
                self.update_label_preview()
            return
        pixmap = QPixmap(str(self.logo_path))
        if pixmap.isNull():
            self.logo_preview.setPixmap(QPixmap())
            self.logo_preview.setText(self.t("Preview unavailable"))
        else:
            self.logo_preview.setText("")
            self.logo_preview.setPixmap(
                pixmap.scaled(
                    self.logo_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.logo_path_label.setText(f"{self.t('Selected: ')}{self.logo_path.name}")
        self.remove_logo_btn.setEnabled(True)
        if hasattr(self, "label_preview"):
            self.update_label_preview()

    def choose_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose company logo",
            str(Path.home()),
            "Image files (*.png *.jpg *.jpeg);;PNG files (*.png);;JPEG files (*.jpg *.jpeg)",
        )
        if not file_path:
            return
        source = Path(file_path)
        pixmap = QPixmap(str(source))
        if pixmap.isNull():
            QMessageBox.warning(
                self, "Unsupported image", "Choose a valid PNG or JPG/JPEG image file."
            )
            return
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            extension = source.suffix.lower()
            if extension not in {".png", ".jpg", ".jpeg"}:
                QMessageBox.warning(
                    self, "Unsupported image", "Only PNG and JPG/JPEG logo files are supported."
                )
                return
            destination = APP_DIR / f"company_logo{extension}"
            # Copy to a temporary file first so choosing a logo already stored in
            # the app folder is safe, even when changing its extension.
            same_file = source.resolve() == destination.resolve()
            temporary = APP_DIR / f".company_logo_tmp{extension}"
            if not same_file:
                shutil.copy2(source, temporary)
            # Remove older logo variants so the selected file is the single active logo.
            for old_extension in (".png", ".jpg", ".jpeg"):
                old_file = APP_DIR / f"company_logo{old_extension}"
                if old_file.exists() and old_file != destination:
                    old_file.unlink()
            if not same_file:
                temporary.replace(destination)
            save_json(LOGO_SETTINGS_FILE, {"filename": destination.name})
            self.logo_path = destination
            self.update_logo_preview()
        except OSError as exc:
            QMessageBox.critical(self, "Could not save logo", str(exc))

    def remove_logo(self):
        if not self.logo_path:
            return
        try:
            for extension in (".png", ".jpg", ".jpeg"):
                logo_file = APP_DIR / f"company_logo{extension}"
                if logo_file.exists():
                    logo_file.unlink()
            save_json(LOGO_SETTINGS_FILE, {"filename": ""})
            self.logo_path = None
            self.update_logo_preview()
        except OSError as exc:
            QMessageBox.critical(self, "Could not remove logo", str(exc))

    def update_label_preview(self, *_args):
        """Debounce rapid edits so we only render after the user pauses briefly."""
        if not hasattr(self, "label_preview"):
            return
        self._preview_timer.start()

    def _render_label_preview_now(self):
        if not hasattr(self, "label_preview"):
            return
        product_type = self.current_product()
        name = self.name_edit.text()
        ingredients = self.selected_ingredients()
        quantity = self.quantity_edit.text()
        warnings = label_fit_warnings(product_type, name, ingredients, self.logo_path)
        if warnings:
            if self.language == "Español":
                translated_warnings = []
                for warning in warnings:
                    warning = warning.replace("Ingredients exceed the Lip Gloss label by about", "Los ingredientes exceden la etiqueta de brillo labial por aproximadamente")
                    warning = warning.replace("Ingredients exceed the Soap label by about", "Los ingredientes exceden la etiqueta de jabón por aproximadamente")
                    warning = warning.replace("line(s). Remove ingredients or shorten the product name.", "línea(s). Quita ingredientes o acorta el nombre del producto.")
                    warning = warning.replace("The product name is too long to leave enough room for the ingredients. Shorten the name.", "El nombre del producto es demasiado largo y no deja espacio suficiente para los ingredientes. Acorta el nombre.")
                    translated_warnings.append(warning)
                self.overflow_warning.setText("⚠ " + "\n⚠ ".join(translated_warnings))
            else:
                self.overflow_warning.setText("⚠ " + "\n⚠ ".join(warnings))
        else:
            self.overflow_warning.setText(self.t("Content fits the label layout."))
        self.overflow_warning.setStyleSheet(
            "color: #a33; font-weight: 600;" if warnings else "color: #28723b;"
        )
        logo_path = self.logo_path
        logo_stamp = None
        if logo_path and Path(logo_path).is_file():
            try:
                stat = Path(logo_path).stat()
                logo_stamp = (str(logo_path), stat.st_mtime_ns, stat.st_size)
            except OSError:
                logo_stamp = str(logo_path)
        cache_key = (product_type, name, tuple(ingredients), quantity, logo_stamp)
        if cache_key == self._preview_cache_key:
            return
        try:
            image = render_label_preview(
                product_type, name, ingredients, quantity, logo_path,
            )
            self.label_preview.set_preview_image(image)
            self._preview_cache_key = cache_key
        except Exception as exc:
            self.label_preview.setText(f"Preview unavailable\n{exc}")

    def current_product(self):
        # Keep internal product keys stable while the visible combo is translated.
        return "Soap" if self.product_combo.currentIndex() == 0 else "Lip Gloss"

    def selected_ingredients(self):
        """Return checked ingredients in the explicit print order shown in the list."""
        ordered = [self.selected_ingredient_list.item(i).text()
                   for i in range(self.selected_ingredient_list.count())]
        # Keep any checked items that were not yet reflected in the order list.
        for name, checkbox in self.checkboxes.items():
            if checkbox.isChecked() and name not in ordered:
                ordered.append(name)
        return ordered

    def on_ingredient_toggled(self, ingredient, state):
        checked = state == Qt.CheckState.Checked.value
        matches = self.selected_ingredient_list.findItems(
            ingredient, Qt.MatchFlag.MatchExactly
        )
        if checked and not matches:
            self.selected_ingredient_list.addItem(ingredient)
        elif not checked:
            for item in matches:
                row = self.selected_ingredient_list.row(item)
                self.selected_ingredient_list.takeItem(row)
        self.update_label_preview()

    def move_selected_ingredient(self, offset):
        row = self.selected_ingredient_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= self.selected_ingredient_list.count():
            return
        item = self.selected_ingredient_list.takeItem(row)
        self.selected_ingredient_list.insertItem(target, item)
        self.selected_ingredient_list.setCurrentRow(target)
        self.update_label_preview()

    def on_product_changed(self):
        self.rebuild_ingredient_checkboxes()
        self.update_size_label()
        self.update_label_preview()

    def update_size_label(self):
        d = PRODUCTS[self.current_product()]
        product = self.current_product()
        self.size_label.setText(f'{d["width"]} × {d["height"]} {"pulgadas" if self.language == "Español" else "inches"}')
        if product == "Soap":
            self.quantity_label.setText(self.t("Approximate soap weight (oz):"))
            self.quantity_edit.setPlaceholderText(self.t("e.g. 4 or 4.5"))
        else:
            self.quantity_label.setText(self.t("Net contents (mL):"))
            self.quantity_edit.setPlaceholderText(self.t("e.g. 5 or 10"))

    def rebuild_ingredient_checkboxes(self, checked=None):
        checked_order = list(dict.fromkeys(checked or []))
        checked = set(checked_order)
        while self.ingredient_grid.count():
            item = self.ingredient_grid.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.checkboxes = {}
        if hasattr(self, "selected_ingredient_list"):
            self.selected_ingredient_list.clear()
        product = self.current_product()
        values = self.ingredients_library.get(product, [])
        for ingredient in values:
            checkbox = QCheckBox(ingredient)
            checkbox.setChecked(ingredient in checked)
            self.checkboxes[ingredient] = checkbox
            checkbox.stateChanged.connect(
                lambda state, name=ingredient: self.on_ingredient_toggled(name, state)
            )
        # Preserve the incoming recipe order, rather than sorting by the library.
        for ingredient in checked_order:
            if ingredient in self.checkboxes and self.checkboxes[ingredient].isChecked():
                self.selected_ingredient_list.addItem(ingredient)
        self.filter_ingredient_checkboxes()
        self.update_label_preview()

    def filter_ingredient_checkboxes(self, *_args):
        """Show matching ingredient checkboxes in a compact two-column grid."""
        while self.ingredient_grid.count():
            self.ingredient_grid.takeAt(0)
        query = self.ingredient_search.text().strip().casefold()
        visible = []
        for name, checkbox in self.checkboxes.items():
            matches = query in name.casefold()
            checkbox.setVisible(matches)
            if matches:
                visible.append(checkbox)
        for index, checkbox in enumerate(visible):
            self.ingredient_grid.addWidget(checkbox, index // 2, index % 2)
        self.ingredient_grid.setRowStretch(math.ceil(len(visible) / 2), 1)

    def recipe_data(self):
        return {
            "product_type": self.current_product(),
            "name": self.name_edit.text().strip(),
            "ingredients": self.selected_ingredients(),
            "quantity": self.quantity_edit.text().strip(),
        }

    def current_saved_list(self):
        index = self.saved_tabs.currentIndex()
        product_type = list(PRODUCTS.keys())[index] if 0 <= index < len(PRODUCTS) else "Soap"
        return self.saved_lists.get(product_type)

    def refresh_saved_list(self, selected_name=None, selected_type=None):
        """Refresh each product's saved-label tab while preserving its search."""
        for product_type, label_list in self.saved_lists.items():
            label_list.clear()
            query = self.saved_searches[product_type].text().strip().casefold()
            for recipe in self.recipes:
                recipe_type = recipe.get("product_type", "Soap")
                if recipe_type != product_type:
                    continue
                searchable = " ".join([
                    str(recipe.get("name", "")),
                    str(recipe.get("quantity", "")),
                    " ".join(str(v) for v in recipe.get("ingredients", [])),
                ]).casefold()
                if query and query not in searchable:
                    continue
                label = recipe.get("name", "(unnamed)") or "(unnamed)"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, recipe)
                label_list.addItem(item)
                if (selected_name and recipe.get("name") == selected_name
                        and (selected_type is None or recipe_type == selected_type)):
                    label_list.setCurrentItem(item)
        if selected_type in self.saved_lists:
            self.saved_tabs.setCurrentWidget(self.saved_lists[selected_type].parentWidget())

    def save_current_recipe(self):
        recipe = self.recipe_data()
        if not recipe["name"]:
            QMessageBox.warning(self, self.t("Product name required"), self.t("Enter a product name before saving."))
            return
        # Replace an existing saved recipe with the same product type and name.
        self.recipes = [
            r for r in self.recipes
            if not (r.get("product_type") == recipe["product_type"]
                    and r.get("name", "").casefold() == recipe["name"].casefold())
        ]
        self.recipes.append(recipe)
        save_json(RECIPES_FILE, self.recipes)
        # Ensure the newly saved label is visible even if that tab had a search active.
        self.saved_searches[recipe["product_type"]].clear()
        self.refresh_saved_list(recipe["name"], recipe["product_type"])
        QMessageBox.information(self, self.t("Saved"), self.t("The label recipe has been saved."))

    def load_selected_recipe(self):
        active_list = self.current_saved_list()
        item = active_list.currentItem() if active_list else None
        if not item:
            QMessageBox.information(self, self.t("Select a label"), self.t("Choose a saved label first."))
            return
        recipe = item.data(Qt.ItemDataRole.UserRole)
        self.product_combo.setCurrentIndex(0 if recipe.get("product_type", "Soap") == "Soap" else 1)
        self.name_edit.setText(recipe.get("name", ""))
        self.quantity_edit.setText(recipe.get("quantity", ""))
        self.rebuild_ingredient_checkboxes(recipe.get("ingredients", []))

    def delete_selected_recipe(self):
        active_list = self.current_saved_list()
        item = active_list.currentItem() if active_list else None
        if not item:
            return
        recipe = item.data(Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(
            self, self.t("Delete saved label"),
            f'Delete "{recipe.get("name", "this label")}"?'
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.recipes = [r for r in self.recipes if r != recipe]
            save_json(RECIPES_FILE, self.recipes)
            self.refresh_saved_list()

    def manage_ingredients(self):
        dialog = IngredientManager(self.ingredients_library, self)
        if self.language == "Español":
            dialog.setWindowTitle("Administrar ingredientes")
            dialog.product_combo.setItemText(0, "Jabón")
            dialog.product_combo.setItemText(1, "Brillo labial")
            for widget in dialog.findChildren(QWidget):
                if isinstance(widget, QLabel) and widget.text() == "Ingredient list for:":
                    widget.setText("Lista de ingredientes para:")
                elif isinstance(widget, QLineEdit):
                    widget.setPlaceholderText("Nombre del ingrediente nuevo")
                elif isinstance(widget, QPushButton):
                    if widget.text() == "Add": widget.setText("Añadir")
                    elif widget.text() == "Remove selected": widget.setText("Eliminar seleccionado")
                    elif widget.text() == "Save": widget.setText("Guardar")
                    elif widget.text() == "Cancel": widget.setText("Cancelar")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_json(INGREDIENTS_FILE, self.ingredients_library)
            # Keep currently selected ingredients when possible.
            selected = self.selected_ingredients()
            self.rebuild_ingredient_checkboxes(selected)

    def print_labels(self):
        """Show a real print preview and print the current one-page label sheet.

        Rendering the PDF against the printer's full paper rectangle preserves
        the US Letter page geometry. QPrintPreviewDialog also avoids the native
        print-dialog preview action that previously reported that this app did
        not support print preview.
        """
        recipe = self.recipe_data()
        if not recipe["name"].strip():
            QMessageBox.warning(
                self, self.t("Product name required"),
                self.t("Enter a product name before saving.")
            )
            return

        temp_path = None
        document = None
        try:
            with tempfile.NamedTemporaryFile(prefix="label_maker_", suffix=".pdf", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            product_type = recipe["product_type"]
            product_count = 9 if product_type == "Soap" else 21
            generate_pdf(
                temp_path, product_type, recipe["name"], recipe["ingredients"],
                product_count,
                logo_path=str(self.logo_path) if self.logo_path else None,
                quantity=recipe.get("quantity", ""),
            )

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)
            printer.setFullPage(True)
            if not printer.isValid():
                raise RuntimeError(self.t("No valid printer is available. Check that a printer is installed and ready."))

            document = QPdfDocument(self)
            # QPdfDocument.load() returns a QPdfDocument.Error value, not a
            # QPdfDocument.Status value. Check the document's status separately;
            # comparing the load() return value to Status.Ready rejects valid PDFs.
            load_error = document.load(str(temp_path))
            if (document.status() != QPdfDocument.Status.Ready
                    or document.pageCount() < 1):
                raise RuntimeError(
                    f"{self.t('The PDF could not be loaded for printing.')} "
                    f"(load error: {load_error}; document status: {document.status()}; "
                    f"PDF pages: {document.pageCount()})"
                )

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle(self.t("Print labels — preview"))
            render_error = {"message": None}

            def paint_page(target_printer):
                """Paint the PDF page at the full physical paper size."""
                painter = QPainter()
                try:
                    # PDF page coordinates include the entire sheet, not just
                    # the printer's printable area. Use paperRect to avoid
                    # unintentionally shrinking/shifting the label grid.
                    paper_rect = target_printer.paperRect(QPrinter.Unit.DevicePixel)
                    render_size = QSize(
                        max(1, round(paper_rect.width())),
                        max(1, round(paper_rect.height())),
                    )
                    page_image = document.render(0, render_size)
                    if page_image.isNull():
                        raise RuntimeError(self.t("The PDF could not be loaded for printing."))
                    if not painter.begin(target_printer):
                        raise RuntimeError(self.t("Could not start the print job. Check the selected printer and try again."))
                    painter.drawImage(paper_rect, page_image)
                except Exception as exc:
                    render_error["message"] = str(exc)
                finally:
                    if painter.isActive():
                        painter.end()

            preview.paintRequested.connect(paint_page)
            result = preview.exec()

            if render_error["message"]:
                raise RuntimeError(render_error["message"])
            if result == QDialog.DialogCode.Accepted:
                QMessageBox.information(
                    self, self.t("Printing started"),
                    f"{self.t('The print preview was accepted. Check the printer queue to confirm the job is progressing.')}\n\n"
                    f"{self.t('Labels on this page:')} {product_count}.\n"
                    f"{self.t('For correct label dimensions, use US Letter paper and Actual Size / 100% scaling where available.')}"
                )
        except Exception as exc:
            QMessageBox.critical(self, self.t("Could not print labels"), str(exc))
        finally:
            if document is not None:
                document.close()
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def create_pdf(self):
        recipe = self.recipe_data()
        if not recipe["name"]:
            QMessageBox.warning(self, self.t("Product name required"), self.t("Enter a product name before saving."))
            return
        suggested = OUTPUT_DIR / f'{recipe["product_type"].replace(" ", "_")}_{safe_filename(recipe["name"])}.pdf'
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.t("Save print-ready PDF"), str(suggested), self.t("PDF files (*.pdf)")
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"
        try:
            cols, rows, per_page = generate_pdf(
                file_path,
                recipe["product_type"],
                recipe["name"],
                recipe["ingredients"],
                9 if recipe["product_type"] == "Soap" else 21,
                logo_path=str(self.logo_path) if self.logo_path else None,
                quantity=recipe.get("quantity", ""),
            )
        except Exception as exc:
            QMessageBox.critical(self, self.t("Could not create PDF"), str(exc))
            return
        QMessageBox.information(
            self, self.t("PDF created"),
            f"{self.t('PDF saved successfully.')}\n\n"
            f"{self.t('Labels on this page:')} {per_page} ({cols} {('de ancho' if self.language == 'Español' else 'across')} × {rows} {('de alto' if self.language == 'Español' else 'down')}).\n\n"
            f"{self.t('Open the PDF and print using Actual Size / 100%.')}"
        )


def safe_filename(value):
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    return cleaned.strip("_") or "label"


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
