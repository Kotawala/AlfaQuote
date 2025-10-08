import streamlit as st
import sys
import os
import io
from datetime import datetime
from uuid import uuid4 # Used for stable session state key
from dotenv import load_dotenv
load_dotenv()

# --- NEW IMPORTS for Email Automation ---
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import COMMASPACE 
# ----------------------------------------

# --- ReportLab Imports for advanced styling ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT

from num2words import num2words

# File path where the last serial number is stored
COUNTER_FILE = "last_receipt_num.txt"
INITIAL_COUNTER_VALUE = 99 # The number *before* the first desired receipt (0100)

# Function to read the last counter value from file
def read_last_counter():
    try:
        with open(COUNTER_FILE, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        # If file doesn't exist, use the initial value
        return INITIAL_COUNTER_VALUE
    except ValueError:
        # If file content is invalid, reset to initial value
        return INITIAL_COUNTER_VALUE

# Function to write the new counter value to file
def write_new_counter(new_value):
    try:
        with open(COUNTER_FILE, 'w') as f:
            f.write(str(new_value))
    except Exception as e:
        st.error(f"Error writing counter to file: {e}")

# Initialize the persistent counter in session state only once per application run
if 'receipt_counter_persistent' not in st.session_state:
    st.session_state['receipt_counter_persistent'] = read_last_counter()

# Function to get the next sequential receipt number
def get_next_receipt_number_persistent(date: datetime):
    # Only increment and update the global counter when the button is pressed (outside of this function)
    counter = st.session_state['receipt_counter_persistent'] + 1
    date_str = date.strftime("%d%m%y")
    return f"REC/{date_str}/{counter:04d}"


# Compatibility patch for hashlib on older Python versions
if sys.version_info < (3, 9):
    import hashlib
    original_md5 = hashlib.md5
    def patched_md5(*args, **kwargs):
        kwargs.pop('usedforsecurity', None)
        return original_md5(*args, **kwargs)
    hashlib.md5 = patched_md5


# --- SESSION STATE INITIALIZATION for Sequential Counter ---
if 'receipt_counter' not in st.session_state:
    # Starting counter at 100 as requested. This will be the first receipt number suffix.
    st.session_state['receipt_counter'] = 99 
    
# Function to get the next sequential receipt number
def get_next_receipt_number(date: datetime):
    # Only increment the counter once per generation session
    if 'current_receipt_num' not in st.session_state:
        st.session_state['receipt_counter'] += 1
        st.session_state['current_receipt_num'] = st.session_state['receipt_counter']
    
    counter = st.session_state['current_receipt_num']
    date_str = date.strftime("%d%m%y")
    return f"REC/{date_str}/{counter:04d}"

# --- EMAIL CONFIGURATION (MUST BE UPDATED) ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
INTERNAL_RECEIVER_EMAIL = os.getenv("INTERNAL_RECEIVER_EMAIL")

# --- PRIMARY CC MAPPING (Used for internal tracking) ---
PRIMARY_CC_MAPPING = {
    "Kiran Shukla": "kiran.alfaleus@gmail.com",
    "Sandal Kotawala": "info@alfaleus.com",
    "Abdul Baquee": "abdul.alfaleus@gmail.com",
    "Pius Varghese": "pius.alfaleus@gmail.com"
}
# --- SECONDARY CC LIST (Always included on customer emails) ---
SECONDARY_CC_EMAILS = ["sandal@alfaleus.com"]
# ---------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# ---------------------------------------------

# --- GENERATOR CONFIGURATION (Now the "Receiver" / Issuer) ---
GENERATOR_DETAILS = {
    "Kiran Shukla": "Head of Sales",
    "Abdul Baquee": "Sales Coordinator",
    "Pius Varghese": "Operations Manager",
    "Sandal Kotawala": "CEO"
}
# -----------------------------------

st.title("💰 Alfaleus Payment Receipt Generator")

# Define PDF page dimensions and margins
WIDTH, HEIGHT = A4
BORDER_MARGIN = 20

# --- MODIFIED Function to send the receipt PDF via email ---
def send_receipt_email(receipt_no, recipient_email, customer_name, pdf_buffer, generator_name, cc_emails=[], is_customer_send=False):
    """Sends the PDF receipt as an attachment to the specified email."""
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    
    recipients = [recipient_email]

    if is_customer_send:
        msg['Subject'] = f"Payment Receipt {receipt_no} from Alfaleus Tech Pvt Ltd"
        
        # --- ADD CC for Customer Send ---
        msg['Cc'] = COMMASPACE.join(cc_emails)
        recipients.extend(cc_emails)
        # --------------------------------
        
        generator_title = GENERATOR_DETAILS.get(generator_name, 'Sales Team')
        body = (
            f"Dear {customer_name},\n\n"
            f"Thank you for your payment. Please find attached the official Payment Receipt (No. {receipt_no}).\n\n"
            f"Best regards,\n"
            f"{generator_name}\n"
            f"{generator_title}, Alfaleus Technology Private Limited"
        )
        success_msg = f"📧 Receipt successfully sent to **{recipient_email}** (Customer) and CC'd to internal team: **{COMMASPACE.join(cc_emails)}**"
        error_prefix = "❌ Failed to send email to customer"
    else:
        # Internal copy
        msg['Subject'] = f"INTERNAL COPY: New Receipt Generated: {receipt_no} for {customer_name}"
        body = f"A new Payment Receipt (No. {receipt_no}) has been generated by {generator_name} for {customer_name}. The PDF copy is attached."
        success_msg = f"📧 Copy of receipt successfully sent to **{recipient_email}** (Internal)."
        error_prefix = "❌ Failed to send internal copy"

    msg.attach(MIMEText(body, 'plain'))

    pdf_attachment = MIMEApplication(pdf_buffer.getvalue(), _subtype="pdf")
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"{receipt_no}_{customer_name.replace(' ', '_')}_Receipt.pdf")
    msg.attach(pdf_attachment)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        
        st.success(success_msg)
        return True
    except smtplib.SMTPAuthenticationError:
        st.error(f"{error_prefix}: Email authentication failed. Check your SENDER_EMAIL/PASSWORD.")
        return False
    except Exception as e:
        st.error(f"{error_prefix}: {e}")
        return False

# --- UI Layout and Inputs ---

generator_name = st.selectbox(
    "Receipt Issued By (Generator):",
    options=list(GENERATOR_DETAILS.keys()),
    index=0
)
generator_title = GENERATOR_DETAILS[generator_name]

st.subheader("Customer Details")
customer_name = st.text_input("Customer Name (Payer)")
customer_email = st.text_input("Customer Email")
address = st.text_area("Customer Address")
gstin = st.text_input("Customer GSTIN (or 'Nil')")

st.subheader("Payment Details")

# --- Receipt Date Input ---
receipt_date = st.date_input("Receipt Date", value=datetime.today())

# --- Mode of Payment Selectbox ---
mode_of_payment = st.selectbox(
    "Mode of Payment",
    options=["Cash", "UPI", "Bank Transfer", "Cheque", "Demand Draft"]
)

# --- Payment Reference Details ---
reference_details = st.text_input(
    "Payment Reference Details (UTR No., Cheque No., Txn ID, etc.)",
    value="N/A" if mode_of_payment == "Cash" else ""
)

# --- Amount Received Input ---
amount_received = st.number_input(
    "Amount Received (INR)",
    min_value=1.00,
    step=1000.00,
    value=11000.00, # Defaulting to the booking amount
    format="%.2f"
)

# --- Default Description ---
default_description = (
    "Booking advance for Intelligent Vision Analyser Plus (iVA+)\n"
    "4th Generation - VR based visual field testing device - complete kit"
)
product_description = st.text_area(
    "Description / Purpose of Payment",
    value=default_description,
    height=100
)

st.divider()

send_to_customer = st.checkbox(" Send a copy directly to the Customer Email", value=False) 

if st.button("Generate Payment Receipt PDF and Send Emails"):
    
    # Input validation
    if not customer_name:
        st.error("Please enter the **Customer Name**.")
        st.stop()
    if send_to_customer and not customer_email:
        st.error("Please enter the **Customer Email** to send the receipt.")
        st.stop()
        
    # Clear the temporary session state key to force counter increment
    if 'current_receipt_num' in st.session_state:
        del st.session_state['current_receipt_num']
        
    # Generate the sequential receipt number
    receipt_no = get_next_receipt_number(receipt_date)
    receipt_date_str = receipt_date.strftime("%d/%m/%Y")

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # --- PDF Generation Logic ---
    styles = getSampleStyleSheet()
    para_style = ParagraphStyle(
        'Normal_Left',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_LEFT
    )

    c.rect(BORDER_MARGIN, BORDER_MARGIN, WIDTH - 2 * BORDER_MARGIN, HEIGHT - 2 * BORDER_MARGIN)

    # Header
    c.setFillColor(HexColor('#255290'))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(WIDTH / 2, HEIGHT - 40, "ALFALEUS TECHNOLOGY PRIVATE LIMITED")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 9)
    c.drawCentredString(WIDTH / 2, HEIGHT - 55,
        "Registered Office : II Floor, 654, Vivek Vihar, New Sanganare Road, Jaipur, Rajasthan - 302019")
    c.drawCentredString(WIDTH / 2, HEIGHT - 68,
        "CIN : U74999RJ2018PTC060255 | Mail : info@alfaleus.com | Contact : +91 96550 42547")

    # Receipt Title
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(WIDTH / 2, HEIGHT - 110, "OFFICIAL PAYMENT RECEIPT")

    # Receipt Info
    y = HEIGHT - 140
    
    # Receipt Number and Date
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Receipt No:")
    c.setFont("Helvetica", 11)
    c.drawString(130, y, receipt_no)
    
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(WIDTH - 150, y, "Date:")
    c.setFont("Helvetica", 11)
    c.drawRightString(WIDTH - 50, y, receipt_date_str)
    
    y -= 40 # Spacing after Receipt Date
    
    # Payer Info (Customer Details)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "RECEIVED FROM")
    c.line(50, y - 2, WIDTH - 50, y - 2)
    y -= 15
    
    c.setFont("Helvetica-Bold", 10) 
    bold_label = "Name : "
    c.drawString(50, y, bold_label)
    label_width = c.stringWidth(bold_label, "Helvetica-Bold", 10)
    c.setFont("Helvetica-Bold", 10) 
    c.drawString(50 + label_width, y, customer_name)
    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(50, y, f"Email : {customer_email}")
    y -= 15
    address_text = address.replace('\n', '<br/>')
    address_para = Paragraph(f"Address : {address_text}", para_style)
    w_addr, h_addr = address_para.wrapOn(c, WIDTH - 100, HEIGHT) 
    address_para.drawOn(c, 50, y - h_addr)
    y -= (h_addr + 15) 
    c.drawString(50, y, f"GSTIN : {gstin}")
    y -= 30

    # Payment Details Table
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "PAYMENT INFORMATION")
    y -= 20
    
    # Table Headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "S No.")
    c.drawString(90, y, "Description / Purpose")
    c.drawString(420, y, "Mode of Payment") 
    c.drawString(510, y, "Amount (Rs.)") 
    y -= 10
    c.line(50, y, 550, y)
    y -= 15
    
    # Table Content - Description
    c.setFont("Helvetica", 10)
    c.drawString(55, y, "1")
    desc_text = product_description.replace('\n', '<br/>')
    desc_para = Paragraph(desc_text, para_style)
    w_desc, h_desc = desc_para.wrapOn(c, 320, HEIGHT) 
    y_start_desc = y - (h_desc - 10) 
    desc_para.drawOn(c, 90, y_start_desc)
    
    # Table Content - Payment Details
    c.drawString(420, y, mode_of_payment) 
    c.drawRightString(550, y, f"{amount_received:,.2f}") 
    y = y_start_desc - 15

    # Reference Details
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Reference/Txn Details:")
    c.setFont("Helvetica", 10)
    c.drawString(180, y, reference_details)
    
    y -= 40 # Spacing above Total

    # Total Amount Received Section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, y, "TOTAL AMOUNT RECEIVED:")
    c.drawRightString(550, y, f"Rs. {amount_received:,.2f}")
    
    # Amount in Words
    y -= 30
    words = num2words(round(amount_received), lang='en_IN').title()
    bold_value = "Value in words"
    normal_text_words = f": Rupees {words} Only."
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, bold_value)
    words_width = c.stringWidth(bold_value, "Helvetica-Bold", 10)
    c.setFont("Helvetica", 10)
    c.drawString(50 + words_width, y, normal_text_words)

    # Note / Declaration
    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Note:")
    y -= 15
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "This receipt acknowledges payment towards the specified purpose and details above.")
    y -= 15
    c.drawString(50, y, "Currency is Indian Rupees (INR) unless otherwise specified.")
    
    # NEW CHANGE: Add "Payment received by"
    y -= 15 
    c.setFont("Helvetica-Bold", 10)
    bold_label_received = "Payment received by:"
    c.drawString(50, y, bold_label_received)
    received_by_width = c.stringWidth(bold_label_received, "Helvetica-Bold", 10)
    c.setFont("Helvetica", 10)
    c.drawString(50 + received_by_width + 5, y, generator_name) # Uses the generator's name
    y -= 30 # Extra spacing before the signature block

    # Signature (Right-Aligned) - Issued By
    # MOVED CHANGE: Move signature block down after the note section
    RIGHT_POS = WIDTH - 50 
    
    c.setFont("Helvetica", 10)
    c.drawRightString(RIGHT_POS, y, f"For Alfaleus Technology Pvt. Ltd")
    y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(RIGHT_POS, y, generator_name) # Signature Name
    c.setFont("Helvetica", 9)
    c.drawRightString(RIGHT_POS, y - 12, generator_title) # Signature Title


    # Footer (position adjusted to stay near the bottom margin)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, BORDER_MARGIN + 15,
        "This is a computer generated receipt and does not require physical signature. "
        "For any queries, contact info@alfaleus.com")

    # ---- Save PDF to buffer ----
    c.showPage()
    c.save()
    buffer.seek(0)
    
    # --- DYNAMIC CC LOGIC ---
    primary_cc = PRIMARY_CC_MAPPING.get(generator_name)
    final_cc_list = set()
    if primary_cc:
        final_cc_list.add(primary_cc)
    final_cc_list.update(SECONDARY_CC_EMAILS)
    final_cc_list = list(final_cc_list)
    # ------------------------

    # --- EMAIL THE PDF COPY ---
    # 1. Send internal copy (always)
    send_receipt_email(receipt_no, INTERNAL_RECEIVER_EMAIL, customer_name, buffer, generator_name, is_customer_send=False)
    
    # Reset buffer for the second email
    buffer.seek(0) 

    # 2. Send to customer (if checked and email provided)
    if send_to_customer and customer_email:
        send_receipt_email(receipt_no, customer_email, customer_name, buffer, generator_name, final_cc_list, is_customer_send=True)
    # --------------------------

    # ---- Download Button ----
    st.download_button(
        label="📄 Download Payment Receipt PDF",
        data=buffer,
        file_name=f"Alfaleus_Receipt_{receipt_no}.pdf",
        mime="application/pdf"
    )