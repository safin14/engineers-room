from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from supabase import create_client
from datetime import date, datetime
from zoneinfo import ZoneInfo
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
import secrets
import os

print(os.getcwd())
import firebase_admin 
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
load_dotenv()


supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

try:
    test = supabase.table("users").select("*").limit(1).execute()
    print("Supabase Connected")
except Exception as e:
    print("Supabase Error:", e)




app = Flask(__name__)


cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

app.secret_key = "engineers_room_secret_key_123"



app.permanent_session_lifetime = timedelta(days=30)


app.config["SESSION_COOKIE_SECURE"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

import requests

BOT_TOKEN = "8889835818:AAGAL-r8TBxB6raO2Y08Qy-XZXtR-1vUL7s"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text
    }

    requests.post(url, data=data)


def send_daily_reminder():
    members = supabase.table("telegram_members").select("chat_id").execute()

    for member in members.data:
        send_message(
            member["chat_id"],
            """🍽️ ENGINEERS ROOM

⏰ Meal Entry Reminder

আজকের meal entry এখনো করা হয়নি।
দয়া করে আপনার meal entry সম্পন্ন করুন।

✅ Breakfast
✅ Lunch
✅ Dinner

ধন্যবাদ।"""
        )

    print("Daily reminder sent.")
    

scheduler = BackgroundScheduler()

scheduler.add_job(
    func=send_daily_reminder,
    trigger="cron",
    hour=9,
    minute=0,
    timezone="Asia/Dhaka"
)
scheduler.start()

BOT_TOKEN = "8889835818:AAGAL-r8TBxB6raO2Y08Qy-XZXtR-1vUL7s"
CHAT_ID = "7534627531"

SUPABASE_URL = "https://cxnnikxpljcatpxmifoa.supabase.co"
SUPABASE_KEY = "sb_publishable_gPPDgfTthPSdnV70yHpwDw_9iDmTEPg"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=data)

def init_db():
    # Supabase handles database tables now
    pass

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]


        response = supabase.table("users")\
            .select("*")\
            .eq("name", username)\
            .eq("password", password)\
            .execute()


        user = response.data[0] if response.data else None


        if user:

            token = secrets.token_hex(32)


            supabase.table("users")\
                .update({
                    "token": token
                })\
                .eq("id", user["id"])\
                .execute()


            session.permanent = True
            session["user_id"] = user["id"]
            session["role"] = user["role"]


            print("Login Token:", token)


            return redirect("/dashboard")


        else:

            return "Wrong Username or Password"


    return render_template("login.html")

@app.route("/save-token", methods=["POST"])
def save_token():

    data = request.json
    token = data.get("token")

    if not token:
        return {"status": "no token"}

    supabase.table("fcm_tokens").insert({
        "token": token
    }).execute()

    return {"status": "saved"}

@app.route("/dashboard")
def dashboard():

    print("DASHBOARD SESSION:", dict(session))

    if "user_id" not in session:
        return redirect("/login")

    today = datetime.now(ZoneInfo("Asia/Dhaka")).date()
    today_display = today.strftime("%d-%m-%y")
    today = today.isoformat()

    # Total Members
    members_response = supabase.table("members").select("id", count="exact").execute()
    total_members = members_response.count or 0


    # Today's meals
    meals_today = supabase.table("meals")\
        .select("*")\
        .eq("date", today)\
        .execute()

    meals_data = meals_today.data or []


    today_morning = sum(item.get("morning", 0) for item in meals_data)
    today_night = sum(item.get("night", 0) for item in meals_data)
    today_meals = today_morning + today_night


    # Morning done
    morning_done = len([
        item for item in meals_data
        if item.get("morning", 0) > 0
    ])

    morning_pending = total_members - morning_done


    # Night done
    night_done = len([
        item for item in meals_data
        if item.get("night", 0) > 0
    ])

    night_pending = total_members - night_done


    # Total Payment
    payments_response = supabase.table("payments")\
        .select("amount")\
        .execute()

    payments_data = payments_response.data or []

    total_payment = sum(
        item.get("amount", 0)
        for item in payments_data
    )


    # Total Meal
    all_meals = supabase.table("meals")\
        .select("morning, night")\
        .execute()

    all_meals_data = all_meals.data or []

    total_meal = sum(
        item.get("morning", 0) + item.get("night", 0)
        for item in all_meals_data
    )


    meal_rate = 0
    if total_meal > 0:
        meal_rate = total_payment / total_meal


    # Notice
    notice_response = supabase.table("notice")\
        .select("message")\
        .eq("id", 1)\
        .execute()

    notice = ""

    if notice_response.data:
        notice = notice_response.data[0]["message"]


    return render_template(
        "dashboard.html",
        total_members=total_members,
        today_meals=today_meals,
        today_morning=today_morning,
        today_night=today_night,
        total_payment=total_payment,
        total_meal=total_meal,
        meal_rate=round(meal_rate, 2),
        morning_done=morning_done,
        morning_pending=morning_pending,
        night_done=night_done,
        night_pending=night_pending,
        today=today_display,
        notice=notice,
        role=session["role"]
    )

@app.route("/update_notice", methods=["POST"])
def update_notice():

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    notice = request.form["notice"]


    supabase.table("notice")\
        .update({
            "message": notice
        })\
        .eq("id", 1)\
        .execute()


    return redirect(url_for("dashboard"))

@app.route("/members")
def members():

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    response = supabase.table("members")\
        .select("*")\
        .execute()

    members = response.data or []


    return render_template(
        "members.html",
        members=members
    )


@app.route("/add_member", methods=["POST"])
def add_member():

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    name = request.form["name"]
    password = request.form["password"]


    # Add member table
    supabase.table("members").insert({
        "name": name
    }).execute()


    # Add user login
    supabase.table("users").insert({
        "name": name,
        "password": password,
        "role": "member"
    }).execute()


    return redirect("/members")


@app.route("/edit_member/<int:id>", methods=["GET", "POST"])
def edit_member(id):

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    if request.method == "POST":

        name = request.form["name"]


        supabase.table("members")\
            .update({
                "name": name
            })\
            .eq("id", id)\
            .execute()


        return redirect("/members")


    response = supabase.table("members")\
        .select("*")\
        .eq("id", id)\
        .execute()


    member = None

    if response.data:
        member = response.data[0]


    return render_template(
        "edit_member.html",
        member=member
    )

@app.route("/delete_member/<int:id>")
def delete_member(id):

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    # Delete member
    supabase.table("members")\
        .delete()\
        .eq("id", id)\
        .execute()


    return redirect("/members")

@app.route("/payment", methods=["GET", "POST"])
def payment():

    if "user_id" not in session:
        return redirect("/login")


    # Only admin can add payment
    if request.method == "POST":

        if session.get("role") != "admin":
            return "Access Denied"


        member_id = request.form["member_id"]
        amount = request.form["amount"]
        payment_date = request.form["date"]


        member_response = supabase.table("members")\
            .select("name")\
            .eq("id", member_id)\
            .execute()


        if member_response.data:

            name = member_response.data[0]["name"]


            supabase.table("payments").insert({
                "name": name,
                "amount": amount,
                "date": payment_date
            }).execute()


        return redirect("/payment")


    members_response = supabase.table("members")\
        .select("*")\
        .execute()

    members = members_response.data or []


    payments_response = supabase.table("payments")\
        .select("*")\
        .order("id", desc=True)\
        .execute()

    payments = payments_response.data or []


    return render_template(
        "payment.html",
        members=members,
        payments=payments,
        role=session["role"]
    )



@app.route("/edit_payment/<int:id>", methods=["GET", "POST"])
def edit_payment(id):

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    if request.method == "POST":

        amount = request.form["amount"]


        supabase.table("payments")\
            .update({
                "amount": amount
            })\
            .eq("id", id)\
            .execute()


        return redirect("/payment")


    response = supabase.table("payments")\
        .select("*")\
        .eq("id", id)\
        .execute()


    payment = None

    if response.data:
        payment = response.data[0]


    return render_template(
        "edit_payment.html",
        payment=payment
    )

@app.route("/delete_payment/<int:id>")
def delete_payment(id):

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    supabase.table("payments")\
        .delete()\
        .eq("id", id)\
        .execute()


    return redirect("/payment")

@app.route("/meal", methods=["GET", "POST"])
def meal():

    if "user_id" not in session:
        return redirect("/login")


    if request.method == "POST":

        member_id = request.form["member_id"]
        morning = int(request.form.get("morning", 0))
        night = int(request.form.get("night", 0))
        meal_date = request.form["date"]


        member_response = supabase.table("members")\
            .select("name")\
            .eq("id", member_id)\
            .execute()


        if member_response.data:

            name = member_response.data[0]["name"]


            supabase.table("meals").insert({

                "name": name,
                "morning": morning,
                "night": night,
                "date": meal_date

            }).execute()


        return redirect("/meal")



    members_response = supabase.table("members")\
        .select("*")\
        .execute()

    members = members_response.data or []



    meals_response = supabase.table("meals")\
        .select("id, name, morning, night, date")\
        .order("id", desc=True)\
        .execute()

    meals = meals_response.data or []



    return render_template(
        "meal.html",
        members=members,
        meals=meals,
        role=session["role"]
    )

@app.route("/edit_meal/<int:id>", methods=["GET", "POST"])
def edit_meal(id):

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    if request.method == "POST":

        morning = request.form["morning"]
        night = request.form["night"]

        supabase.table("meals")\
            .update({
                "morning": morning,
                "night": night
            })\
            .eq("id", id)\
            .execute()

        return redirect("/meal")


    response = supabase.table("meals")\
        .select("*")\
        .eq("id", id)\
        .execute()

    meal = response.data[0] if response.data else None


    return render_template(
        "edit_meal.html",
        meal=meal
    )


@app.route("/delete_meal/<int:id>")
def delete_meal(id):

    if "role" not in session or session["role"] != "admin":
        return "Access Denied"


    supabase.table("meals")\
        .delete()\
        .eq("id", id)\
        .execute()


    return redirect("/meal")


@app.route("/summary")
def summary():

    if "user_id" not in session:
        return redirect("/login")

    payment_response = supabase.table("payments")\
        .select("name, amount")\
        .execute()

    meal_response = supabase.table("meals")\
        .select("name, morning, night")\
        .execute()


    payments = {}

    for item in payment_response.data or []:
        payments[item["name"]] = payments.get(item["name"], 0) + item["amount"]


    meals = {}

    for item in meal_response.data or []:
        meals[item["name"]] = meals.get(item["name"], 0) + item["morning"] + item["night"]


    total_payment = sum(payments.values())
    total_meal = sum(meals.values())


    meal_rate = total_payment / total_meal if total_meal else 0


    all_names = set(payments.keys()) | set(meals.keys())


    members = []

    for name in all_names:

        payment = payments.get(name, 0)
        meal = meals.get(name, 0)

        cost = meal * meal_rate
        balance = payment - cost

        members.append({
            "name": name,
            "payment": payment,
            "meal": meal,
            "cost": round(cost, 2),
            "balance": round(balance, 2)
        })


    return render_template(
        "summary.html",
        total_payment=total_payment,
        total_meal=total_meal,
        meal_rate=round(meal_rate, 2),
        members=members
    )

@app.route("/member", methods=["POST"])
def member():

    if "role" not in session or session["role"] != "member":
        return "Access Denied"

    user_id = session["user_id"]

    user_response = supabase.table("users")\
        .select("name")\
        .eq("id", user_id)\
        .execute()

    if not user_response.data:
        return "User not found"

    name = user_response.data[0]["name"]

    morning = int(request.form.get("morning", 0))
    night = int(request.form.get("night", 0))
    meal_date = request.form["date"]

    supabase.table("meals").insert({
        "name": name,
        "morning": morning,
        "night": night,
        "date": meal_date
    }).execute()

    return redirect("/dashboard")
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def index():
    return redirect(url_for("login"))
@app.route("/profile/<int:id>")
def profile(id):

    member_response = supabase.table("members")\
        .select("*")\
        .eq("id", id)\
        .execute()

    if not member_response.data:
        return "Member not found"

    member = member_response.data[0]
    name = member["name"]


    # Total Payment
    payment_response = supabase.table("payments")\
        .select("amount, date")\
        .eq("name", name)\
        .order("date", desc=True)\
        .execute()


    payment_history = payment_response.data or []


    total_payment = sum(
        p["amount"] for p in payment_history
    )


    # Total Meal
    meal_response = supabase.table("meals")\
        .select("morning, night, date")\
        .eq("name", name)\
        .order("date", desc=True)\
        .execute()


    meal_history = meal_response.data or []


    total_meal = sum(
        m["morning"] + m["night"]
        for m in meal_history
    )


    # Overall meal rate
    all_payment_response = supabase.table("payments")\
        .select("amount")\
        .execute()

    all_payment = sum(
        p["amount"] for p in all_payment_response.data or []
    )


    all_meal_response = supabase.table("meals")\
        .select("morning, night")\
        .execute()

    all_meal = sum(
        m["morning"] + m["night"]
        for m in all_meal_response.data or []
    )


    meal_rate = all_payment / all_meal if all_meal else 0


    meal_cost = total_meal * meal_rate

    balance = total_payment - meal_cost


    return render_template(
        "profile.html",
        member=member,
        total_payment=total_payment,
        total_meal=total_meal,
        meal_rate=round(meal_rate, 2),
        meal_cost=round(meal_cost, 2),
        balance=round(balance, 2),
        payment_history=payment_history,
        meal_history=meal_history
    )

@app.route("/download_pdf")
def download_pdf():

    payments_response = supabase.table("payments")\
        .select("name, amount")\
        .execute()

    meals_response = supabase.table("meals")\
        .select("name, morning, night")\
        .execute()


    payment_data = {}

    for p in payments_response.data or []:
        payment_data[p["name"]] = payment_data.get(p["name"], 0) + p["amount"]


    meal_data = {}

    for m in meals_response.data or []:
        meal_data[m["name"]] = meal_data.get(m["name"], 0) + m["morning"] + m["night"]


    total_payment = sum(payment_data.values())
    total_meal = sum(meal_data.values())

    meal_rate = total_payment / total_meal if total_meal else 0


    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from flask import send_file
    import os


    pdf_path = os.path.join(app.root_path, "ENGINEERS_ROOM_Report.pdf")


    pdf = SimpleDocTemplate(pdf_path)

    styles = getSampleStyleSheet()


    elements = []

    elements.append(
        Paragraph("ENGINEERS ROOM REPORT", styles["Heading1"])
    )


    elements.append(
        Paragraph(f"Total Payment: {total_payment}", styles["Normal"])
    )

    elements.append(
        Paragraph(f"Total Meal: {total_meal}", styles["Normal"])
    )

    elements.append(
        Paragraph(f"Meal Rate: {meal_rate:.2f}", styles["Normal"])
    )


    data = [
        ["Name", "Payment", "Meal", "Cost", "Balance"]
    ]


    names = set(payment_data.keys()) | set(meal_data.keys())


    for name in names:

        payment = payment_data.get(name,0)
        meal = meal_data.get(name,0)

        cost = meal * meal_rate
        balance = payment - cost

        data.append([
            name,
            payment,
            meal,
            round(cost,2),
            round(balance,2)
        ])


    table = Table(data)

    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black)
    ]))


    elements.append(table)


    pdf.build(elements)


    return send_file(
        pdf_path,
        as_attachment=True
    )

@app.route("/telegram-test")
def telegram_test():
    send_telegram_message("""🍽️ ENGINEERS ROOM

⏰ Meal Entry Reminder

আজকের meal entry এখনো করা হয়নি।
দয়া করে আপনার meal entry সম্পন্ন করুন।

✅ Breakfast
✅ Lunch
✅ Dinner

ধন্যবাদ।""")
    return "Telegram message sent"

@app.route("/test")
def test():
    members = supabase.table("telegram_members").select("chat_id").execute()

    for member in members.data:
        send_message(
            member["chat_id"],
            "🍽️ TEST REMINDER\n\nআজকের meal entry করুন।"
        )

        

    return "Test message sent"



if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
