import requests
from bs4 import BeautifulSoup
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
    # Набивай си линкчовци тук на воля!
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
            print("Failed to load JSON. Ще го презапишем, гащник.")

    changed = False

    for name, url in products.items():
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Вземаме ID-то (vid) от линка
            vid = url.split('vid=')[1].split('&')[0] if 'vid=' in url else None
            
            current_price = None
            exact_name = name
            
            if vid:
                # Търсим конкретния бутон/контейнер за този вариант, за да избегнем SSR дефолтите
                variant_li = soup.find('li', id=f"accessory-item-{vid}")
                if variant_li:
                    # Вадим цената само от него
                    price_tag = variant_li.find('span', class_=re.compile(r'price'))
                    if price_tag:
                        current_price = price_tag.text.strip()
                    
                    # Вадим точното име само от него
                    title_tag = variant_li.find('div', class_=re.compile(r'product-title'))
                    if title_tag:
                        exact_name = title_tag.text.strip()

            # План Б: Ако няма vid или дизайнът е друг, ползваме главното заглавие
            if not current_price:
                price_span = soup.find('span', class_=re.compile(r'styles__price'))
                if price_span:
                    current_price = price_span.text.strip()
                    
                h1_tag = soup.find('h1', class_=re.compile(r'product-title'))
                if h1_tag and exact_name == name:
                    exact_name = h1_tag.text.strip()

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
                    print(f"[{exact_name}] Price is still {current_price}. No spam for you, боклуче.")
            else:
                err_msg = f"Could not find price for {name}. Тотален паприкаш!"
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
