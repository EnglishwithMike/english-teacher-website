from flask import Flask, render_template, request, redirect
import sqlite3
import os
import stripe
import resend
from dotenv import load_dotenv

load_dotenv()

OWNER_EMAIL = os.getenv("OWNER_EMAIL")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

stripe.api_key = STRIPE_SECRET_KEY
resend.api_key = RESEND_API_KEY

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,
            time TEXT,
            name TEXT,
            email TEXT,
            phone TEXT
        )
    """)

    try:
        c.execute("ALTER TABLE bookings ADD COLUMN checkout_session_id TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE bookings ADD COLUMN email_sent INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()


def send_email(to_email, subject, message):
    try:
        resend.Emails.send({
            "from": f"English with Mike <{SENDER_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "text": message,
        })
        return True

    except Exception as e:
        print("RESEND EMAIL ERROR:", repr(e))
        return False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/booking")
def booking():
    return render_template("booking.html")


@app.route("/booking/<day>")
def booking_day(day):
    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("SELECT time FROM bookings WHERE day=?", (day,))
    booked_times = [row[0] for row in c.fetchall()]

    conn.close()

    return render_template("booking_day.html", day=day, booked=booked_times)


@app.route("/book", methods=["POST"])
def book():
    day = request.form["day"]
    time = request.form["time"]
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]

    if not time:
        return "Please choose a lesson time."

    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("SELECT * FROM bookings WHERE day=? AND time=?", (day, time))
    exists = c.fetchone()

    conn.close()

    if exists:
        return "This slot is already booked."

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "gbp",
                    "product_data": {
                        "name": "English Lesson",
                    },
                    "unit_amount": 1000,
                },
                "quantity": 1,
            }
        ],
        success_url="https://english-teacher-website-xe4z.onrender.com/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://english-teacher-website-xe4z.onrender.com/booking",
        metadata={
            "day": day,
            "time": time,
            "name": name,
            "email": email,
            "phone": phone,
        },
    )

    return redirect(checkout_session.url)


@app.route("/success")
def success():
    session_id = request.args.get("session_id")

    if not session_id:
        return "No payment session found."

    checkout_session = stripe.checkout.Session.retrieve(session_id)

    if checkout_session.payment_status != "paid":
        return "Payment not completed."

    day = checkout_session.metadata["day"]
    time = checkout_session.metadata["time"]
    name = checkout_session.metadata["name"]
    email = checkout_session.metadata["email"]
    phone = checkout_session.metadata["phone"]

    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("SELECT * FROM bookings WHERE checkout_session_id=?", (session_id,))
    already_saved = c.fetchone()

    c.execute("SELECT * FROM bookings WHERE day=? AND time=?", (day, time))
    slot_taken = c.fetchone()

    if slot_taken and not already_saved:
        conn.close()
        return "Sorry, this lesson slot was booked by another student while payment was being processed. Please choose another time."

    if not already_saved:
        c.execute("""
            INSERT INTO bookings (day, time, name, email, phone, checkout_session_id, email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (day, time, name, email, phone, session_id, 0))
        conn.commit()

    conn.close()

    owner_msg = f"""
New paid booking received:

Name: {name}
Email: {email}
Phone: {phone}
Day: {day}
Time: {time}
Payment: £10 paid
"""
    owner_email_ok = send_email(OWNER_EMAIL, "New Paid Lesson Booking", owner_msg)

    student_msg = f"""
Hi {name},

Your lesson has been booked successfully.

Day: {day}
Time: {time}

If you need anything or have any questions, please feel free to send me an email. I will try to reply as soon as possible.

Email: {OWNER_EMAIL}

See you then!
"""
    student_email_ok = send_email(email, "Booking Confirmed", student_msg)

    if owner_email_ok and student_email_ok:
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        c.execute("UPDATE bookings SET email_sent=1 WHERE checkout_session_id=?", (session_id,))
        conn.commit()
        conn.close()

    return render_template("success.html", day=day, time=time)


if __name__ == "__main__":
    app.run(debug=True)
