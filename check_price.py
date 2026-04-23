import requests
import smtplib
import os
import json
import re
import time
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

# Пътят към папката, че да не ги търсиш като изгубени чорапчовци
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

def send_email(subject, body_text):
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver = sender 

    if not sender or not password:
        print("❌ No email credentials found. Андибул морков! Провери си GitHub Secrets!")
        return

    msg = MIMEText(body_text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
            print(f"✅ Email sent successfully: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def get_price_data(url, site_key):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        price = "Unknown"
        status = "Unknown"

        if site_key == "store_dji_bg":
            # Link 1: store.dji.bg
            price_elem = soup.find(id="our_price_display")
            status_elem = soup.find(id="availability_value")
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            status = status_elem.get_text(strip=True) if status_elem else "N/A"

        elif site_key == "aerocam_bg":
            # Link 2: aerocam.bg
            price_elem = soup.select_one(".live-price-new")
            # Наличността е малко по-скрита в текста
            status_match = re.search(r'Наличност:</b>\s*([^<]+)', response.text)
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            status = status_match.group(1).strip() if status_match else "N/A"

        elif site_key == "copter_bg":
            # Link 3: copter.bg
            price_elem = soup.select_one(".current-price-value")
            status_elem = soup.select_one(".js-product-availability")
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            status = status_elem.get_text(strip=True) if status_elem else "N/A"

        return {"price": price, "status": status}
    except Exception as e:
        return {"price": "Error", "status": str(e)}

def check_prices():
    shops = {
        "DJI Store Sofia (Official)": {
            "url": "https://store.dji.bg/bg/dron-dji-mini-3.html",
            "key": "store_dji_bg"
        },
        "AeroCam.bg": {
            "url": "https://aerocam.bg/DJI-dronove/dji-mini-drones/dronove-Dji-mini-3/dron-dji-mini-3",
            "key": "aerocam_bg"
        },
        "Copter.bg": {
            "url": "https://www.copter.bg/bg/dron-dji-mini-3.html",
            "key": "copter_bg"
        }
    }

    prices_file = os.path.join(output_dir, "multi_prices.json")
    last_data = {}
    if os.path.exists(prices_file):
        with open(prices_file, "r", encoding="utf-8") as f:
            last_data = json.load(f)

    current_results = {}
    any_change = False
    report_steps = []
    
    print("🚀 Стартиране на проверката за DJI Mini 3...")
    report_steps.append("🚀 Session started.")

    for name, info in shops.items():
        print(f"🔎 Checking {name}...")
        data = get_price_data(info["url"], info["key"])
        current_results[name] = data
        
        old_price = last_data.get(name, {}).get("price", "None")
        if data["price"] != old_price:
            any_change = True
            report_steps.append(f"✅ Change detected in {name}: {old_price} -> {data['price']}")
        else:
            report_steps.append(f"😴 No change in {name} ({data['price']})")

    if any_change:
        # Build Email Body
        email_body = "Йо шефе, ето ти пълния паприкаш от цени за DJI Mini 3:\n\n"
        for name, res in current_results.items():
            email_body += f"🏪 {name}\n"
            email_body += f"💰 Цена: {res['price']}\n"
            email_body += f"📦 Статус: {res['status']}\n"
            email_body += f"🔗 Линк: {shops[name]['url']}\n"
            email_body += "-" * 30 + "\n"
        
        email_body += "\nБягай да действаш, andibul carrot!"
        
        send_email("🚨 DJI Mini 3: Ценова Сводка", email_body)
        
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(current_results, f, ensure_ascii=False, indent=4)
        report_steps.append("💾 Saved results to multi_prices.json")
    else:
        print("Нищо ново под слънцето, гащник.")

    print("\n--- Успешни стъпки ---")
    for step in report_steps:
        print(step)
    print("\nМамка му човече, работи! Всички дрончовци са под контрол.\n")

if __name__ == "__main__":
    check_prices()
