import sys
import subprocess
import os
import argparse
import smtplib
import time
import datetime
from email.mime.text import MIMEText

# Auto-installer for necessary packages
def install_packages():
    packages = ['requests', 'beautifulsoup4', 'cloudscraper']
    for pkg in packages:
        try:
            if pkg == 'beautifulsoup4':
                import bs4
            else:
                __import__(pkg)
        except ImportError:
            print(f"⚠️ Installing missing package: {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_packages()

import cloudscraper
from bs4 import BeautifulSoup

# Define output directory
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

# Configuration
TARGET_URL = "https://www.quanloop.com/" 

# Comprehensive array of critical keywords indicating financial distress
CRITICAL_KEYWORDS = [
    "withdrawal limit", "withdrawal limits", "withdrawals suspended", 
    "withdrawals paused", "withdrawals halted", "withdrawals delayed",
    "delayed", "delay", "temporary suspension", "temporarily suspended", 
    "frozen", "funds frozen", "account frozen", "pending review", 
    "queuing", "liquidity issue", "liquidity constraint", 
    "payment disruption", "payment gateway issue", "force majeure",
    "maintenance", "scheduled maintenance", "unscheduled maintenance", 
    "technical difficulties", "technical issue", "system upgrade", 
    "database migration", "migrating", "temporary outage", 
    "server error", "experiencing issues", "technical outage",
    "investigation", "under investigation", "regulatory action", 
    "fsa warning", "bafin", "hcmc", "sec warning", "regulator", 
    "cease and desist", "license revoked", "license suspended", 
    "compliance hold", "aml check", "frozen by authorities",
    "insolvency", "insolvent", "bankruptcy", "bankrupt", 
    "restructuring", "default", "defaulted", "closure", 
    "shutting down", "winding down", "liquidation", "liquidator", 
    "breached", "hacked", "compromised", "stolen", "cyber attack"
]

def send_email(subject, body_text):
    """Handles the SMTP connection and email dispatch."""
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver = sender 

    if not sender or not password:
        print("❌ CRITICAL ERROR: No email credentials found in environment variables.")
        return False

    msg = MIMEText(body_text, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
            print(f"✅ Email sent successfully: {subject}")
            return True
    except Exception as e:
        print(f"❌ Failed to send email via SMTP: {e}")
        return False

def get_html_template(title, message, color_theme, status_code="N/A"):
    """Generates the HTML structure for the alert emails."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f4f7f6; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.2); border: 2px solid {color_theme};">
            <div style="background-color: {color_theme}; padding: 20px; text-align: center; color: white;">
                <h2 style="margin: 0; font-size: 24px;">🚨 {title} 🚨</h2>
            </div>
            <div style="padding: 25px;">
                <p style="font-size: 18px; color: #333;"><strong>Системен статус:</strong></p>
                <div style="background-color: #f1f2f6; padding: 15px; border-left: 5px solid {color_theme}; border-radius: 4px; margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 16px;">{message}</p>
                </div>
                <p><strong>HTTP Status Code:</strong> {status_code}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
            </div>
        </div>
    </body>
    </html>
    """

def run_test_email():
    """Executes a dry-run test email to verify credentials."""
    print("🔄 Executing test email routine...")
    body = get_html_template(
        title="ТЕСТ НА СИСТЕМАТА", 
        message="Йо шефе как си днес! Това е тестов имейл. Връзката работи перфектно. Ако видиш това, значи си готов за истинския мониторинг.",
        color_theme="#1e90ff",
        status_code="200 OK"
    )
    success = send_email("🛠️ TEST: Системата за мониторинг е активна", body)
    if success:
        print("✅ Тестовият имейл премина успешно.")
    else:
        print("❌ Тестовият имейл се провали. Проверете GitHub Secrets.")

def check_platform():
    """Main scraping and analysis logic."""
    print(f"🚀 Starting monitoring session for: {TARGET_URL}")
    
    try:
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        response = scraper.get(TARGET_URL, timeout=20)
        html_text = response.text
        status_code = response.status_code
        
        is_blocked = False
        block_reason = ""
        
        # 1. Cloudflare / WAF Detection
        if status_code in [403, 503]:
            is_blocked = True
            block_reason = "Сървърът връща 403/503 HTTP грешка."
        elif "cloudflare" in html_text.lower() or "challenge-platform" in html_text.lower() or "just a moment..." in html_text.lower():
            is_blocked = True
            block_reason = "Открита е Cloudflare CAPTCHA или JS Challenge."
        elif "access denied" in html_text.lower():
            is_blocked = True
            block_reason = "Достъпът е отказан (Access Denied / IP Block)."

        if is_blocked:
            print("⚠️ BOT BLOCKED: Unable to parse site payload.")
            email_body = get_html_template(
                title="БОТЪТ Е БЛОКИРАН", 
                message=f"Скриптът не може да зареди страницата. Причина: {block_reason}",
                color_theme="#ffa502", 
                status_code=status_code
            )
            send_email("⚠️ ALERT: Ботът е блокиран от платформата", email_body)
            return

        # 2. Text Analysis for Critical Keywords
        soup = BeautifulSoup(html_text, 'html.parser')
        page_text = soup.get_text().lower()

        found_flags = [word for word in CRITICAL_KEYWORDS if word in page_text]
        
        if found_flags:
            print(f"🔥 CRITICAL FLAGS DETECTED: {found_flags}")
            email_body = get_html_template(
                title="ФИНАНСОВ СРИВ ЗАСЕЧЕН", 
                message=f"Намерени са следните критични думи в сайта: <strong>{', '.join(found_flags)}</strong>. Действайте незабавно.",
                color_theme="#ff4757", 
                status_code=status_code
            )
            send_email("🚨 КРИТИЧНО: Засечен е проблем с ликвидността!", email_body)
        else:
            print("✅ Status Normal: No critical keywords detected.")

    except Exception as e:
        print(f"❌ Execution Fatal Error: {e}")
        email_body = get_html_template(
            title="ГРЕШКА ПРИ ИЗПЪЛНЕНИЕ", 
            message=f"Скриптът за мониторинг крашна с грешка: {str(e)}",
            color_theme="#2f3542", 
            status_code="Error"
        )
        send_email("❌ ALERT: Скриптът за мониторинг крашна", email_body)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P Platform Monitor Script")
    parser.add_argument('--test', action='store_true', help="Run a test email execution.")
    args = parser.parse_args()

    if args.test:
        run_test_email()
    else:
        check_platform()
