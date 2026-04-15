import requests
from bs4 import BeautifulSoup
import smtplib
import os
import json
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
    # Тук си набиваш всички линкчовци, палавник!
    # Форматът е "Име на продукта": "Линк"
    products = {
        "DJI Mini 3 (Refurbished)": "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=pages-refurbished&vid=141921",
        "DJI Mini 3 Fly More Combo (Refurbished)": "https://store.dji.com/bg/product/dji-mini-3-combo-refurbished-unit?from=pages-refurbished&vid=141981",
        # Слагай запетайки след всеки линк, освен последния!
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    # Вече ползваме JSON, за да пазим множество цени
    prices_file = os.path.join(output_dir, "last_prices.json")
    last_prices = {}

    # Зареждаме старите цени, ако файлът съществува
    if os.path.exists(prices_file):
        try:
            with open(prices_file, "r", encoding="utf-8") as f:
                last_prices = json.load(f)
        except Exception:
            print("Failed to load JSON. Ще го презапишем, no cap.")

    changed = False

    # Въртим цикъл през всички сайтчовци
    for name, url in products.items():
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            price_span = soup.find('span', class_='styles__price___xAdOB')

            if price_span:
                current_price = price_span.text.strip()
                old_price = last_prices.get(name, "")

                if current_price != old_price:
                    send_email(
                        f"🚨 Price Change: {name}", 
                        f"Йо шефе, цената на {name} се смени от {old_price if old_price else 'неизвестна'} на {current_price}! Бягай да купуваш, andibul carrot!"
                    )
                    last_prices[name] = current_price
                    changed = True
                    print(f"[{name}] Price updated: {old_price} -> {current_price}. Мамка му човече, работи!")
                else:
                    print(f"[{name}] Price is still {current_price}. No spam, гащник.")
            else:
                err_msg = f"Could not find the price span for {name}. Пълен паприкаш!"
                print(err_msg)
                send_email(f"⚠️ Error: {name}", err_msg)

        except Exception as e:
            err_msg = f"Error occurred while checking {name}: {e}"
            print(err_msg)
            send_email("🔥 DJI Script Crash!", f"Льольо, скриптът гръмна на {name}: {err_msg}")

    # Ако поне една цена се е сменила, запазваме новия JSON файл
    if changed:
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(last_prices, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    check_prices()
