import requests
import smtplib
import os
import json
import re
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
        print("No email credentials found. Андибул морков!")
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
        "DJI Mini 3 Fly More (RC-N1)": "https://store.dji.com/bg/product/dji-mini-3-combo-refurbished-unit?from=pages-refurbished&vid=141981"
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
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Изсмукваме големия JSON с всички данни
            match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
            
            if match:
                state_json = json.loads(match.group(1))
                vid = url.split('vid=')[1].split('&')[0] if 'vid=' in url else None
                
                current_price = None
                exact_name = name # Fallback име
                
                if vid:
                    variants = state_json.get('products', {}).get('variants', [])
                    for variant in variants:
                        if str(variant.get('id')) == str(vid):
                            price_cents = variant.get('priceCents', 0)
                            current_price = f"{price_cents / 100} €"
                            
                            # ВЗИМАМЕ ТОЧНОТО ИМЕ ДИРЕКТНО ОТ JSON-a, ЗА ДА НЯМА ГРЕШКИ!
                            if variant.get('title'):
                                exact_name = variant.get('title')
                            break

                if current_price:
                    old_price = last_prices.get(exact_name, "")

                    if current_price != old_price:
                        send_email(
                            f"🚨 Price Change: {exact_name}", 
                            f"Йо шефе, цената на {exact_name} се смени от {old_price if old_price else 'неизвестна'} на {current_price}! Бягай да купуваш, andibul carrot!"
                        )
                        last_prices[exact_name] = current_price
                        changed = True
                        print(f"[{exact_name}] Price updated: {old_price} -> {current_price}. Мамка му човече, работи!")
                    else:
                        print(f"[{exact_name}] Price is still {current_price}. No spam, гащник.")
                else:
                    err_msg = f"Could not find price for {name} in JSON data. Пълен паприкаш!"
                    print(err_msg)
                    send_email(f"⚠️ Error: {name}", err_msg)
            else:
                err_msg = f"Could not find __PRELOADED_STATE__ for {name}. Пълен паприкаш! Пак са сменили сайта!"
                print(err_msg)
                send_email(f"⚠️ Error: {name}", err_msg)

        except Exception as e:
            err_msg = f"Error occurred while checking {name}: {e}"
            print(err_msg)
            send_email("🔥 DJI Script Crash!", f"Льольо, скриптът гръмна на {name}: {err_msg}")

    if changed:
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(last_prices, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    check_prices()
