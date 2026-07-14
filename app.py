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
    },
    "michalis": {
        "name": "Michalis",
        "flag": "🇬🇷",
        "lesson_name": "Greek Lesson with Michalis",
    }
}

TRANSLATIONS = {
    "en": {
        "slogan": "Learning in every direction.",
        "book_a_lesson": "Book a Lesson",
        "about_us": "About Us",
        "about_intro": "LearningXY is an independent online learning website that gives people from all around the world the opportunity to learn while also allowing teachers to create and offer their own lessons.",
        "qualified_tutors": "Qualified and supportive tutors",
        "personalised_lessons": "Lessons personalised to your goals",
        "worldwide_lessons": "Online lessons available worldwide",
        "our_goal": "Our goal is to help learners become more confident and make steady progress in a comfortable learning environment.",
        "follow_socials": "Follow Our Socials!",
        "english_lessons": "English Lessons",
        "greek_lessons": "Greek Lessons",
        "spanish_lessons": "Spanish Lessons",
        "book_english": "Book English",
        "book_greek": "Book Greek",
        "book_spanish": "Book Spanish",
        "book_your_lesson": "Book Your Lesson",
        "select_day_mf": "Select a day (Monday–Friday)",
        "select_day_ms": "Select a day (Monday–Saturday)",
        "back_home": "Back to homepage",
        "about": "About",
        "select_time": "Select a lesson time",
        "uk_time_note": "All bookings are saved in UK time. Your local time is shown for convenience.",
        "booked": "Booked",
        "booking_details": "Booking Details",
        "your_name": "Your Name",
        "email": "Email",
        "phone": "Phone / WhatsApp (optional)",
        "book_lesson": "Book Lesson",
        "back_calendar": "← Back to Calendar",
        "your_time": "your time",
        "choose_time_alert": "Please choose a lesson time first.",
        "congrats": "🎉 Congratulations!",
        "confirmed": "Your booking is confirmed",
        "booked_for": "You are booked for:",
        "day": "Day",
        "time": "Time",
        "contact_text": "If you need anything beforehand or have any questions, feel free to contact me:",
        "return_home": "Return to Homepage",
        "mike_bio_1": "Graduate teacher with experience specialising in teaching English.",
        "mike_bio_2": "During my studies I volunteered in numerous schools, gaining valuable classroom experience with learners of different ages.",
        "mike_bio_3": "I also completed the internationally recognised Trinity CertTESOL, where I taught university students and further developed my teaching, lesson planning and classroom management skills.",
        "michalis_bio": "Greek teacher offering personalised online Greek lessons for learners who want to build confidence and communicate clearly.",
        "emily_bio_1": "Spanish teacher offering personalised online Spanish lessons.",
        "emily_bio_2": "Lessons are designed to help students build confidence, improve communication skills and practise useful Spanish for real situations.",
    },
    "el": {
        "slogan": "Μάθηση προς κάθε κατεύθυνση.",
        "book_a_lesson": "Κλείστε ένα Μάθημα",
        "about_us": "Σχετικά με Εμάς",
        "about_intro": "Το LearningXY είναι μια ανεξάρτητη διαδικτυακή ιστοσελίδα μάθησης που δίνει σε ανθρώπους από όλο τον κόσμο την ευκαιρία να μάθουν, ενώ παράλληλα επιτρέπει σε εκπαιδευτικούς να δημιουργούν και να προσφέρουν τα δικά τους μαθήματα.",
        "qualified_tutors": "Καταρτισμένοι και υποστηρικτικοί καθηγητές",
        "personalised_lessons": "Μαθήματα προσαρμοσμένα στους στόχους σας",
        "worldwide_lessons": "Διαδικτυακά μαθήματα διαθέσιμα παγκοσμίως",
        "our_goal": "Στόχος μας είναι να βοηθήσουμε τους μαθητές να αποκτήσουν μεγαλύτερη αυτοπεποίθηση και να σημειώνουν σταθερή πρόοδο σε ένα άνετο μαθησιακό περιβάλλον.",
        "follow_socials": "Ακολουθήστε μας στα κοινωνικά δίκτυα!",
        "english_lessons": "Μαθήματα Αγγλικών",
        "greek_lessons": "Μαθήματα Ελληνικών",
        "spanish_lessons": "Μαθήματα Ισπανικών",
        "book_english": "Κλείσε Αγγλικά",
        "book_greek": "Κλείσε Ελληνικά",
        "book_spanish": "Κλείσε Ισπανικά",
        "book_your_lesson": "Κλείσε το μάθημά σου",
        "select_day_mf": "Επίλεξε ημέρα (Δευτέρα–Παρασκευή)",
        "select_day_ms": "Επίλεξε ημέρα (Δευτέρα–Σάββατο)",
        "back_home": "Πίσω στην αρχική σελίδα",
        "about": "Σχετικά με",
        "select_time": "Επίλεξε ώρα μαθήματος",
        "uk_time_note": "Όλες οι κρατήσεις αποθηκεύονται σε ώρα Ηνωμένου Βασιλείου. Η τοπική σου ώρα εμφανίζεται για ευκολία.",
        "booked": "Κλεισμένο",
        "booking_details": "Στοιχεία κράτησης",
        "your_name": "Το όνομά σου",
        "email": "Email",
        "phone": "Τηλέφωνο / WhatsApp (προαιρετικό)",
        "book_lesson": "Κλείσε μάθημα",
        "back_calendar": "← Πίσω στο ημερολόγιο",
        "your_time": "η ώρα σου",
        "choose_time_alert": "Παρακαλώ επίλεξε πρώτα ώρα μαθήματος.",
        "congrats": "🎉 Συγχαρητήρια!",
        "confirmed": "Η κράτησή σου επιβεβαιώθηκε",
        "booked_for": "Έχεις κράτηση για:",
        "day": "Ημέρα",
        "time": "Ώρα",
        "contact_text": "Αν χρειάζεσαι κάτι πριν το μάθημα ή έχεις ερωτήσεις, μπορείς να επικοινωνήσεις μαζί μου:",
        "return_home": "Επιστροφή στην αρχική σελίδα",
        "mike_bio_1": "Πτυχιούχος καθηγητής με εμπειρία στη διδασκαλία της Αγγλικής γλώσσας.",
        "mike_bio_2": "Κατά τη διάρκεια των σπουδών μου εργάστηκα εθελοντικά σε πολλά σχολεία, αποκτώντας πολύτιμη εμπειρία με μαθητές διαφορετικών ηλικιών.",
        "mike_bio_3": "Ολοκλήρωσα επίσης το διεθνώς αναγνωρισμένο Trinity CertTESOL, όπου δίδαξα φοιτητές πανεπιστημίου και ανέπτυξα περαιτέρω τις δεξιότητές μου στη διδασκαλία, τον σχεδιασμό μαθημάτων και τη διαχείριση της τάξης.",
        "michalis_bio": "Καθηγητής Ελληνικών που προσφέρει εξατομικευμένα διαδικτυακά μαθήματα για μαθητές που θέλουν να αποκτήσουν αυτοπεποίθηση και να επικοινωνούν με άνεση.",
        "emily_bio_1": "Καθηγήτρια Ισπανικών που προσφέρει εξατομικευμένα διαδικτυακά μαθήματα.",
        "emily_bio_2": "Τα μαθήματα έχουν σχεδιαστεί ώστε να βοηθούν τους μαθητές να αποκτήσουν αυτοπεποίθηση, να βελτιώσουν την επικοινωνία τους και να εξασκήσουν χρήσιμα Ισπανικά για πραγματικές καταστάσεις.",
    },
    "es": {
        "slogan": "Aprendizaje en todas las direcciones.",
        "book_a_lesson": "Reserva una Clase",
        "about_us": "Sobre Nosotros",
        "about_intro": "LearningXY es un sitio web independiente de aprendizaje en línea que ofrece a personas de todo el mundo la oportunidad de aprender, al mismo tiempo que permite a los profesores crear y ofrecer sus propias clases.",
        "qualified_tutors": "Profesores cualificados y comprometidos",
        "personalised_lessons": "Clases adaptadas a tus objetivos",
        "worldwide_lessons": "Clases en línea disponibles en todo el mundo",
        "our_goal": "Nuestro objetivo es ayudar a los estudiantes a ganar confianza y progresar de forma constante en un entorno de aprendizaje cómodo.",
        "follow_socials": "¡Síguenos en nuestras redes sociales!",
        "english_lessons": "Clases de inglés",
        "greek_lessons": "Clases de griego",
        "spanish_lessons": "Clases de español",
        "book_english": "Reservar inglés",
        "book_greek": "Reservar griego",
        "book_spanish": "Reservar español",
        "book_your_lesson": "Reserva tu clase",
        "select_day_mf": "Elige un día (lunes–viernes)",
        "select_day_ms": "Elige un día (lunes–sábado)",
        "back_home": "Volver a la página principal",
        "about": "Sobre",
        "select_time": "Elige una hora para la clase",
        "uk_time_note": "Todas las reservas se guardan en horario del Reino Unido. Tu hora local se muestra para ayudarte.",
        "booked": "Reservado",
        "booking_details": "Datos de la reserva",
        "your_name": "Tu nombre",
        "email": "Email",
        "phone": "Teléfono / WhatsApp (opcional)",
        "book_lesson": "Reservar clase",
        "back_calendar": "← Volver al calendario",
        "your_time": "tu hora",
        "choose_time_alert": "Por favor, elige primero una hora para la clase.",
        "congrats": "🎉 ¡Felicidades!",
        "confirmed": "Tu reserva está confirmada",
        "booked_for": "Has reservado:",
        "day": "Día",
        "time": "Hora",
        "contact_text": "Si necesitas algo antes de la clase o tienes alguna pregunta, puedes contactarme:",
        "return_home": "Volver a la página principal",
        "mike_bio_1": "Profesor titulado con experiencia especializado en la enseñanza del inglés.",
        "mike_bio_2": "Durante mis estudios fui voluntario en varios centros educativos, adquiriendo una valiosa experiencia docente con estudiantes de diferentes edades.",
        "mike_bio_3": "También obtuve el reconocido Trinity CertTESOL, donde enseñé a estudiantes universitarios y desarrollé aún más mis habilidades de enseñanza, planificación de clases y gestión del aula.",
        "michalis_bio": "Profesor de griego que ofrece clases personalizadas en línea para estudiantes que desean ganar confianza y comunicarse con claridad.",
        "emily_bio_1": "Profesora de español que ofrece clases personalizadas en línea.",
        "emily_bio_2": "Las clases están diseñadas para ayudar a los estudiantes a ganar confianza, mejorar sus habilidades comunicativas y practicar español útil para situaciones reales.",
    }
}

def get_lang():
    lang = request.args.get("lang", "en")
    if lang not in TRANSLATIONS:
        lang = "en"
    return lang



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

    c.execute("""
        CREATE TABLE IF NOT EXISTS free_lessons (
            email TEXT PRIMARY KEY
        )
    """)

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



@app.route("/robots.txt")
def robots_txt():
    return app.send_static_file("robots.txt")


@app.route("/sitemap.xml")
def sitemap_xml():
    return app.send_static_file("sitemap.xml")


@app.route("/")
def home():
    lang = get_lang()
    return render_template("index.html", teachers=TEACHERS, lang=lang, t=TRANSLATIONS[lang])


@app.route("/booking")
def booking():
    lang = get_lang()
    return render_template("booking.html", teacher="mike", teacher_info=TEACHERS["mike"], lang=lang, t=TRANSLATIONS[lang])


@app.route("/booking/emily")
def booking_emily():
    lang = get_lang()
    return render_template("booking.html", teacher="emily", teacher_info=TEACHERS["emily"], lang=lang, t=TRANSLATIONS[lang])


@app.route("/booking/michalis")
def booking_michalis():
    lang = get_lang()
    return render_template("booking.html", teacher="michalis", teacher_info=TEACHERS["michalis"], lang=lang, t=TRANSLATIONS[lang])


@app.route("/booking/<day>")
def booking_day(day):
    return show_booking_day("mike", day)


@app.route("/booking/emily/<day>")
def booking_day_emily(day):
    return show_booking_day("emily", day)


@app.route("/booking/michalis/<day>")
def booking_day_michalis(day):
    return show_booking_day("michalis", day)


def show_booking_day(teacher, day):
    lang = get_lang()

    # TEMPORARY: this Wednesday is fully booked
    if day == "Wednesday":
        booked_times = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
    else:
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()

        # Mike and Michalis are the same person, so their bookings share availability
        if teacher in ["mike", "michalis"]:
            c.execute("SELECT time FROM bookings WHERE teacher IN ('mike', 'michalis') AND day=?", (day,))
        else:
            c.execute("SELECT time FROM bookings WHERE teacher=? AND day=?", (teacher, day))

        booked_times = [row[0] for row in c.fetchall()]
        conn.close()

    return render_template(
        "booking_day.html",
        day=day,
        booked=booked_times,
        teacher=teacher,
        teacher_info=TEACHERS[teacher],
        lang=lang,
        t=TRANSLATIONS[lang]
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
    lang = request.form.get("lang", "en")
    if lang not in TRANSLATIONS:
        lang = "en"

    if not time:
        return "Please choose a lesson time."

    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    if teacher in ["mike", "michalis"]:
        c.execute(
            "SELECT * FROM bookings WHERE teacher IN ('mike', 'michalis') AND day=? AND time=?",
            (day, time)
        )
    else:
        c.execute(
            "SELECT * FROM bookings WHERE teacher=? AND day=? AND time=?",
            (teacher, day, time)
        )

    exists = c.fetchone()

    c.execute("SELECT email FROM free_lessons WHERE lower(email)=lower(?)", (email,))
    previous_booking = c.fetchone()

    conn.close()

    if exists:
        return "This slot is already booked."

    # First lesson is free
    if teacher in ["mike", "michalis"] and not previous_booking:
        conn = sqlite3.connect("bookings.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO bookings (teacher, day, time, name, email, phone, checkout_session_id, email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (teacher, day, time, name, email, phone, "FREE_FIRST_LESSON", 0))

        c.execute("INSERT OR IGNORE INTO free_lessons (email) VALUES (?)", (email.lower(),))

        conn.commit()
        conn.close()

        teacher_name = TEACHERS[teacher]["name"]
        teacher_flag = TEACHERS[teacher]["flag"]

        send_email(
            OWNER_EMAIL,
            f"New Free First Lesson Booking for {teacher_name}",
            f"""New FREE first lesson booking received:

Teacher: {teacher_name} {teacher_flag}
Student name: {name}
Student email: {email}
Student phone: {phone}
Day: {day}
Time: {time}
Payment: Free first lesson
"""
        )

        send_email(
            email,
            "Free First Lesson Booking Confirmed",
            f"""Hi {name},

Your free first lesson with {teacher_name} {teacher_flag} has been booked successfully.

Day: {day}
Time: {time}

If you need anything or have any questions, please send an email here:

Email: {OWNER_EMAIL}

See you then!
"""
        )

        return render_template("success.html", day=day, time=time, teacher=teacher, teacher_info=TEACHERS[teacher], lang=lang, t=TRANSLATIONS[lang])

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
        cancel_url=f"https://english-teacher-website-xe4z.onrender.com/booking/{teacher if teacher != 'mike' else ''}",
        metadata={
            "teacher": teacher,
            "day": day,
            "time": time,
            "name": name,
            "email": email,
            "phone": phone,
            "lang": lang,
        },
    )

    return render_template(
        "checkout_redirect.html",
        checkout_url=checkout_session.url,
        teacher=teacher,
        day=day,
        time=time,
        lang=lang
    )


@app.route("/success")
def success():
    session_id = request.args.get("session_id")

    if not session_id:
        return "No payment session found."

    checkout_session = stripe.checkout.Session.retrieve(session_id)

    if checkout_session.payment_status != "paid":
        return "Payment not completed."

    metadata = checkout_session.metadata._data
    teacher = metadata.get("teacher", "mike")
    lang = metadata.get("lang", "en")
    if lang not in TRANSLATIONS:
        lang = "en"

    if teacher not in TEACHERS:
        teacher = "mike"

    teacher_name = TEACHERS[teacher]["name"]
    teacher_flag = TEACHERS[teacher]["flag"]

    day = metadata["day"]
    time = metadata["time"]
    name = metadata["name"]
    email = metadata["email"]
    phone = metadata["phone"]

    conn = sqlite3.connect("bookings.db")
    c = conn.cursor()

    c.execute("SELECT * FROM bookings WHERE checkout_session_id=?", (session_id,))
    already_saved = c.fetchone()

    if teacher in ["mike", "michalis"]:
        c.execute(
            "SELECT * FROM bookings WHERE teacher IN ('mike', 'michalis') AND day=? AND time=?",
            (day, time)
        )
    else:
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

    return render_template("success.html", day=day, time=time, teacher=teacher, teacher_info=TEACHERS[teacher], lang=lang, t=TRANSLATIONS[lang])

@app.route("/success-preview")
def success_preview():
    return render_template(
        "success.html",
        day="Monday",
        time="10:00",
        teacher="mike",
        teacher_info=TEACHERS["mike"],
        lang="en",
        t=TRANSLATIONS["en"]
    )




if __name__ == "__main__":
    app.run(debug=True)
