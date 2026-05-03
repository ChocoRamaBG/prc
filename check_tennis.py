import sys
import subprocess
import os
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Авто-инсталатор, за да няма гръмнали пакети в GitHub Actions
def install_packages():
    packages = ['requests', 'beautifulsoup4', 'cloudscraper']
    for pkg in packages:
        try:
            if pkg == 'beautifulsoup4':
                import bs4
            else:
                __import__(pkg)
        except ImportError:
            print(f"⚠️ Липсва {pkg}! Инсталирам автоматично...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_packages()

import cloudscraper
from bs4 import BeautifulSoup

# Взимаме пътя до папката за запис на JSON файла
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

def send_email(subject, body_text, event_url):
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    
    # Списък с всички получатели
    receivers = [
        sender, 
        "miroslavkichukov.mmk@gmail.com", 
        "eva.trifonova@gmail.com"
    ]

    if not sender or not password:
        print("❌ Няма въведени credentials! Провери си GitHub Secrets!")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ", ".join(receivers)

    msg.attach(MIMEText(body_text, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receivers, msg.as_string())
            print(f"✅ Успешно изпратен имейл до {len(receivers)} получатели.")
    except Exception as e:
        print(f"❌ Грешка при изпращане на имейл: {e}")

def check_tennis_events():
    url = "https://www.eventim.bg/events/%D1%81%D0%BF%D0%BE%D1%80%D1%82-292/%D1%82%D0%B5%D0%BD%D0%B8%D1%81-2879/"
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    
    try:
        print("🔎 Проверявам Eventim за тенис билети...")
        response = scraper.get(url, timeout=20)
        response.raise_for_status()
        html_text = response.text
    except Exception as e:
        print(f"❌ Грешка при връзката със сайта: {e}")
        return

    # Търсим текста "Намерени X резултат(а)"
    current_events = 0
    match = re.search(r'Намерени\s+(\d+)\s+резултат', html_text, re.IGNORECASE)
    
    if match:
        current_events = int(match.group(1))
    else:
        # Резервен вариант, ако HTML-ът се зареди динамично - търсим броя на самите картички на събития
        soup = BeautifulSoup(html_text, 'html.parser')
        events = soup.select('product-item')
        current_events = len(events)

    state_file = os.path.join(output_dir, "tennis_state.json")
    last_events = 0
    
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_events = data.get("count", 0)
        except: 
            pass

    print(f"Текущи събития: {current_events} (Предишни: {last_events})")

    # Пращаме имейл САМО ако бройката се е увеличила и е повече от 0
    if current_events != last_events:
        if current_events > 0 and current_events > last_events:
            print("🔥 Има нови събития! Подготвям имейла...")
            
            body = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="background-color: #2ed573; padding: 20px; text-align: center; color: white;">
                        <h2 style="margin: 0; font-size: 24px;">🎾 Нови Тенис Събития!</h2>
                    </div>
                    <div style="padding: 25px; font-size: 16px; color: #333;">
                        <p>Засечена е промяна в броя на тенис събитията в Eventim.</p>
                        <ul style="line-height: 1.8; font-size: 18px;">
                            <li><b>Предишен брой:</b> {last_events}</li>
                            <li><b style="color: #ff4757;">Нов брой:</b> {current_events}</li>
                        </ul>
                        <div style="text-align: center; margin-top: 30px;">
                            <a href="{url}" style="background-color: #ff4757; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">🔗 Отвори Eventim</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            send_email("🎾 ВНИМАНИЕ: Пуснаха билети за ТЕНИС в Eventim!", body, url)
        else:
            print("😴 Промяна има, но е надолу или 0. Спестяваме спама.")
            
        # Записваме новото състояние
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"count": current_events}, f, ensure_ascii=False, indent=4)
    else:
        print("Без промяна. Пазарът е застинал.")

if __name__ == "__main__":
    check_tennis_events()
