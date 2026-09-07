from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image
)

from reportlab.lib.styles import getSampleStyleSheet
from django.core.files import File

import qrcode
import os


def generate_ticket(
    booking,
    payment,
    output_path
):

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    doc = SimpleDocTemplate(output_path)

    styles = getSampleStyleSheet()

    seat_numbers = booking.booked_seats or "Not Available"

    # Generate QR Code
    qr_data = (
    f"http://127.0.0.1:8000/"
    f"verify-ticket/"
    f"{booking.booking_reference}/"
)
    qr_path = os.path.join(
        os.path.dirname(output_path),
        f"qr_{booking.id}.png"
    )

    qr = qrcode.make(qr_data)
    qr.save(qr_path)

    elements = [

        Paragraph(
            "🎬 MovieVerse E-Ticket",
            styles["Title"]
        ),

        Spacer(1, 20),

        Paragraph(
            "<b>Booking Confirmation</b>",
            styles["Heading2"]
        ),

        Spacer(1, 15),

        Paragraph(
            f"<b>Movie:</b> {booking.movie.title}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>User:</b> {booking.user.username}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Booking Reference:</b> {booking.booking_reference}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Payment ID:</b> {payment.transaction_id}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Theater:</b> {booking.schedule.theater.name}",
            styles["Normal"]
        ),

        Paragraph(
            "<b>Screen:</b> Screen 1",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Location:</b> {booking.schedule.theater.location}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Show Time:</b> {booking.schedule.show_time.strftime('%d-%m-%Y %I:%M %p')}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Seats:</b> {seat_numbers}",
            styles["Normal"]
        ),

        Paragraph(
            f"<b>Ticket Price:</b> ₹{booking.schedule.ticket_price}",
            styles["Normal"]
        ),

        Spacer(1, 20),

        Paragraph(
            "Please carry this ticket during entry. "
            "You may show either a printed copy or the PDF version on your mobile device.",
            styles["Normal"]
        ),

        Spacer(1, 20),

        Paragraph(
            "Thank you for booking with MovieVerse. Enjoy your movie!",
            styles["Italic"]
        ),

        Spacer(1, 20),

        Paragraph(
            "<b>Verification QR Code</b>",
            styles["Heading3"]
        ),

        Spacer(1, 10),

        Image(
            qr_path,
            width=120,
            height=120
        )
    ]

    doc.build(elements)

    with open(output_path, "rb") as pdf_file:

        booking.ticket_pdf.save(
            f"ticket_{booking.id}.pdf",
            File(pdf_file),
            save=True
        )

    return output_path