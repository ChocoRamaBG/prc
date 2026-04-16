import requests
from bs4 import BeautifulSoup
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
    # Набиваш линкчовци тук. Ключовете в речника са просто "за резерва", ако сайтът гръмне.
    products = {
        "DJI Mini 3 (RC-N1)": "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=pages-refurbished&vid=141921",
        "DJI Mini 3 Fly More Combo": "https://store.dji.com/bg/product/dji-mini-3-combo-refurbished-unit?from=site-nav&vid=141981&set_region=BG"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    # МАГИЯТА ЗА ЕВРОТО: Набиваме му бисквитки, че сме в БГ и искаме ЕВРО!
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
            print("Failed to load JSON. Ще го презапишем, льольо.")

    changed = False

    for default_name, url in products.items():
        try:
            # 3 секунди пауза, както си поръча, палавник!
            time.sleep(3)
            
            # ПОЛЗВАМЕ БИСКВИТКИТЕ ТУК, ГАЩНИК! Не ги трий пак!
            response = requests.get(url, headers=headers, cookies=forced_cookies)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Търсим големия JSON
            match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
            
            current_state = None
            exact_name = default_name
            
            vid = url.split('vid=')[1].split('&')[0] if 'vid=' in url else None

            # 1. Опитваме първо с JSON-а (най-надеждно)
            if match and vid:
                state_json = json.loads(match.group(1))
                variants = state_json.get('products', {}).get('variants', [])
                for variant in variants:
                    if str(variant.get('id')) == str(vid):
                        # Име
                        if variant.get('title'):
                            exact_name = variant.get('title')
                        
                        # Цена
                        price_label = variant.get('priceLabel')
                        if not price_label:
                            price_label = f"{variant.get('priceCents', 0) / 100} €"
                        
                        # Статус
                        status_text = variant.get('status', {}).get('text', 'Unknown Status')
                        
                        # Ако статусът е "Out of stock" или "Notify Me", го унифицираме
                        if "out of stock" in status_text.lower() or "notify me" in status_text.lower() or "not available" in status_text.lower():
                            status_text = "Out of Stock / Notify Me"
                        
                        current_state = f"{price_label} | Статус: {status_text}"
                        break
            
            # 2. План Б: Ако JSON-ът се счупи, стържем HTML-а по конкретното ID
            if not current_state and vid:
                variant_li = soup.find('li', id=f"accessory-item-{vid}")
                if variant_li:
                    # Име
                    title_tag = variant_li.find('div', class_=re.compile(r'product-title'))
                    if title_tag:
                        exact_name = title_tag.text.strip()
                    
                    # Цена
                    price_tag = variant_li.find('span', class_=re.compile(r'price'))
                    if price_tag:
                        price_label = price_tag.text.strip()
                    else:
                        price_label = "Неизвестна цена"
                        
                    # Статус (търсим за текстове Out of stock или Notify me)
                    if variant_li.find(text=re.compile(r'Out of Stock|Notify Me', re.IGNORECASE)):
                        status_text = "Out of Stock / Notify Me"
                    else:
                        status_text = "Available / Buy Now"
                        
                    current_state = f"{price_label} | Статус: {status_text}"

            # Ако всичко мине окей и имаме състояние
            if current_state:
                old_state = last_prices.get(exact_name, "")

                if current_state != old_state:
                    # Форматираме красиво имейла
                    email_body = (
                        f"Йо шефе,\n\n"
                        f"Имаме промяна за:\n{exact_name}\n"
                        f"Линк: {url}\n\n"
                        f"Предишно състояние: {old_state if old_state else 'неизвестно'}\n"
                        f"Ново състояние: {current_state}\n\n"
                        f"Бягай да проверяваш, andibul carrot!"
                    )
                    
                    send_email(f"🚨 Промяна: {exact_name}", email_body)
                    last_prices[exact_name] = current_state
                    changed = True
                    
                    # Конзолен изход с ИМЕ + ЛИНК + СТАТУС
                    print(f"[{exact_name}] ({url}) State updated: {old_state} -> {current_state}. Мамка му човече, работи!")
                else:
                    # Конзолен изход с ИМЕ + ЛИНК + СТАТУС
                    print(f"[{exact_name}] ({url}) State is still {current_state}. No spam, гащник.")
            else:
                err_msg = f"Could not find data for {default_name}. Тотален паприкаш!"
                print(err_msg)
                send_email(f"⚠️ Error: {default_name}", f"{err_msg}\nЛинк: {url}")

        except Exception as e:
            err_msg = f"Error occurred while checking {default_name}: {e}"
            print(err_msg)
            send_email("🔥 DJI Script Crash!", f"Льольо, скриптът гръмна на {default_name}: {err_msg}\nЛинк: {url}")

    if changed:
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(last_prices, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    check_prices()
