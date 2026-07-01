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

TEACHERS = {
    "mike": {
        "name": "Mike",
        "flag": "🇬🇧",
        "lesson_name": "English Lesson with Mike",
    },
    "emily": {
        "name": "Emily",
        "flag": "🇪🇸",
        "lesson_name": "Spanish Lesson with Emily",
    }
}


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

    for column in [
        "checkout_session_id TEXT",
        "email_sent INTEGER DEFAULT 0",
        "teacher TEXT DEFAULT 'mike'"
    ]:
        try:
            c.execute(f"ALTER TABLE bookings ADD COLUMN {column}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


init_db()


def send_email(to_email, subject, message):
    try:
        resend.Emails.send({
            "from": f"LearningXY <{SENDER_EMAIL}>",
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
    return render_template("index.html", teachers=TEACHERS)


@app.route("/booking")
def booking():
    return render_template("booking.html", teacher="mike", teacher_info=TEACHERS["mike"])


@app.route("/booking/emily")
def booking_emily():
    return render_template("booking.html", teacher="emily", teacher_info=TEACHERS["emily"])


@app.route("/booking/<day>")
def booking_day(day):
    return show_booking_day("mike", day)


@app.route("/booking/emily/<day>")
def booking_day_emily(day):
    return show_booking_day("emily", day)


def show_booking_day(teacher, day):
    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("SELECT time FROM bookings WHERE teacher=? AND day=?", (teacher, day))
    booked_times = [row[0] for row in c.fetchall()]

    conn.close()

    return render_template(
        "booking_day.html",
        day=day,
        booked=booked_times,
        teacher=teacher,
        teacher_info=TEACHERS[teacher]
    )


@app.route("/book", methods=["POST"])
def book():
    teacher = request.form.get("teacher", "mike")

    if teacher not in TEACHERS:
        teacher = "mike"

    day = request.form["day"]
    time = request.form["time"]
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]

    if not time:
        return "Please choose a lesson time."

    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute(
        "SELECT * FROM bookings WHERE teacher=? AND day=? AND time=?",
        (teacher, day, time)
    )
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
                        "name": TEACHERS[teacher]["lesson_name"],
                    },
                    "unit_amount": 1000,
                },
                "quantity": 1,
            }
        ],
        success_url="https://english-teacher-website-xe4z.onrender.com/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=f"https://english-teacher-website-xe4z.onrender.com/booking/{'emily' if teacher == 'emily' else ''}",
        metadata={
            "teacher": teacher,
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

    teacher = checkout_session.metadata.get("teacher", "mike")

    if teacher not in TEACHERS:
        teacher = "mike"

    teacher_name = TEACHERS[teacher]["name"]
    teacher_flag = TEACHERS[teacher]["flag"]

    day = checkout_session.metadata["day"]
    time = checkout_session.metadata["time"]
    name = checkout_session.metadata["name"]
    email = checkout_session.metadata["email"]
    phone = checkout_session.metadata["phone"]

    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("SELECT * FROM bookings WHERE checkout_session_id=?", (session_id,))
    already_saved = c.fetchone()

    c.execute(
        "SELECT * FROM bookings WHERE teacher=? AND day=? AND time=?",
        (teacher, day, time)
    )
    slot_taken = c.fetchone()

    if slot_taken and not already_saved:
        conn.close()
        return "Sorry, this lesson slot was booked by another student while payment was being processed. Please choose another time."

    if not already_saved:
        c.execute("""
            INSERT INTO bookings (teacher, day, time, name, email, phone, checkout_session_id, email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (teacher, day, time, name, email, phone, session_id, 0))
        conn.commit()

    conn.close()

    owner_msg = f"""
New paid booking received:

Teacher: {teacher_name} {teacher_flag}
Student name: {name}
Student email: {email}
Student phone: {phone}
Day: {day}
Time: {time}
Payment: £10 paid

Emily lesson split if this is for Emily:
Your 4.5%: £0.45
Emily share before Stripe fees: £9.55
"""

    owner_email_ok = send_email(
        OWNER_EMAIL,
        f"New Paid Lesson Booking for {teacher_name}",
        owner_msg
    )

    student_msg = f"""
Hi {name},

Your lesson with {teacher_name} {teacher_flag} has been booked successfully.

Day: {day}
Time: {time}

If you need anything or have any questions, please send an email here:

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

    return render_template("success.html", day=day, time=time, teacher_info=TEACHERS[teacher])

@app.route("/success-preview")
def success_preview():
    return render_template(
        "success.html",
        day="Monday",
        time="10:00",
        teacher_info=TEACHERS["mike"]
    )




if __name__ == "__main__":
    app.run(debug=True)
