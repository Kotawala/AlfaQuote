import streamlit as st
import sys
import io
from datetime import datetime

# --- ReportLab Imports for advanced styling ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

from num2words import num2words

# Compatibility patch for hashlib on older Python versions
if sys.version_info < (3, 9):
    import hashlib
    original_md5 = hashlib.md5
    def patched_md5(*args, **kwargs):
        kwargs.pop('usedforsecurity', None)
        return original_md5(*args, **kwargs)
    hashlib.md5 = patched_md5

st.title("🏥 Alfaleus Doctor Quotation Generator")

# Define PDF page dimensions and margins
WIDTH, HEIGHT = A4
BORDER_MARGIN = 20

# --- Form Inputs ---
customer_name = st.text_input("Customer Name (e.g., Kauvery Eye Hospital)")

# Change 7: Customer Address now uses a text area and will be rendered correctly with line breaks.
address = st.text_area("Customer Address")
gstin = st.text_input("Customer GSTIN (or 'Nil')")

# Change 4: Default text for Product Description
default_description = (
    "Intelligent Vision Analyser Plus (iVA+)\n"
    "4th Generation - VR based visual field testing device - complete kit "
    "with 1 year CMC warranty, including 1 unit Lens kit, 1 unit Lens holder (custom build)"
)
product_description = st.text_area(
    "Product Description / Details",
    value=default_description,
    height=150
)

unit = st.text_input("Unit (e.g., 1 Nos)", value="1 Nos")

# Change 6: Added a dynamic payment terms field
default_payment_terms = "Rs. 11,000 booking amount and balance payment upon installation."
payment_terms = st.text_area("Payment Terms", value=default_payment_terms)


# Change 5: Rate is now inclusive of GST. Label and variable names updated.
# Change 8: Currency symbol updated from ₹ to Rs.
RATE_MIN = 300000.00
RATE_MAX = 480000.00
total_inclusive_gst = st.number_input(
    "Total Amount (Inclusive of GST) (Rs.) - Must be between 3,00,000 and 4,80,000",
    min_value=RATE_MIN,
    max_value=RATE_MAX,
    step=1000.00,
    value=RATE_MIN,
    format="%.2f"
)

gst_percent = st.number_input("GST (%)", min_value=0.0, step=0.01, value=5.0)


if st.button("Generate Alfaleus Quotation PDF"):
    # Input validation
    if not (RATE_MIN <= total_inclusive_gst <= RATE_MAX):
        st.error(f"The entered rate must be between Rs.{RATE_MIN:,.2f} and Rs.{RATE_MAX:,.2f}.")
        st.stop()
        
    # ---- Calculations (based on inclusive GST) ----
    # Change 5: Logic reversed to calculate base rate from the total.
    rate_exclusive_gst = total_inclusive_gst / (1 + gst_percent / 100)
    gst_amount = total_inclusive_gst - rate_exclusive_gst
    
    quote_no = f"ALF/{datetime.now().year % 100}-{(datetime.now().year + 1) % 100}/{int(datetime.now().timestamp()) % 1000:03d}"
    date_str = datetime.now().strftime("%d/%m/%Y")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # --- Helper for drawing wrapped text (Paragraphs) ---
    styles = getSampleStyleSheet()
    # Style for address and description
    para_style = ParagraphStyle(
        'Normal_Left',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_LEFT
    )

    # 1 - include a border for overall generated quotation
    c.rect(BORDER_MARGIN, BORDER_MARGIN, WIDTH - 2 * BORDER_MARGIN, HEIGHT - 2 * BORDER_MARGIN)

    # ---- Header ----
    # Change 1: Header color set to #255290
    c.setFillColor(HexColor('#255290'))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(WIDTH / 2, HEIGHT - 40, "ALFALEUS TECHNOLOGY PRIVATE LIMITED")
    c.setFillColorRGB(0, 0, 0) # Reset color to black

    c.setFont("Helvetica", 9)
    c.drawCentredString(WIDTH / 2, HEIGHT - 55,
        "Registered Office : II Floor, 654, Vivek Vihar, New Sanganare Road, Jaipur, Rajasthan - 302019")
    c.drawCentredString(WIDTH / 2, HEIGHT - 68,
        "CIN : U74999RJ2018PTC060255 | Mail : info@alfaleus.com | Contact : +91 96550 42547")

    # ---- Quotation Title ----
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(WIDTH / 2, HEIGHT - 100, "Sales Quotation")

    # ---- Supplier Info ----
    y = HEIGHT - 130
    
    # Change 1: "Name of Supplier:" is bold, value is normal, no extra space
    bold_text = "Name of Supplier: "
    normal_text = "Alfaleus Technology Private Limited"
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, bold_text)
    text_width = c.stringWidth(bold_text, "Helvetica-Bold", 10)
    c.setFont("Helvetica", 10)
    c.drawString(50 + text_width, y, normal_text)

    y -= 15
    # MODIFICATION 1: Make "Quotation No" bold
    bold_quote = "Quotation No: "
    normal_quote_no = quote_no
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, bold_quote)
    quote_width = c.stringWidth(bold_quote, "Helvetica-Bold", 10)
    c.setFont("Helvetica", 10)
    c.drawString(50 + quote_width, y, normal_quote_no)
    
    # Change 2: Date is right-aligned
    c.drawRightString(WIDTH - 50, y, f"Date: {date_str}")
    
    # Change 3: Added one line space after date/quote line
    y -= 30 
    
    c.drawString(50, y, "Head Office: E1, Technology Research Park, IIT Hyderabad, Kandi - 502285")
    y -= 15
    c.drawString(50, y, "GSTIN : 36AAQCA5270P1ZY")
    y -= 15
    c.drawString(50, y, "E-mail: sales@alfaleus.com")
    y -= 15
    c.drawString(50, y, "Phone: +91 96550 42547")

    # ---- Customer Details ----
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Customer Details")
    y -= 15
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Name : {customer_name}")
    y -= 15
    
    # Change 7: Draw address using Paragraph to handle multiple lines
    address_text = address.replace('\n', '<br/>')
    address_para = Paragraph(f"Address : {address_text}", para_style)
    w_addr, h_addr = address_para.wrapOn(c, WIDTH - 100, HEIGHT) # Get required height
    address_para.drawOn(c, 50, y - h_addr)
    y -= (h_addr + 15) # Move y-cursor down by the height of the address block
    
    c.drawString(50, y, f"GSTIN : {gstin}")

    # ---- Product Details Table ----
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Product Details")
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "S No.")
    c.drawString(90, y, "Product Description")
    c.drawString(350, y, "Unit")
    c.drawString(420, y, "Amount (Rs.)") # Change 8
    c.drawString(510, y, "Total (Rs.)")  # Change 8
    y -= 10
    c.line(50, y, 550, y)
    y -= 15

    c.setFont("Helvetica", 10)
    c.drawString(55, y, "1")
    
    # Change 4: Draw product description using Paragraph to handle wrapping and newlines
    desc_text = product_description.replace('\n', '<br/>')
    desc_para = Paragraph(desc_text, para_style)
    w_desc, h_desc = desc_para.wrapOn(c, 250, HEIGHT) # Wrap in a 250-point width column
    
    # y-position for drawing the paragraph needs to be adjusted since drawOn uses bottom-left corner
    y_start_desc = y - (h_desc - 10) 
    desc_para.drawOn(c, 90, y_start_desc)
    
    # Align other cells with the top of the description
    c.drawString(350, y, unit)

    # Use the calculated pre-GST rate here
    c.drawRightString(480, y, f"{rate_exclusive_gst:,.2f}") 
    c.drawRightString(550, y, f"{rate_exclusive_gst:,.2f}")

    # Set y to below the tallest element in the row (the description)
    y = y_start_desc - 15

    # ---- Total Calculations Section ----
    c.setFont("Helvetica", 10)
    c.drawString(300, y, "Sub Total:")
    c.drawRightString(550, y, f"{rate_exclusive_gst:,.2f}")
    
    y -= 20
    c.drawString(300, y, f"Add GST ({gst_percent:.2f}%):")
    c.drawRightString(550, y, f"{gst_amount:,.2f}")

    y -= 10
    c.line(300, y, 550, y)

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, y, "Grand Total:")
    # Change 8
    c.drawRightString(550, y, f"Rs. {total_inclusive_gst:,.2f}")
    
    # ---- Amount in Words ----
    y -= 30
    words = num2words(round(total_inclusive_gst), lang='en_IN').title()
    # MODIFICATION 2: Make "Value in words" bold
    bold_value = "Value in words"
    normal_text_words = f": Rupees {words} Only."
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, bold_value)
    words_width = c.stringWidth(bold_value, "Helvetica-Bold", 10)
    c.setFont("Helvetica", 10)
    c.drawString(50 + words_width, y, normal_text_words)

    # ---- Declaration ----
    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Declaration:")
    y -= 15
    c.setFont("Helvetica", 10)
    # MODIFICATION 3: Change Declaration text
    c.drawString(50, y, "On behalf of M/s Alfaleus Technology Private Limited generated by Mr. Kiran Shukla")
    y -= 15
    c.drawString(50, y, "- The particulars given above are true and correct.")

    # ---- Terms & Conditions ----
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Terms & Conditions -")
    y -= 15
    c.setFont("Helvetica", 10)
    
    # Change 6: Use dynamic payment terms
    terms = [
        f"1 - Payment terms: {payment_terms}",
        "2 - Delivery terms: Dispatch within 30 working days from order placement."
    ]
    for t in terms:
        # Using a Paragraph for terms as well to handle potential wrapping
        term_para = Paragraph(t, para_style)
        w_term, h_term = term_para.wrapOn(c, WIDTH - 100, HEIGHT)
        term_para.drawOn(c, 50, y - h_term)
        y -= (h_term + 5)


    # ---- Signature ----
    y = BORDER_MARGIN + 80 # Position signature from the bottom for consistency
    c.drawString(50, y, "Kiran Shukla")
    c.drawString(50, y - 12, "Head of Sales")
    c.drawString(50, y - 24, "Alfaleus Technology Pvt. Ltd, TRP, IIT Hyderabad, Kandi - 502285")

    # ---- Footer ----
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, BORDER_MARGIN + 15,
        "This is a computer generated quotation and does not require physical signature. "
        "For any queries, contact info@alfaleus.com")

    # ---- Save and Download ----
    c.showPage()
    c.save()
    buffer.seek(0)

    st.download_button(
        label="📄 Download Quotation PDF",
        data=buffer,
        file_name=f"Alfaleus_Quotation_{customer_name.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )