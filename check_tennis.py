import sys
import subprocess
import os
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Авто-инсталатор, щото си пълен аджамия и мързелът е skibidi toilet ниво!
def install_packages():
    packages = ['requests', 'beautifulsoup4', 'cloudscraper']
    for pkg in packages:
        try:
            if pkg == 'beautifulsoup4':
                import bs4
            else:
                __import__(pkg)
        except ImportError:
            print(f"⚠️ Мамка му човече, липсва {pkg}! Батко чатко инсталира автоматично...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_packages()

import cloudscraper
from bs4 import BeautifulSoup

# Вземай пътя до папката за запис на JSON файлчето, както искаше
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

def send_email(subject, body_text, event_url):
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    
    # Списък с всички получатели (включително ония двама палавници)
    receivers = [
        sender, 
        "miroslavkichukov.mmk@gmail.com", 
        "eva.trifonova@gmail.com"
    ]

    if not sender or not password:
        print("❌ Няма въведени credentials! Андибул морков! Провери си GitHub Secrets, боклуче!")
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
            print(f"✅ Успешно изпратени мейлчовци до {len(receivers)} льольовци.")
    except Exception as e:
        print(f"❌ What the fuck, грешка при изпращане на имейл: {e}")

def check_tennis_events():
    url = "https://www.eventim.bg/events/%D1%81%D0%BF%D0%BE%D1%80%D1%82-292/%D1%82%D0%B5%D0%BD%D0%B8%D1%81-2879/"
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    
    try:
        print("🔎 Проверявам Eventim за тенис билети...")
        response = scraper.get(url, timeout=20)
        response.raise_for_status()
        html_text = response.text
    except Exception as e:
        print(f"❌ What the fuck, грешка при връзката със сайта: {e}")
        
        error_file = os.path.join(output_dir, "error_log.txt")
        with open(error_file, "w", encoding="utf-8") as f:
            f.write(f"Грешка при заявката:\n{str(e)}")
            
        if hasattr(e, 'response') and e.response is not None:
            dump_file = os.path.join(output_dir, "error_dump.html")
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(e.response.text)
            print(f"💾 Записах ти 'скриншот' (HTML дъмп) в {dump_file}!")
            
        return

    # Защита от тихия Cloudflare блок (да не стане паприкаш)
    if "eventim.bg" not in html_text.lower() and "резултати" not in html_text.lower():
        print("❌ Мамка му човече, Cloudflare ни нацепи канчето! Блокирани сме и виждаме само капчи!")
        dump_file = os.path.join(output_dir, "error_dump.html")
        with open(dump_file, "w", encoding="utf-8") as f:
            f.write(html_text)
        print(f"💾 Записах ти 'скриншот' (HTML дъмп) в {dump_file}, да си го дебъгваш!")
        return

    # Търсим текста "Намерени X резултати"
    current_events = 0
    match = re.search(r'Намерени\s+(\d+)\s+резултат[и]?', html_text, re.IGNORECASE)
    
    if match:
        current_events = int(match.group(1))
    else:
        # Резервен вариант, ако малини, къпини, все тая - търсиме картичките
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

    # Пращаме имейл САМО ако бройката се е увеличила
    if current_events != last_events:
        if current_events > 0 and current_events > last_events:
            print("🔥 РАЗБИРААЙ! Има нови събития! Подготвям мейлчето...")
            
            body = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="background-color: #2ed573; padding: 20px; text-align: center; color: white;">
                        <h2 style="margin: 0; font-size: 24px;">🎾 Нови Тенис Събития, Гащник!</h2>
                    </div>
                    <div style="padding: 25px; font-size: 16px; color: #333;">
                        <p>Йо шефе как си днес! Засечена е промяна в броя на тенис събитията в Eventim. Вземай портмонето и бегай!</p>
                        <ul style="line-height: 1.8; font-size: 18px;">
                            <li><b>Предишен брой:</b> {last_events}</li>
                            <li><b style="color: #ff4757;">Нов брой:</b> {current_events}</li>
                        </ul>
                        <div style="text-align: center; margin-top: 30px;">
                            <a href="{url}" style="background-color: #ff4757; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">🔗 Отвори Eventim и купувай</a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            send_email("🎾 ВНИМАНИЕ: Пуснаха билети за ТЕНИС в Eventim!", body, url)
        else:
            print("😴 Промяна има, но е надолу или 0. Спестяваме спама на тия скриптчовци.")
            
        # Записваме новото състояние
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"count": current_events}, f, ensure_ascii=False, indent=4)
    else:
        print("Без промяна. Пазарът е застинал като умрял кон.")

if __name__ == "__main__":
    check_tennis_events()
