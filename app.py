from flask import Flask, render_template, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import database as sqlite3
from cloud_storage import (
    PROOF_BUCKET,
    PROFILE_BUCKET,
    cache_profile_image,
    inline_response,
    proof_preview_response,
    remove_file,
    upload_file,
)
import os
import uuid
import time
import subprocess
from functools import wraps
from zoneinfo import ZoneInfo, available_timezones
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
app.secret_key = os.getenv("FLASK_SECRET_KEY")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")


def admin_required(function):
    @wraps(function)
    def protected_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect("/admin/login")
        return function(*args, **kwargs)
    return protected_function


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
            "reply_to": OWNER_EMAIL,
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



def get_public_approved_teachers():
    if not os.path.exists("approved_teachers.db"):
        return []

    conn = sqlite3.connect("approved_teachers.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    table_exists = cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'approved_teachers'
    """).fetchone()

    if not table_exists:
        conn.close()
        return []

    teachers = cursor.execute("""
        SELECT id, slug, name, surname, subject, bio,
               profile_image, hourly_rate_pence
        FROM approved_teachers
        WHERE active = 1
        ORDER BY approved_at ASC
    """).fetchall()

    conn.close()

    for teacher in teachers:
        cache_profile_image(teacher["profile_image"], app.root_path)

    return teachers


def get_approved_teacher_by_slug(slug):
    if not os.path.exists("approved_teachers.db"):
        return None

    conn = sqlite3.connect("approved_teachers.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT id, application_id, slug, name, surname,
               email, subject, bio, profile_image,
               hourly_rate_pence, timezone, active
        FROM approved_teachers
        WHERE slug = ? AND active = 1
    """, (slug,)).fetchone()

    conn.close()

    if not teacher:
        return None

    cache_profile_image(teacher["profile_image"], app.root_path)

    return {
        "id": teacher["id"],
        "application_id": teacher["application_id"],
        "slug": teacher["slug"],
        "name": teacher["name"],
        "surname": teacher["surname"],
        "full_name": f"{teacher['name']} {teacher['surname']}",
        "email": teacher["email"],
        "subject": teacher["subject"],
        "bio": teacher["bio"],
        "profile_image": teacher["profile_image"],
        "hourly_rate_pence": teacher["hourly_rate_pence"],
        "timezone": teacher["timezone"],
        "flag": "🎓",
        "lesson_name": (
            f"{teacher['subject']} Lesson with {teacher['name']}"
        ),
        "dynamic": True,
    }


@app.route("/")
def home():
    lang = get_lang()
    return render_template(
        "index.html",
        teachers=TEACHERS,
        approved_teachers=get_public_approved_teachers(),
        lang=lang,
        t=TRANSLATIONS[lang]
    )



def get_dynamic_teacher_availability(teacher_id):
    conn = sqlite3.connect("approved_teachers.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT day, start_time, end_time
        FROM teacher_availability
        WHERE teacher_id = ?
        ORDER BY
            CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
    """, (teacher_id,)).fetchall()

    conn.close()
    return rows


def generate_lesson_times(start_time, end_time):
    start_hour, start_minute = map(int, start_time.split(":"))
    end_hour, end_minute = map(int, end_time.split(":"))

    current_minutes = start_hour * 60 + start_minute
    ending_minutes = end_hour * 60 + end_minute
    lesson_times = []

    while current_minutes + 60 <= ending_minutes:
        hour = current_minutes // 60
        minute = current_minutes % 60
        lesson_times.append(f"{hour:02d}:{minute:02d}")
        current_minutes += 60

    return lesson_times


@app.route("/booking/teacher/<teacher_slug>")
def booking_approved_teacher(teacher_slug):
    lang = get_lang()
    teacher_info = get_approved_teacher_by_slug(teacher_slug)

    if not teacher_info:
        return "Teacher not found.", 404

    availability = get_dynamic_teacher_availability(
        teacher_info["id"]
    )

    return render_template(
        "booking.html",
        teacher=teacher_slug,
        teacher_info=teacher_info,
        dynamic_teacher=True,
        available_days=[row["day"] for row in availability],
        lang=lang,
        t=TRANSLATIONS[lang]
    )


@app.route("/booking/teacher/<teacher_slug>/qualification")
def public_teacher_qualification(teacher_slug):
    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    qualification = cursor.execute("""
        SELECT application.proof_filename
        FROM approved_teachers AS teacher
        JOIN teacher_applications AS application
          ON application.id = teacher.application_id
        WHERE teacher.slug = ?
          AND teacher.active = 1
          AND application.status = 'approved'
          AND application.deleted_at IS NULL
    """, (teacher_slug,)).fetchone()

    conn.close()

    if not qualification or not qualification[0]:
        return "Qualification not found.", 404

    try:
        return proof_preview_response(
            os.path.basename(qualification[0])
        )
    except Exception as error:
        print("PUBLIC QUALIFICATION ERROR:", repr(error))
        return "The qualification could not be displayed.", 404


@app.route("/booking/teacher/<teacher_slug>/<day>")
def booking_day_approved_teacher(teacher_slug, day):
    lang = get_lang()
    teacher_info = get_approved_teacher_by_slug(teacher_slug)

    if not teacher_info:
        return "Teacher not found.", 404

    availability = get_dynamic_teacher_availability(
        teacher_info["id"]
    )

    selected_day = next(
        (row for row in availability if row["day"] == day),
        None
    )

    if not selected_day:
        return "This teacher is not available on that day.", 404

    available_times = generate_lesson_times(
        selected_day["start_time"],
        selected_day["end_time"]
    )

    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT time
        FROM bookings
        WHERE teacher = ? AND day = ?
    """, (teacher_slug, day))
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template(
        "booking_day.html",
        day=day,
        booked=booked_times,
        available_times=available_times,
        teacher=teacher_slug,
        teacher_info=teacher_info,
        dynamic_teacher=True,
        lang=lang,
        t=TRANSLATIONS[lang]
    )


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
    teacher_info = TEACHERS.get(teacher)
    dynamic_teacher = False

    if not teacher_info:
        teacher_info = get_approved_teacher_by_slug(teacher)
        dynamic_teacher = True

    if not teacher_info:
        return "Teacher not found.", 404

    day = request.form.get("day", "")
    lesson_time = request.form.get("time", "")
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    lang = request.form.get("lang", "en")

    if lang not in TRANSLATIONS:
        lang = "en"

    if not lesson_time:
        return "Please choose a lesson time.", 400

    if dynamic_teacher:
        availability = get_dynamic_teacher_availability(
            teacher_info["id"]
        )

        selected_day = next(
            (row for row in availability if row["day"] == day),
            None
        )

        if not selected_day:
            return "This teacher is not available on that day.", 400

        valid_times = generate_lesson_times(
            selected_day["start_time"],
            selected_day["end_time"]
        )

        if lesson_time not in valid_times:
            return "That lesson time is not available.", 400

    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()

    if teacher in ["mike", "michalis"]:
        cursor.execute("""
            SELECT id FROM bookings
            WHERE teacher IN ('mike', 'michalis')
            AND day = ? AND time = ?
        """, (day, lesson_time))
    else:
        cursor.execute("""
            SELECT id FROM bookings
            WHERE teacher = ? AND day = ? AND time = ?
        """, (teacher, day, lesson_time))

    slot_exists = cursor.fetchone()

    cursor.execute("""
        SELECT email FROM free_lessons
        WHERE lower(email) = lower(?)
    """, (email,))
    previous_free_lesson = cursor.fetchone()

    conn.close()

    if slot_exists:
        return "This slot is already booked.", 409

    if teacher in ["mike", "michalis"] and not previous_free_lesson:
        conn = sqlite3.connect("bookings.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bookings
            (
                teacher, day, time, name, email, phone,
                checkout_session_id, email_sent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            teacher, day, lesson_time, name, email, phone,
            "FREE_FIRST_LESSON", 0
        ))

        cursor.execute("""
            INSERT OR IGNORE INTO free_lessons (email)
            VALUES (?)
        """, (email.lower(),))

        conn.commit()
        conn.close()

        teacher_name = teacher_info["name"]
        teacher_flag = teacher_info["flag"]

        send_email(
            OWNER_EMAIL,
            f"New Free First Lesson Booking for {teacher_name}",
            f"""New FREE first lesson booking received:

Teacher: {teacher_name} {teacher_flag}
Student: {name}
Student email: {email}
Student phone: {phone}
Day: {day}
Time: {lesson_time}
"""
        )

        send_email(
            email,
            "Free First Lesson Booking Confirmed",
            f"""Hi {name},

Your free first lesson with {teacher_name} has been booked.

Day: {day}
Time: {lesson_time} UK time

See you then!
"""
        )

        return render_template(
            "success.html",
            day=day,
            time=lesson_time,
            teacher=teacher,
            teacher_info=teacher_info,
            lang=lang,
            t=TRANSLATIONS[lang]
        )

    unit_amount = (
        teacher_info["hourly_rate_pence"]
        if dynamic_teacher else 1000
    )

    base_url = request.host_url.rstrip("/")

    if dynamic_teacher:
        cancel_url = (
            f"{base_url}/booking/teacher/{teacher}"
            f"?lang={lang}"
        )
    elif teacher == "mike":
        cancel_url = f"{base_url}/booking?lang={lang}"
    else:
        cancel_url = f"{base_url}/booking/{teacher}?lang={lang}"

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "gbp",
                    "product_data": {
                        "name": teacher_info["lesson_name"],
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }
        ],
        success_url=(
            f"{base_url}/success"
            "?session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=cancel_url,
        metadata={
            "teacher": teacher,
            "day": day,
            "time": lesson_time,
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
        time=lesson_time,
        lang=lang
    )


@app.route("/success")
def success():
    session_id = request.args.get("session_id")

    if not session_id:
        return "No payment session found.", 400

    checkout_session = stripe.checkout.Session.retrieve(session_id)

    if checkout_session.payment_status != "paid":
        return "Payment not completed.", 400

    metadata = checkout_session.metadata._data
    teacher = metadata.get("teacher", "mike")
    teacher_info = TEACHERS.get(teacher)
    dynamic_teacher = False

    if not teacher_info:
        teacher_info = get_approved_teacher_by_slug(teacher)
        dynamic_teacher = True

    if not teacher_info:
        return "The booked teacher account was not found.", 404

    lang = metadata.get("lang", "en")

    if lang not in TRANSLATIONS:
        lang = "en"

    teacher_name = (
        teacher_info["full_name"]
        if dynamic_teacher else teacher_info["name"]
    )
    teacher_flag = teacher_info["flag"]

    day = metadata["day"]
    lesson_time = metadata["time"]
    name = metadata["name"]
    email = metadata["email"]
    phone = metadata.get("phone", "")
    paid_amount_pence = checkout_session.amount_total or 0
    paid_amount = paid_amount_pence / 100

    conn = sqlite3.connect("bookings.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM bookings
        WHERE checkout_session_id = ?
    """, (session_id,))
    already_saved = cursor.fetchone()

    if teacher in ["mike", "michalis"]:
        cursor.execute("""
            SELECT id FROM bookings
            WHERE teacher IN ('mike', 'michalis')
            AND day = ? AND time = ?
        """, (day, lesson_time))
    else:
        cursor.execute("""
            SELECT id FROM bookings
            WHERE teacher = ? AND day = ? AND time = ?
        """, (teacher, day, lesson_time))

    slot_taken = cursor.fetchone()

    if slot_taken and not already_saved:
        conn.close()
        return (
            "Sorry, this lesson slot was booked by another student "
            "while payment was being processed."
        ), 409

    if not already_saved:
        cursor.execute("""
            INSERT INTO bookings
            (
                teacher, day, time, name, email, phone,
                checkout_session_id, email_sent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            teacher, day, lesson_time, name, email, phone,
            session_id, 0
        ))
        conn.commit()

    conn.close()

    owner_email_ok = send_email(
        OWNER_EMAIL,
        f"New Paid Lesson Booking for {teacher_name}",
        f"""New paid booking received:

Teacher: {teacher_name} {teacher_flag}
Student: {name}
Student email: {email}
Student phone: {phone}
Day: {day}
Time: {lesson_time}
Payment: £{paid_amount:.2f}
"""
    )

    student_email_ok = send_email(
        email,
        "Booking Confirmed",
        f"""Hi {name},

Your lesson with {teacher_name} has been booked successfully.

Day: {day}
Time: {lesson_time} UK time
Payment: £{paid_amount:.2f}

If you have any questions, contact: {OWNER_EMAIL}

See you then!
"""
    )

    if dynamic_teacher:
        send_email(
            teacher_info["email"],
            "New Lesson Booked with You",
            f"""Hi {teacher_info['name']},

A student booked a lesson with you.

Student: {name}
Student email: {email}
Student phone: {phone}
Day: {day}
Time: {lesson_time} UK time

You can also see this booking in your teacher dashboard.
"""
        )

    if owner_email_ok and student_email_ok:
        conn = sqlite3.connect("bookings.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE bookings
            SET email_sent = 1
            WHERE checkout_session_id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    return render_template(
        "success.html",
        day=day,
        time=lesson_time,
        teacher=teacher,
        teacher_info=teacher_info,
        lang=lang,
        t=TRANSLATIONS[lang]
    )


@app.route("/become-a-teacher")
def become_a_teacher():
    subjects = [
        ("English", "fa-language"),
        ("Spanish", "fa-language"),
        ("Greek", "fa-language"),
        ("French", "fa-language"),
        ("Maths", "fa-calculator"),
        ("Physics", "fa-atom"),
        ("Dance", "fa-person-running"),
        ("Zumba", "fa-music"),
        ("Chess", "fa-chess"),
        ("Guitar", "fa-guitar"),
        ("Acoustic Guitar", "fa-guitar"),
        ("Electric Piano", "fa-music"),
        ("Violin", "fa-music"),
        ("Singing", "fa-microphone"),
        ("Painting", "fa-palette"),
    ]
    return render_template("teacher_subjects.html", subjects=subjects)




def create_approved_teacher_account(application_id):
    application_conn = sqlite3.connect("teacher_applications.db")
    application_cursor = application_conn.cursor()

    application = application_cursor.execute("""
        SELECT id, subject, name, surname, email, password_hash
        FROM teacher_applications
        WHERE id = ?
    """, (application_id,)).fetchone()

    application_conn.close()

    if not application:
        return None

    app_id, subject, name, surname, email, password_hash = application

    base_slug = secure_filename(
        f"{name}-{surname}"
    ).lower().replace("_", "-")

    if not base_slug:
        base_slug = "teacher"

    teacher_slug = f"{base_slug}-{app_id}"

    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approved_teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            subject TEXT NOT NULL,
            bio TEXT NOT NULL DEFAULT '',
            profile_image TEXT,
            hourly_rate_pence INTEGER NOT NULL DEFAULT 1000,
            timezone TEXT NOT NULL DEFAULT 'Europe/London',
            active INTEGER NOT NULL DEFAULT 1,
            approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            UNIQUE(teacher_id, day),
            FOREIGN KEY (teacher_id)
                REFERENCES approved_teachers(id)
        )
    """)

    existing_teacher = cursor.execute("""
        SELECT id
        FROM approved_teachers
        WHERE application_id = ? OR lower(email) = lower(?)
    """, (app_id, email)).fetchone()

    if existing_teacher:
        cursor.execute("""
            UPDATE approved_teachers
            SET name = ?,
                surname = ?,
                subject = ?,
                password_hash = ?,
                active = 1
            WHERE id = ?
        """, (
            name,
            surname,
            subject,
            password_hash,
            existing_teacher[0],
        ))
        teacher_id = existing_teacher[0]
    else:
        cursor.execute("""
            INSERT INTO approved_teachers
            (
                application_id, slug, name, surname,
                email, password_hash, subject
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id,
            teacher_slug,
            name,
            surname,
            email,
            password_hash,
            subject,
        ))
        teacher_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return teacher_id



PORTAL_TRANSLATIONS = {
    "en": {
        "language_name": "English",
        "become_teacher": "Become a Teacher",
        "choose_subject": "Choose the subject you would like to teach.",
        "back_home": "Back to homepage",
        "back_subjects": "Back to subjects",
        "apply_teach": "Apply to Teach",
        "complete_form": "Complete the form and submit evidence of your teaching ability.",
        "custom_subject": "Subject you want to teach",
        "first_name": "First name",
        "surname": "Surname",
        "email": "Email address",
        "password": "Password",
        "confirm_password": "Confirm password",
        "password_help": "Use at least 8 characters.",
        "proof_required": "Proof required",
        "upload_proof": "Upload your proof",
        "proof_types": "Accepted: PDF, PNG, JPG, JPEG, DOC, DOCX or ODT. Maximum size: 5 MB.",
        "submit_application": "Submit Application",
        "admin_testing": "Admin testing mode is active. A proof file is optional.",
        "add_option": "Add an option",
        "congratulations": "Congratulations",
        "application_received": "Your application has been received.",
        "review_message": "Our team will review your credentials and may get back to you as soon as tomorrow.",
        "share_message": "In the meantime, you can tell your friends that you are applying to teach with LearningXY, so they know where they will be able to book lessons with you.",
        "share_link": "Share this link:",
        "copy": "Copy",
        "copied": "Copied!",
        "social_message": "After your teaching qualifications are approved, we will advertise you and your lessons across our social media pages.",
        "happy_teaching": "Good luck and happy teaching!",
        "return_home": "Return to Homepage",
        "teacher_login": "Teacher Login",
        "login_instructions": "Sign in using the email and password from your application.",
        "login_teacher": "Log In as Teacher",
        "welcome": "Welcome",
        "teacher_word": "teacher",
        "logout": "Log Out",
        "admin_test_mode": "Admin Testing Mode",
        "testing_account": "You are testing this teacher’s account.",
        "stop_testing": "Stop Testing and Return to Admin",
        "your_profile": "Your Profile",
        "profile_picture": "Profile picture",
        "picture_help": "PNG, JPG, JPEG or WEBP. Maximum 5 MB.",
        "qualification": "Qualification",
        "view_qualification": "View Qualification",
        "no_qualification": "No qualification file was uploaded.",
        "price_hour": "Your price per hour",
        "weekly_availability": "Your Weekly Availability",
        "availability_help": "Tick each day you want to teach, then choose your starting and finishing time.",
        "from": "From",
        "until": "Until",
        "save_profile": "Save Profile and Availability",
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
        "teaching_qualification": "Teaching Qualification",
        "back_dashboard": "Back to Dashboard",
        "admin_dashboard": "Teacher Applications",
        "admin_private": "This page is private and visible only after admin login.",
        "test_application": "Test Application",
        "test_teacher": "Test Teacher",
        "applicant": "Applicant",
        "subject": "Subject",
        "proof": "Proof",
        "status": "Status",
        "submitted": "Submitted",
        "action": "Action",
        "view": "View",
        "approved": "Approved",
        "declined": "Declined",
        "pending": "Pending",
    },

    "es": {
        "language_name": "Español",
        "become_teacher": "Hazte profesor",
        "choose_subject": "Elige la asignatura que te gustaría enseñar.",
        "back_home": "Volver a la página principal",
        "back_subjects": "Volver a las asignaturas",
        "apply_teach": "Solicitud para enseñar",
        "complete_form": "Completa el formulario y presenta pruebas de tu capacidad para enseñar.",
        "custom_subject": "Asignatura que deseas enseñar",
        "first_name": "Nombre",
        "surname": "Apellido",
        "email": "Correo electrónico",
        "password": "Contraseña",
        "confirm_password": "Confirmar contraseña",
        "password_help": "Utiliza al menos 8 caracteres.",
        "proof_required": "Documento requerido",
        "upload_proof": "Sube tu documento",
        "proof_types": "Formatos aceptados: PDF, PNG, JPG, JPEG, DOC, DOCX u ODT. Tamaño máximo: 5 MB.",
        "submit_application": "Enviar solicitud",
        "admin_testing": "El modo de prueba de administrador está activo. El documento es opcional.",
        "add_option": "Añadir una opción",
        "congratulations": "¡Enhorabuena",
        "application_received": "Hemos recibido tu solicitud.",
        "review_message": "Nuestro equipo revisará tus credenciales y podría responderte a partir de mañana.",
        "share_message": "Mientras tanto, puedes contarles a tus amigos que has solicitado enseñar con LearningXY para que sepan dónde podrán reservar clases contigo.",
        "share_link": "Comparte este enlace:",
        "copy": "Copiar",
        "copied": "¡Copiado!",
        "social_message": "Una vez aprobadas tus credenciales, anunciaremos tu nombre y tus clases en nuestras redes sociales.",
        "happy_teaching": "¡Buena suerte y feliz enseñanza!",
        "return_home": "Volver a la página principal",
        "teacher_login": "Acceso para profesores",
        "login_instructions": "Inicia sesión con el correo y la contraseña de tu solicitud.",
        "login_teacher": "Iniciar sesión como profesor",
        "welcome": "Bienvenido/a",
        "teacher_word": "profesor/a",
        "logout": "Cerrar sesión",
        "admin_test_mode": "Modo de prueba de administrador",
        "testing_account": "Estás probando la cuenta de este profesor.",
        "stop_testing": "Dejar de probar y volver al administrador",
        "your_profile": "Tu perfil",
        "profile_picture": "Foto de perfil",
        "picture_help": "PNG, JPG, JPEG o WEBP. Máximo 5 MB.",
        "qualification": "Credencial",
        "view_qualification": "Ver credencial",
        "no_qualification": "No se ha subido ningún documento.",
        "price_hour": "Tu precio por hora",
        "weekly_availability": "Tu disponibilidad semanal",
        "availability_help": "Marca los días en los que deseas enseñar y elige las horas de inicio y finalización.",
        "from": "Desde",
        "until": "Hasta",
        "save_profile": "Guardar perfil y disponibilidad",
        "monday": "Lunes",
        "tuesday": "Martes",
        "wednesday": "Miércoles",
        "thursday": "Jueves",
        "friday": "Viernes",
        "saturday": "Sábado",
        "sunday": "Domingo",
        "teaching_qualification": "Credencial docente",
        "back_dashboard": "Volver al panel",
        "admin_dashboard": "Solicitudes de profesores",
        "admin_private": "Esta página es privada y solo puede verse después de iniciar sesión como administrador.",
        "test_application": "Probar solicitud",
        "test_teacher": "Probar profesor",
        "applicant": "Solicitante",
        "subject": "Asignatura",
        "proof": "Documento",
        "status": "Estado",
        "submitted": "Enviado",
        "action": "Acción",
        "view": "Ver",
        "approved": "Aprobada",
        "declined": "Rechazada",
        "pending": "Pendiente",
    },

    "el": {
        "language_name": "Ελληνικά",
        "become_teacher": "Γίνε εκπαιδευτικός",
        "choose_subject": "Επίλεξε το μάθημα που θα ήθελες να διδάξεις.",
        "back_home": "Επιστροφή στην αρχική σελίδα",
        "back_subjects": "Επιστροφή στα μαθήματα",
        "apply_teach": "Αίτηση διδασκαλίας",
        "complete_form": "Συμπλήρωσε τη φόρμα και υπέβαλε αποδεικτικά της διδακτικής σου ικανότητας.",
        "custom_subject": "Μάθημα που θέλεις να διδάξεις",
        "first_name": "Όνομα",
        "surname": "Επώνυμο",
        "email": "Ηλεκτρονική διεύθυνση",
        "password": "Κωδικός πρόσβασης",
        "confirm_password": "Επιβεβαίωση κωδικού",
        "password_help": "Χρησιμοποίησε τουλάχιστον 8 χαρακτήρες.",
        "proof_required": "Απαιτούμενο αποδεικτικό",
        "upload_proof": "Ανέβασε το αποδεικτικό σου",
        "proof_types": "Δεκτά αρχεία: PDF, PNG, JPG, JPEG, DOC, DOCX ή ODT. Μέγιστο μέγεθος: 5 MB.",
        "submit_application": "Υποβολή αίτησης",
        "admin_testing": "Η δοκιμαστική λειτουργία διαχειριστή είναι ενεργή. Το αρχείο είναι προαιρετικό.",
        "add_option": "Προσθήκη επιλογής",
        "congratulations": "Συγχαρητήρια",
        "application_received": "Η αίτησή σου παραλήφθηκε.",
        "review_message": "Η ομάδα μας θα εξετάσει τα προσόντα σου και ενδέχεται να επικοινωνήσει μαζί σου ακόμη και από αύριο.",
        "share_message": "Στο μεταξύ, μπορείς να ενημερώσεις τους φίλους σου ότι έκανες αίτηση για να διδάξεις στο LearningXY, ώστε να γνωρίζουν πού θα μπορούν να κλείσουν μάθημα μαζί σου.",
        "share_link": "Μοιράσου αυτόν τον σύνδεσμο:",
        "copy": "Αντιγραφή",
        "copied": "Αντιγράφηκε!",
        "social_message": "Μετά την έγκριση των προσόντων σου, θα διαφημίσουμε το όνομά σου και τα μαθήματά σου στα μέσα κοινωνικής δικτύωσης.",
        "happy_teaching": "Καλή επιτυχία και καλή διδασκαλία!",
        "return_home": "Επιστροφή στην αρχική σελίδα",
        "teacher_login": "Σύνδεση εκπαιδευτικού",
        "login_instructions": "Συνδέσου με το email και τον κωδικό που χρησιμοποίησες στην αίτηση.",
        "login_teacher": "Σύνδεση ως εκπαιδευτικός",
        "welcome": "Καλώς ήρθες",
        "teacher_word": "εκπαιδευτικός",
        "logout": "Αποσύνδεση",
        "admin_test_mode": "Δοκιμαστική λειτουργία διαχειριστή",
        "testing_account": "Δοκιμάζεις τον λογαριασμό αυτού του εκπαιδευτικού.",
        "stop_testing": "Τέλος δοκιμής και επιστροφή στον διαχειριστή",
        "your_profile": "Το προφίλ σου",
        "profile_picture": "Φωτογραφία προφίλ",
        "picture_help": "PNG, JPG, JPEG ή WEBP. Μέγιστο μέγεθος 5 MB.",
        "qualification": "Προσόν",
        "view_qualification": "Προβολή προσόντος",
        "no_qualification": "Δεν ανέβηκε αρχείο προσόντων.",
        "price_hour": "Η τιμή σου ανά ώρα",
        "weekly_availability": "Η εβδομαδιαία διαθεσιμότητά σου",
        "availability_help": "Επίλεξε τις ημέρες που θέλεις να διδάσκεις και μετά τις ώρες έναρξης και λήξης.",
        "from": "Από",
        "until": "Έως",
        "save_profile": "Αποθήκευση προφίλ και διαθεσιμότητας",
        "monday": "Δευτέρα",
        "tuesday": "Τρίτη",
        "wednesday": "Τετάρτη",
        "thursday": "Πέμπτη",
        "friday": "Παρασκευή",
        "saturday": "Σάββατο",
        "sunday": "Κυριακή",
        "teaching_qualification": "Διδακτικό προσόν",
        "back_dashboard": "Επιστροφή στον πίνακα",
        "admin_dashboard": "Αιτήσεις εκπαιδευτικών",
        "admin_private": "Αυτή η σελίδα είναι ιδιωτική και εμφανίζεται μόνο μετά τη σύνδεση διαχειριστή.",
        "test_application": "Δοκιμή αίτησης",
        "test_teacher": "Δοκιμή εκπαιδευτικού",
        "applicant": "Υποψήφιος",
        "subject": "Μάθημα",
        "proof": "Αποδεικτικό",
        "status": "Κατάσταση",
        "submitted": "Υποβλήθηκε",
        "action": "Ενέργεια",
        "view": "Προβολή",
        "approved": "Εγκρίθηκε",
        "declined": "Απορρίφθηκε",
        "pending": "Σε αναμονή",
    },
}


@app.context_processor
def inject_portal_translations():
    selected_language = request.args.get(
        "lang",
        session.get("portal_language", "en")
    )

    if selected_language not in PORTAL_TRANSLATIONS:
        selected_language = "en"

    if request.args.get("lang") in PORTAL_TRANSLATIONS:
        session["portal_language"] = selected_language

    return {
        "portal_t": PORTAL_TRANSLATIONS[selected_language],
        "portal_lang": selected_language,
        "subject_t": SUBJECT_TRANSLATIONS[selected_language],
    }



SUBJECT_TRANSLATIONS = {
    "en": {
        "English": "English",
        "Spanish": "Spanish",
        "Greek": "Greek",
        "French": "French",
        "Maths": "Maths",
        "Physics": "Physics",
        "Dance": "Dance",
        "Zumba": "Zumba",
        "Chess": "Chess",
        "Guitar": "Guitar",
        "Acoustic Guitar": "Acoustic Guitar",
        "Electric Piano": "Electric Piano",
        "Violin": "Violin",
        "Singing": "Singing",
        "Painting": "Painting",
        "Other": "Other",
    },
    "es": {
        "English": "Inglés",
        "Spanish": "Español",
        "Greek": "Griego",
        "French": "Francés",
        "Maths": "Matemáticas",
        "Physics": "Física",
        "Dance": "Baile",
        "Zumba": "Zumba",
        "Chess": "Ajedrez",
        "Guitar": "Guitarra",
        "Acoustic Guitar": "Guitarra acústica",
        "Electric Piano": "Piano eléctrico",
        "Violin": "Violín",
        "Singing": "Canto",
        "Painting": "Pintura",
        "Other": "Otra asignatura",
    },
    "el": {
        "English": "Αγγλικά",
        "Spanish": "Ισπανικά",
        "Greek": "Ελληνικά",
        "French": "Γαλλικά",
        "Maths": "Μαθηματικά",
        "Physics": "Φυσική",
        "Dance": "Χορός",
        "Zumba": "Zumba",
        "Chess": "Σκάκι",
        "Guitar": "Κιθάρα",
        "Acoustic Guitar": "Ακουστική κιθάρα",
        "Electric Piano": "Ηλεκτρικό πιάνο",
        "Violin": "Βιολί",
        "Singing": "Τραγούδι",
        "Painting": "Ζωγραφική",
        "Other": "Άλλο μάθημα",
    },
}


TEACHER_SUBJECTS = {
    "english": "English",
    "spanish": "Spanish",
    "greek": "Greek",
    "french": "French",
    "maths": "Maths",
    "physics": "Physics",
    "dance": "Dance",
    "zumba": "Zumba",
    "chess": "Chess",
    "guitar": "Guitar",
    "acoustic-guitar": "Acoustic Guitar",
    "electric-piano": "Electric Piano",
    "violin": "Violin",
    "singing": "Singing",
    "painting": "Painting",
    "other": "Other",
}

PROOF_REQUIREMENTS = {
    "chess": "Upload evidence showing a chess rating of at least 1200 ELO.",
    "dance": "Upload a qualification, certificate, professional reference, portfolio or other evidence that you can teach dance.",
    "zumba": "Upload a Zumba qualification, fitness certificate or other evidence that you can teach Zumba.",
}

ALLOWED_PROOF_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "odt"}
MAX_PROOF_SIZE = 5 * 1024 * 1024


def proof_file_allowed(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_PROOF_EXTENSIONS
    )


@app.route("/teacher-application/<subject_slug>", methods=["GET", "POST"])
def teacher_application(subject_slug):
    if subject_slug not in TEACHER_SUBJECTS:
        return redirect("/become-a-teacher")

    subject_name = TEACHER_SUBJECTS[subject_slug]
    proof_requirement = PROOF_REQUIREMENTS.get(
        subject_slug,
        "Upload a relevant diploma, degree, teaching certificate, portfolio or other evidence that you are qualified to teach this subject."
    )
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        surname = request.form.get("surname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        custom_subject = request.form.get("custom_subject", "").strip()
        proof = request.files.get("proof")

        final_subject = custom_subject if subject_slug == "other" else subject_name

        if not name or not surname or not email or not password:
            error = "Please complete every required field."
        elif subject_slug == "other" and not custom_subject:
            error = "Please enter the subject you would like to teach."
        elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Your password must contain at least 8 characters."
        elif password != confirm_password:
            error = "The passwords do not match."
        elif (
            not session.get("admin_logged_in")
            and (not proof or not proof.filename)
        ):
            error = "Please upload proof of your teaching ability."
        elif proof and proof.filename and not proof_file_allowed(proof.filename):
            error = "Proof must be a PDF, image, DOC, DOCX or ODT file."
        elif proof and proof.filename:
            proof.seek(0, os.SEEK_END)
            proof_size = proof.tell()
            proof.seek(0)

            if proof_size > MAX_PROOF_SIZE:
                error = "The proof file must be no larger than 5 MB."

        if not error:
            upload_directory = os.path.join(
                app.root_path, "teacher_application_uploads"
            )
            os.makedirs(upload_directory, exist_ok=True)

            if proof and proof.filename:
                original_filename = secure_filename(proof.filename)
                extension = original_filename.rsplit(".", 1)[1].lower()
                stored_filename = f"{uuid.uuid4().hex}.{extension}"
                proof.save(os.path.join(upload_directory, stored_filename))
                upload_file(PROOF_BUCKET, stored_filename, proof)
            else:
                original_filename = "Admin test — no proof uploaded"
                stored_filename = ""

            conn = sqlite3.connect("teacher_applications.db")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teacher_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    proof_filename TEXT NOT NULL,
                    proof_original_name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO teacher_applications
                (subject, name, surname, email, password_hash,
                 proof_filename, proof_original_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                final_subject,
                name,
                surname,
                email,
                generate_password_hash(password),
                stored_filename,
                original_filename,
            ))
            application_id = cursor.lastrowid
            conn.commit()
            conn.close()

            send_email(
                OWNER_EMAIL,
                f"New Teacher Application: {final_subject}",
                f"""A new teacher application has been submitted.

Application ID: {application_id}
Subject: {final_subject}
Name: {name} {surname}
Email: {email}
Proof file: {original_filename}

The application is waiting for review."""
            )

            return redirect(f"/teacher-application-success?name={name}")

    return render_template(
        "teacher_application.html",
        subject_name=subject_name,
        subject_slug=subject_slug,
        proof_requirement=proof_requirement,
        error=error,
        admin_testing=session.get("admin_logged_in", False),
    )



@app.route("/teacher-application-success")
def teacher_application_success():
    applicant_name = request.args.get("name", "").strip()
    return render_template(
        "teacher_application_success.html",
        applicant_name=applicant_name,
        share_link="https://learningxy.com"
    )



@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect("/admin")

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        username_correct = username == ADMIN_USERNAME
        password_correct = (
            ADMIN_PASSWORD_HASH
            and check_password_hash(ADMIN_PASSWORD_HASH, password)
        )

        if username_correct and password_correct:
            session.clear()
            session["admin_logged_in"] = True
            session.permanent = False
            return redirect("/admin")

        error = "Incorrect username or password."

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")


@app.route("/admin")
@admin_required
def admin_dashboard():
    permanently_remove_expired_applications()

    applications = []
    deleted_applications = []

    if "admin_csrf_token" not in session:
        session["admin_csrf_token"] = uuid.uuid4().hex

    if os.path.exists("teacher_applications.db"):
        ensure_teacher_delete_columns()

        conn = sqlite3.connect("teacher_applications.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        table_exists = cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='teacher_applications'
        """).fetchone()

        if table_exists:
            applications = cursor.execute("""
                SELECT id, subject, name, surname, email,
                       proof_filename, proof_original_name,
                       status, submitted_at
                FROM teacher_applications
                WHERE deleted_at IS NULL
                ORDER BY submitted_at DESC
            """).fetchall()

            deleted_applications = cursor.execute("""
                SELECT id, subject, name, surname, deleted_at
                FROM teacher_applications
                WHERE deleted_at IS NOT NULL
                ORDER BY deleted_at DESC
            """).fetchall()

        conn.close()

    teacher_accounts_by_application = {}

    if os.path.exists("approved_teachers.db"):
        teacher_conn = sqlite3.connect("approved_teachers.db")
        teacher_conn.row_factory = sqlite3.Row
        teacher_cursor = teacher_conn.cursor()

        teacher_rows = teacher_cursor.execute("""
            SELECT id, application_id
            FROM approved_teachers
            WHERE active = 1
        """).fetchall()

        teacher_accounts_by_application = {
            row["application_id"]: row["id"]
            for row in teacher_rows
        }

        teacher_conn.close()

    return render_template(
        "admin_dashboard.html",
        applications=applications,
        deleted_applications=deleted_applications,
        teacher_accounts_by_application=teacher_accounts_by_application,
        csrf_token=session["admin_csrf_token"],
        current_timestamp=int(time.time())
    )


@app.route("/admin/proof/<filename>")
@admin_required
def admin_proof(filename):
    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()
    application = cursor.execute("""
        SELECT id FROM teacher_applications
        WHERE proof_filename = ? AND proof_filename != ''
    """, (filename,)).fetchone()
    conn.close()

    if not application:
        return "Proof file not found.", 404

    try:
        return inline_response(PROOF_BUCKET, filename, filename)
    except Exception:
        return "Proof file not found.", 404



@app.route("/admin/application/<int:application_id>")
@admin_required
def admin_application_detail(application_id):
    conn = sqlite3.connect("teacher_applications.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    application = cursor.execute("""
        SELECT id, subject, name, surname, email,
               proof_filename, proof_original_name,
               status, submitted_at
        FROM teacher_applications
        WHERE id = ?
    """, (application_id,)).fetchone()

    conn.close()

    if not application:
        return "Application not found.", 404

    if "admin_csrf_token" not in session:
        session["admin_csrf_token"] = uuid.uuid4().hex

    teacher_account = None

    if os.path.exists("approved_teachers.db"):
        teacher_conn = sqlite3.connect("approved_teachers.db")
        teacher_conn.row_factory = sqlite3.Row
        teacher_cursor = teacher_conn.cursor()

        teacher_account = teacher_cursor.execute("""
            SELECT id, name, surname, email, subject, active
            FROM approved_teachers
            WHERE application_id = ?
        """, (application_id,)).fetchone()

        teacher_conn.close()

    return render_template(
        "admin_application_detail.html",
        application=application,
        teacher_account=teacher_account,
        csrf_token=session["admin_csrf_token"]
    )


@app.route("/admin/application/<int:application_id>/decision", methods=["POST"])
@admin_required
def admin_application_decision(application_id):
    submitted_token = request.form.get("csrf_token", "")
    saved_token = session.get("admin_csrf_token", "")
    decision = request.form.get("decision", "")

    if not submitted_token or submitted_token != saved_token:
        return "Invalid security token.", 403

    if decision not in {"approved", "declined"}:
        return "Invalid application decision.", 400

    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()

    application = cursor.execute("""
        SELECT name, surname, email, subject
        FROM teacher_applications
        WHERE id = ?
    """, (application_id,)).fetchone()

    if not application:
        conn.close()
        return "Application not found.", 404

    cursor.execute("""
        UPDATE teacher_applications
        SET status = ?
        WHERE id = ?
    """, (decision, application_id))

    conn.commit()
    conn.close()

    if decision == "approved":
        create_approved_teacher_account(application_id)

    return redirect(f"/admin/application/{application_id}")


@app.route("/admin/application/<int:application_id>/proof-viewer")
@admin_required
def admin_proof_viewer(application_id):
    conn = sqlite3.connect("teacher_applications.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    application = cursor.execute("""
        SELECT id, name, surname, subject,
               proof_filename, proof_original_name
        FROM teacher_applications
        WHERE id = ? AND deleted_at IS NULL
    """, (application_id,)).fetchone()

    conn.close()

    if not application or not application["proof_filename"]:
        return "This application has no proof file.", 404

    return render_template(
        "admin_proof_viewer.html",
        application=application
    )


@app.route("/admin/application/<int:application_id>/proof-content")
@admin_required
def admin_proof_content(application_id):
    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()
    application = cursor.execute("""
        SELECT proof_filename
        FROM teacher_applications
        WHERE id = ? AND deleted_at IS NULL
    """, (application_id,)).fetchone()
    conn.close()

    if not application or not application[0]:
        return "Proof file not found.", 404

    try:
        return proof_preview_response(os.path.basename(application[0]))
    except Exception:
        return "Proof file not found.", 404



def temporarily_disable_teacher(application_id):
    if not os.path.exists("approved_teachers.db"):
        return

    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE approved_teachers
        SET active = 0
        WHERE application_id = ?
    """, (application_id,))

    conn.commit()
    conn.close()


def restore_teacher_after_undo(application_id, previous_status):
    if previous_status != "approved":
        return

    if not os.path.exists("approved_teachers.db"):
        return

    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE approved_teachers
        SET active = 1
        WHERE application_id = ?
    """, (application_id,))

    conn.commit()
    conn.close()


def permanently_delete_teacher_account(application_id):
    if not os.path.exists("approved_teachers.db"):
        return

    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT id, profile_image
        FROM approved_teachers
        WHERE application_id = ?
    """, (application_id,)).fetchone()

    if not teacher:
        conn.close()
        return

    teacher_id, profile_image = teacher

    cursor.execute("""
        DELETE FROM teacher_availability
        WHERE teacher_id = ?
    """, (teacher_id,))

    cursor.execute("""
        DELETE FROM approved_teachers
        WHERE id = ?
    """, (teacher_id,))

    conn.commit()
    conn.close()

    if profile_image:
        remove_file(PROFILE_BUCKET, os.path.basename(profile_image))
        image_path = os.path.join(
            app.root_path,
            "static",
            "teacher_profiles",
            os.path.basename(profile_image)
        )

        if os.path.isfile(image_path):
            os.remove(image_path)


def ensure_teacher_delete_columns():
    if not os.path.exists("teacher_applications.db"):
        return

    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()

    table_exists = cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='teacher_applications'
    """).fetchone()

    if table_exists:
        columns = {
            row[1] for row in
            cursor.execute("PRAGMA table_info(teacher_applications)").fetchall()
        }

        if "deleted_at" not in columns:
            cursor.execute("""
                ALTER TABLE teacher_applications
                ADD COLUMN deleted_at INTEGER
            """)

        if "status_before_delete" not in columns:
            cursor.execute("""
                ALTER TABLE teacher_applications
                ADD COLUMN status_before_delete TEXT
            """)

        conn.commit()

    conn.close()


def permanently_remove_expired_applications():
    ensure_teacher_delete_columns()

    if not os.path.exists("teacher_applications.db"):
        return

    expiry_time = int(time.time()) - 60

    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()

    expired = cursor.execute("""
        SELECT id, proof_filename
        FROM teacher_applications
        WHERE deleted_at IS NOT NULL
        AND deleted_at <= ?
    """, (expiry_time,)).fetchall()

    upload_directory = os.path.join(
        app.root_path, "teacher_application_uploads"
    )

    for application_id, proof_filename in expired:
        permanently_delete_teacher_account(application_id)

        if proof_filename:
            stored_proof = os.path.basename(proof_filename)
            remove_file(PROOF_BUCKET, stored_proof)
            proof_path = os.path.join(upload_directory, stored_proof)

            if os.path.isfile(proof_path):
                os.remove(proof_path)

        cursor.execute("""
            DELETE FROM teacher_applications
            WHERE id = ?
        """, (application_id,))

    conn.commit()
    conn.close()


@app.route("/admin/application/<int:application_id>/delete", methods=["POST"])
@admin_required
def admin_delete_application(application_id):
    submitted_token = request.form.get("csrf_token", "")
    saved_token = session.get("admin_csrf_token", "")

    if not submitted_token or submitted_token != saved_token:
        return "Invalid security token.", 403

    ensure_teacher_delete_columns()

    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()

    application = cursor.execute("""
        SELECT status
        FROM teacher_applications
        WHERE id = ? AND deleted_at IS NULL
    """, (application_id,)).fetchone()

    if not application:
        conn.close()
        return "Application not found.", 404

    cursor.execute("""
        UPDATE teacher_applications
        SET status_before_delete = status,
            status = 'pending_delete',
            deleted_at = ?
        WHERE id = ?
    """, (int(time.time()), application_id))

    conn.commit()
    conn.close()

    temporarily_disable_teacher(application_id)

    session.pop("teacher_id", None)
    session.pop("admin_testing_teacher", None)

    return redirect("/admin")


@app.route("/admin/application/<int:application_id>/undo-delete", methods=["POST"])
@admin_required
def admin_undo_delete(application_id):
    submitted_token = request.form.get("csrf_token", "")
    saved_token = session.get("admin_csrf_token", "")

    if not submitted_token or submitted_token != saved_token:
        return "Invalid security token.", 403

    ensure_teacher_delete_columns()

    conn = sqlite3.connect("teacher_applications.db")
    cursor = conn.cursor()

    application = cursor.execute("""
        SELECT deleted_at, status_before_delete
        FROM teacher_applications
        WHERE id = ? AND deleted_at IS NOT NULL
    """, (application_id,)).fetchone()

    if not application:
        conn.close()
        return "Application is no longer available.", 404

    deleted_at, previous_status = application

    if int(time.time()) - deleted_at >= 60:
        conn.close()
        permanently_remove_expired_applications()
        return redirect("/admin")

    cursor.execute("""
        UPDATE teacher_applications
        SET status = ?,
            deleted_at = NULL,
            status_before_delete = NULL
        WHERE id = ?
    """, (previous_status or "pending", application_id))

    conn.commit()
    conn.close()

    restore_teacher_after_undo(
        application_id,
        previous_status or "pending"
    )

    return redirect("/admin")


@app.route("/admin/finish-expired-deletions", methods=["POST"])
@admin_required
def admin_finish_expired_deletions():
    permanently_remove_expired_applications()
    return ("", 204)




def get_teacher_qualification(application_id):
    if not os.path.exists("teacher_applications.db"):
        return None

    conn = sqlite3.connect("teacher_applications.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    qualification = cursor.execute("""
        SELECT proof_filename, proof_original_name
        FROM teacher_applications
        WHERE id = ?
    """, (application_id,)).fetchone()

    conn.close()
    return qualification



def get_approved_teacher_bookings(teacher_slug):
    if not os.path.exists("bookings.db"):
        return []

    conn = sqlite3.connect("bookings.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    table_exists = cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'bookings'
    """).fetchone()

    if not table_exists:
        conn.close()
        return []

    bookings = cursor.execute("""
        SELECT id, day, time, name, email, phone
        FROM bookings
        WHERE teacher = ?
        ORDER BY
            CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
                ELSE 8
            END,
            time
    """, (teacher_slug,)).fetchall()

    conn.close()
    return bookings


def teacher_required(function):
    @wraps(function)
    def protected_teacher_function(*args, **kwargs):
        if not session.get("teacher_id"):
            return redirect("/teacher/login")
        return function(*args, **kwargs)
    return protected_teacher_function


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if session.get("teacher_id"):
        return redirect("/teacher/dashboard")

    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = sqlite3.connect("approved_teachers.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        teacher = cursor.execute("""
            SELECT id, email, password_hash, active
            FROM approved_teachers
            WHERE lower(email) = lower(?)
        """, (email,)).fetchone()

        conn.close()

        if (
            teacher
            and teacher["active"]
            and check_password_hash(teacher["password_hash"], password)
        ):
            session.clear()
            session["teacher_id"] = teacher["id"]
            return redirect("/teacher/dashboard")

        error = "Incorrect email or password, or your account is inactive."

    return render_template("teacher_login.html", error=error)


@app.route("/teacher/logout")
def teacher_logout():
    was_admin = session.get("admin_logged_in", False)

    session.pop("teacher_id", None)
    session.pop("admin_testing_teacher", None)

    if was_admin:
        return redirect("/admin")

    session.clear()
    return redirect("/teacher/login")


@app.route("/teacher/dashboard", methods=["GET", "POST"])
@teacher_required
def teacher_dashboard():
    teacher_id = session["teacher_id"]
    error = None
    message = None

    conn = sqlite3.connect("approved_teachers.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT id, application_id, slug, name, surname, email, subject, bio,
               profile_image, hourly_rate_pence, timezone, active
        FROM approved_teachers
        WHERE id = ? AND active = 1
    """, (teacher_id,)).fetchone()

    if not teacher:
        conn.close()
        session.clear()
        return redirect("/teacher/login")

    if request.method == "POST":
        rate_text = request.form.get("hourly_rate", "").strip()
        bio_text = request.form.get("bio", "").strip()
        profile_image = request.files.get("profile_image")
        qualification_file = request.files.get("qualification_file")
        timezone_name = request.form.get(
            "timezone", teacher["timezone"] or "Europe/London"
        ).strip()

        try:
            hourly_rate = round(float(rate_text), 2)
        except ValueError:
            hourly_rate = 0

        if hourly_rate < 5 or hourly_rate > 200:
            error = "Your hourly price must be between £5 and £200."
        elif len(bio_text) > 2000:
            error = "Your bio must be 2,000 characters or fewer."
        else:
            try:
                ZoneInfo(timezone_name)
            except Exception:
                error = "Please select a valid timezone."

        selected_availability = []

        for day in [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]:
            if request.form.get(f"available_{day}"):
                start_time = request.form.get(
                    f"start_{day}", ""
                ).strip()
                end_time = request.form.get(
                    f"end_{day}", ""
                ).strip()

                if not start_time or not end_time:
                    error = f"Choose both times for {day}."
                    break

                if start_time >= end_time:
                    error = (
                        f"The finishing time for {day} must be "
                        "later than the starting time."
                    )
                    break

                selected_availability.append(
                    (day, start_time, end_time)
                )

        new_image_filename = teacher["profile_image"]

        if profile_image and profile_image.filename:
            original_name = secure_filename(profile_image.filename)
            extension = (
                original_name.rsplit(".", 1)[-1].lower()
                if "." in original_name else ""
            )

            if extension not in {"png", "jpg", "jpeg", "webp"}:
                error = "Profile pictures must be PNG, JPG, JPEG or WEBP."
            else:
                profile_image.seek(0, os.SEEK_END)
                image_size = profile_image.tell()
                profile_image.seek(0)

                if image_size > 5 * 1024 * 1024:
                    error = "The profile picture must be under 5 MB."

        qualification_original_name = None
        qualification_extension = None

        if qualification_file and qualification_file.filename and not error:
            qualification_original_name = secure_filename(
                qualification_file.filename
            )
            qualification_extension = (
                qualification_original_name.rsplit(".", 1)[-1].lower()
                if "." in qualification_original_name else ""
            )

            if qualification_extension not in ALLOWED_PROOF_EXTENSIONS:
                error = (
                    "Qualifications must be PDF, PNG, JPG, JPEG, "
                    "DOC, DOCX or ODT files."
                )
            else:
                qualification_file.seek(0, os.SEEK_END)
                qualification_size = qualification_file.tell()
                qualification_file.seek(0)

                if qualification_size > MAX_PROOF_SIZE:
                    error = "The qualification file must be under 5 MB."

        if not error:
            if qualification_file and qualification_file.filename:
                old_qualification = cursor.execute("""
                    SELECT proof_filename
                    FROM teacher_applications
                    WHERE id = ?
                """, (teacher["application_id"],)).fetchone()

                new_qualification_filename = (
                    f"{uuid.uuid4().hex}.{qualification_extension}"
                )
                upload_file(
                    PROOF_BUCKET,
                    new_qualification_filename,
                    qualification_file,
                )

                cursor.execute("""
                    UPDATE teacher_applications
                    SET proof_filename = ?, proof_original_name = ?
                    WHERE id = ?
                """, (
                    new_qualification_filename,
                    qualification_original_name,
                    teacher["application_id"],
                ))

                if old_qualification and old_qualification[0]:
                    remove_file(
                        PROOF_BUCKET,
                        os.path.basename(old_qualification[0]),
                    )

            if profile_image and profile_image.filename:
                image_directory = os.path.join(
                    app.root_path,
                    "static",
                    "teacher_profiles"
                )
                os.makedirs(image_directory, exist_ok=True)

                new_image_filename = (
                    f"{uuid.uuid4().hex}.{extension}"
                )
                new_image_path = os.path.join(
                    image_directory,
                    new_image_filename
                )
                profile_image.save(new_image_path)
                upload_file(
                    PROFILE_BUCKET,
                    new_image_filename,
                    profile_image,
                )

                old_image = teacher["profile_image"]

                if old_image:
                    remove_file(PROFILE_BUCKET, os.path.basename(old_image))
                    old_image_path = os.path.join(
                        image_directory,
                        os.path.basename(old_image)
                    )

                    if os.path.isfile(old_image_path):
                        os.remove(old_image_path)

            cursor.execute("""
                UPDATE approved_teachers
                SET hourly_rate_pence = ?,
                    profile_image = ?,
                    bio = ?,
                    timezone = ?
                WHERE id = ?
            """, (
                int(round(hourly_rate * 100)),
                new_image_filename,
                bio_text,
                timezone_name,
                teacher_id,
            ))

            cursor.execute("""
                DELETE FROM teacher_availability
                WHERE teacher_id = ?
            """, (teacher_id,))

            for day, start_time, end_time in selected_availability:
                cursor.execute("""
                    INSERT INTO teacher_availability
                    (teacher_id, day, start_time, end_time)
                    VALUES (?, ?, ?, ?)
                """, (
                    teacher_id,
                    day,
                    start_time,
                    end_time,
                ))

            conn.commit()
            message = "Your teacher profile has been updated."

            teacher = cursor.execute("""
                SELECT id, application_id, slug, name, surname, email, subject, bio,
                       profile_image, hourly_rate_pence, timezone, active
                FROM approved_teachers
                WHERE id = ?
            """, (teacher_id,)).fetchone()

    availability_rows = cursor.execute("""
        SELECT day, start_time, end_time
        FROM teacher_availability
        WHERE teacher_id = ?
    """, (teacher_id,)).fetchall()

    conn.close()

    availability = {
        row["day"]: {
            "start": row["start_time"],
            "end": row["end_time"],
        }
        for row in availability_rows
    }

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        availability=availability,
        error=error,
        message=message,
        admin_testing_teacher=session.get(
            "admin_testing_teacher", False
        ),
        qualification=get_teacher_qualification(
            teacher["application_id"]
        ),
        booked_lessons=get_approved_teacher_bookings(
            teacher["slug"]
        ),
        timezone_options=sorted(available_timezones()),
    )



@app.route("/admin/application/<int:application_id>/test-teacher", methods=["POST"])
@admin_required
def admin_test_teacher_from_application(application_id):
    submitted_token = request.form.get("csrf_token", "")
    saved_token = session.get("admin_csrf_token", "")

    if not submitted_token or submitted_token != saved_token:
        return "Invalid security token.", 403

    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT id
        FROM approved_teachers
        WHERE application_id = ? AND active = 1
    """, (application_id,)).fetchone()

    conn.close()

    if not teacher:
        return "Approved teacher account not found.", 404

    session["teacher_id"] = teacher[0]
    session["admin_testing_teacher"] = True

    return redirect("/teacher/dashboard")



@app.route("/admin/teacher/<int:teacher_id>/test-login", methods=["POST"])
@admin_required
def admin_test_as_teacher(teacher_id):
    submitted_token = request.form.get("csrf_token", "")
    saved_token = session.get("admin_csrf_token", "")

    if not submitted_token or submitted_token != saved_token:
        return "Invalid security token.", 403

    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT id
        FROM approved_teachers
        WHERE id = ? AND active = 1
    """, (teacher_id,)).fetchone()

    conn.close()

    if not teacher:
        return "Approved teacher account not found.", 404

    session["teacher_id"] = teacher_id
    session["admin_testing_teacher"] = True

    return redirect("/teacher/dashboard")



@app.route("/admin/stop-teacher-test")
@admin_required
def admin_stop_teacher_test():
    session.pop("teacher_id", None)
    session.pop("admin_testing_teacher", None)
    return redirect("/admin")



@app.route("/teacher/qualification")
@teacher_required
def teacher_qualification_viewer():
    teacher_id = session["teacher_id"]

    conn = sqlite3.connect("approved_teachers.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT id, application_id, name, surname, subject
        FROM approved_teachers
        WHERE id = ? AND active = 1
    """, (teacher_id,)).fetchone()

    conn.close()

    if not teacher:
        return "Teacher account not found.", 404

    qualification = get_teacher_qualification(
        teacher["application_id"]
    )

    if not qualification or not qualification["proof_filename"]:
        return "No qualification file was uploaded.", 404

    return render_template(
        "teacher_qualification_viewer.html",
        teacher=teacher,
        qualification=qualification
    )


@app.route("/teacher/qualification-content")
@teacher_required
def teacher_qualification_content():
    teacher_id = session["teacher_id"]
    conn = sqlite3.connect("approved_teachers.db")
    cursor = conn.cursor()
    teacher = cursor.execute("""
        SELECT application_id
        FROM approved_teachers
        WHERE id = ? AND active = 1
    """, (teacher_id,)).fetchone()
    conn.close()

    if not teacher:
        return "Teacher account not found.", 404

    qualification = get_teacher_qualification(teacher[0])
    if not qualification or not qualification["proof_filename"]:
        return "No qualification file was uploaded.", 404

    try:
        return proof_preview_response(
            os.path.basename(qualification["proof_filename"])
        )
    except Exception:
        return "Qualification file not found.", 404


SUPPORT_TRANSLATIONS = {
    "en": {
        "page_title": "Customer Support",
        "heading": "How can we help?",
        "intro": "Send us a message and our team will get back to you by email.",
        "email": "Your email address",
        "message": "How can we help you?",
        "send": "Send Message",
        "home": "Return to Homepage",
        "success": "Thank you. Your message has been sent to our team.",
        "error": "Please enter a valid email address and a message.",
    },
    "es": {
        "page_title": "Atención al cliente",
        "heading": "¿Cómo podemos ayudarte?",
        "intro": "Envíanos un mensaje y nuestro equipo te responderá por correo electrónico.",
        "email": "Tu correo electrónico",
        "message": "¿Cómo podemos ayudarte?",
        "send": "Enviar mensaje",
        "home": "Volver a la página principal",
        "success": "Gracias. Tu mensaje ha sido enviado a nuestro equipo.",
        "error": "Introduce un correo electrónico válido y un mensaje.",
    },
    "el": {
        "page_title": "Υποστήριξη πελατών",
        "heading": "Πώς μπορούμε να βοηθήσουμε;",
        "intro": "Στείλε μας ένα μήνυμα και η ομάδα μας θα σου απαντήσει μέσω email.",
        "email": "Η διεύθυνση email σου",
        "message": "Πώς μπορούμε να σε βοηθήσουμε;",
        "send": "Αποστολή μηνύματος",
        "home": "Επιστροφή στην αρχική σελίδα",
        "success": "Ευχαριστούμε. Το μήνυμά σου στάλθηκε στην ομάδα μας.",
        "error": "Συμπλήρωσε ένα έγκυρο email και ένα μήνυμα.",
    },
}


def ensure_customer_support_table():
    conn = sqlite3.connect("customer_support.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            admin_reply TEXT,
            status TEXT NOT NULL DEFAULT 'unread',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            replied_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


@app.route("/customer-support", methods=["GET", "POST"])
def customer_support():
    lang = request.values.get("lang", "en")
    if lang not in SUPPORT_TRANSLATIONS:
        lang = "en"

    support_t = SUPPORT_TRANSLATIONS[lang]
    error = None
    success_message = None
    submitted_email = ""
    submitted_message = ""

    if request.method == "POST":
        submitted_email = request.form.get("email", "").strip().lower()
        submitted_message = request.form.get("message", "").strip()

        email_is_valid = (
            "@" in submitted_email
            and "." in submitted_email.rsplit("@", 1)[-1]
            and len(submitted_email) <= 254
        )

        if not email_is_valid or not submitted_message:
            error = support_t["error"]
        elif len(submitted_message) > 5000:
            error = support_t["error"]
        else:
            ensure_customer_support_table()
            conn = sqlite3.connect("customer_support.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customer_messages (email, message)
                VALUES (?, ?)
            """, (submitted_email, submitted_message))
            conn.commit()
            conn.close()

            try:
                if OWNER_EMAIL:
                    send_email(
                        OWNER_EMAIL,
                        "New LearningXY Customer Support Message",
                        f"""A new customer support message was received.

Customer email: {submitted_email}

Message:
{submitted_message}

Sign in to the LearningXY admin dashboard to reply.
"""
                    )
            except Exception:
                pass

            success_message = support_t["success"]
            submitted_email = ""
            submitted_message = ""

    return render_template(
        "customer_support.html",
        lang=lang,
        support_t=support_t,
        error=error,
        success_message=success_message,
        submitted_email=submitted_email,
        submitted_message=submitted_message,
    )


@app.route("/admin/customer-messages")
@admin_required
def admin_customer_messages():
    ensure_customer_support_table()

    if "admin_csrf_token" not in session:
        session["admin_csrf_token"] = uuid.uuid4().hex

    conn = sqlite3.connect("customer_support.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    messages = cursor.execute("""
        SELECT id, email, message, admin_reply, status,
               created_at, replied_at
        FROM customer_messages
        ORDER BY created_at DESC, id DESC
    """).fetchall()
    conn.close()

    return render_template(
        "admin_customer_messages.html",
        messages=messages,
        csrf_token=session["admin_csrf_token"],
        result=request.args.get("result"),
    )


@app.route("/admin/customer-messages/<int:message_id>/reply", methods=["POST"])
@admin_required
def admin_reply_customer_message(message_id):
    submitted_token = request.form.get("csrf_token", "")
    saved_token = session.get("admin_csrf_token", "")

    if not saved_token or submitted_token != saved_token:
        return "Invalid security token.", 403

    reply_text = request.form.get("reply", "").strip()
    if not reply_text or len(reply_text) > 5000:
        return redirect("/admin/customer-messages?result=invalid")

    ensure_customer_support_table()
    conn = sqlite3.connect("customer_support.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    customer_message = cursor.execute("""
        SELECT id, email, message
        FROM customer_messages
        WHERE id = ?
    """, (message_id,)).fetchone()

    if not customer_message:
        conn.close()
        return "Customer message not found.", 404

    email_sent = False
    try:
        email_sent = bool(send_email(
            customer_message["email"],
            "Reply from LearningXY Customer Support",
            f"""Hello,

Thank you for contacting LearningXY.

{reply_text}

Kind regards,
LearningXY Customer Support
"""
        ))
    except Exception:
        email_sent = False

    if not email_sent:
        conn.close()
        return redirect("/admin/customer-messages?result=email-failed")

    cursor.execute("""
        UPDATE customer_messages
        SET admin_reply = ?, status = 'replied',
            replied_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (reply_text, message_id))
    conn.commit()
    conn.close()

    return redirect("/admin/customer-messages?result=replied")


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
