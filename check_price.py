import requests
import smtplib
import os
import json
import re
import time
from email.mime.text import MIMEText

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
    # Тук си слагаш линкчовците
    products = {
        "DJI Mini 3 (RC-N1)": "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=pages-refurbished&vid=141921",
        "DJI Mini 3 Fly More Combo": "https://store.dji.com/bg/product/dji-mini-3-combo-refurbished-unit?from=pages-refurbished&vid=141981"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    prices_file = os.path.join(output_dir, "last_prices.json")
    last_prices = {}

    if os.path.exists(prices_file):
        try:
            with open(prices_file, "r", encoding="utf-8") as f:
                last_prices = json.load(f)
        except Exception:
            print("Failed to load JSON. Ще го презапишем.")

    changed = False

    for name, url in products.items():
        try:
            # 3 секунди пауза, както си поръча, палавник!
            time.sleep(3)
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Изсмукваме големия JSON с всички данни
            match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
            
            if match:
                state_json = json.loads(match.group(1))
                vid = url.split('vid=')[1].split('&')[0] if 'vid=' in url else None
                
                current_state = None
                exact_name = name 
                
                if vid:
                    variants = state_json.get('products', {}).get('variants', [])
                    for variant in variants:
                        if str(variant.get('id')) == str(vid):
                            # Взимаме директно етикета на цената от DJI, за да няма британски паунди и глупости
                            price_label = variant.get('priceLabel')
                            if not price_label:
                                price_label = f"{variant.get('priceCents', 0) / 100} €"
                            
                            # Взимаме статуса на бутона (напр. "Buy Now" или "Out of stock")
                            status_text = variant.get('status', {}).get('text', 'Unknown Status')
                            
                            # Комбинираме ги! Вече следим и цената, и наличността
                            current_state = f"{price_label} | Статус: {status_text}"
                            
                            if variant.get('title'):
                                exact_name = variant.get('title')
                            break

                if current_state:
                    old_state = last_prices.get(exact_name, "")

                    if current_state != old_state:
                        email_body = f"Йо шефе,\n\nИмаме промяна за {exact_name}!\n\nПредишно състояние: {old_state if old_state else 'неизвестно'}\nНово състояние: {current_state}\n\nБягай да проверяваш, andibul carrot!\n\nДиректен линк към продукта:\n{url}"
                        
                        send_email(f"🚨 Промяна: {exact_name}", email_body)
                        last_prices[exact_name] = current_state
                        changed = True
                        print(f"[{exact_name}] State updated: {old_state} -> {current_state}. Мамка му човече, работи!")
                    else:
                        print(f"[{exact_name}] State is still {current_state}. No spam, гащник.")
                else:
                    err_msg = f"Could not find data for {name} in JSON. Пълен паприкаш!"
                    print(err_msg)
                    send_email(f"⚠️ Error: {name}", err_msg)
            else:
                err_msg = f"Could not find __PRELOADED_STATE__ for {name}. Пак са сменили сайта!"
                print(err_msg)
                send_email(f"⚠️ Error: {name}", f"{err_msg}\nЛинк: {url}")

        except Exception as e:
            err_msg = f"Error occurred while checking {name}: {e}"
            print(err_msg)
            send_email("🔥 DJI Script Crash!", f"Льольо, скриптът гръмна на {name}: {err_msg}\nЛинк: {url}")

    if changed:
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(last_prices, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    check_prices()
