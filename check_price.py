import requests
import smtplib
import os
import json
import re
import time
from email.mime.text import MIMEText

# Гледай сега, гащник, тука ти слагам папката, както искаше
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

def send_email(subject, body_text):
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver = sender 

    if not sender or not password:
        print("No email credentials found. Андибул морков! Провери си GitHub Secrets!")
        return

    msg = MIMEText(body_text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
            print(f"Email '{subject}' sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def check_prices():
    # Само един линк, че да не се претовари малкият ти процесор
    url = "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=site-nav&vid=141921&set_region=BG"
    name = "DJI Mini 3 (DJI RC-N1) (Refurbished Unit)"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    forced_cookies = {
        "currency": "EUR",
        "country": "bg",
        "region": "BG"
    }
    
    prices_file = os.path.join(output_dir, "last_prices.json")
    last_prices = {}

    if os.path.exists(prices_file):
        try:
            with open(prices_file, "r", encoding="utf-8") as f:
                last_prices = json.load(f)
        except Exception:
            print("Мамка му човече, JSON-ът е дроб. Презаписваме.")

    try:
        response = requests.get(url, headers=headers, cookies=forced_cookies, timeout=15)
        response.raise_for_status()

        # Търсим големия мазник JSON в сорса
        match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
        
        if match:
            state_json = json.loads(match.group(1))
            # Вадим VID-а от URL-а, ако си го забравил
            target_vid = "141921" 
            
            variants = state_json.get('products', {}).get('variants', [])
            current_state = None
            
            for variant in variants:
                if str(variant.get('id')) == target_vid:
                    # DJI понякога слагат цената в различни полета, гащник!
                    price_cents = variant.get('priceCents', 0)
                    price_label = variant.get('priceLabel')
                    
                    if not price_label or "€" not in price_label:
                        price_label = f"{price_cents / 100} €"
                    
                    status_text = variant.get('status', {}).get('text', 'Unknown')
                    
                    # Гледаме и за наличността в бутона
                    inventory = "In Stock" if variant.get('status', {}).get('is_in_stock') else "Out of Stock"
                    
                    current_state = f"{price_label} | Статус: {status_text} ({inventory})"
                    break

            if current_state:
                old_state = last_prices.get(name, "")

                if current_state != old_state:
                    email_body = (
                        f"Йо шефе,\n\n"
                        f"Твоите дрончовци са с нова цена!\n"
                        f"Продукт: {name}\n"
                        f"Предишно състояние: {old_state if old_state else 'неизвестно'}\n"
                        f"Ново състояние: {current_state}\n\n"
                        f"Бягай да купуваш, andibul carrot!"
                    )
                    
                    send_email(f"🚨 Промяна: {name}", email_body)
                    last_prices[name] = current_state
                    
                    with open(prices_file, "w", encoding="utf-8") as f:
                        json.dump(last_prices, f, ensure_ascii=False, indent=4)
                    
                    print(f"[{name}] Ъпдейтнахме го! Сега е {current_state}. Мамка му човече, работи!")
                else:
                    print(f"[{name}] Пак е {current_state}. Нищо ново, льольо.")
            else:
                print("Не можах да намеря тоя VID в JSON-а. Пълен паприкаш!")
        else:
            print("DJI пак са сменили структурата. Малини, къпини, все тая... не работи.")

    except Exception as e:
        print(f"Гръмна като стара лада: {e}")

if __name__ == "__main__":
    check_prices()
