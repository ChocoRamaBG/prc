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
            print(f"✅ Email '{subject}' sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def check_prices():
    url = "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=site-nav&vid=141921&set_region=BG"
    name = "DJI Mini 3 (DJI RC-N1) (Refurbished Unit)"
    target_vid = "141921"
    
    steps = []
    steps.append(f"🚀 Starting price check for: {name}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    forced_cookies = {"currency": "EUR", "country": "bg", "region": "BG"}
    prices_file = os.path.join(output_dir, "last_prices.json")
    
    try:
        # Step 1: Fetching the page
        response = requests.get(url, headers=headers, cookies=forced_cookies, timeout=15)
        response.raise_for_status()
        steps.append("✅ Successfully downloaded page content from DJI Store.")

        # Step 2: Extracting JSON state
        match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
        if not match:
            raise ValueError("Could not find __PRELOADED_STATE__. Пак са сменили сайта!")
        
        state_json = json.loads(match.group(1))
        steps.append("✅ Successfully extracted __PRELOADED_STATE__ JSON.")

        # Step 3: Parsing variants
        variants = state_json.get('products', {}).get('variants', [])
        current_state = None
        
        for variant in variants:
            if str(variant.get('id')) == target_vid:
                steps.append(f"✅ Found product variant with VID: {target_vid}")
                
                # При DJI 'in_stock' е директен ключ или е в 'status'
                is_in_stock = variant.get('in_stock', False) or variant.get('status', {}).get('is_in_stock', False)
                status_text = variant.get('status', {}).get('text', 'Unknown')
                
                # Допълнителна проверка - ако текстът на бутона е "Buy Now", значи Е в наличност!
                if status_text in ["Buy Now", "Add to Cart"]:
                    is_in_stock = True

                price_label = variant.get('priceLabel')
                if not price_label:
                    price_label = f"{variant.get('priceCents', 0) / 100} €"
                
                inventory_msg = "In Stock" if is_in_stock else "Out of Stock"
                current_state = f"{price_label} | Статус: {status_text} ({inventory_msg})"
                break

        if current_state:
            steps.append(f"📊 Current state determined: {current_state}")
            
            # Step 4: Comparison and Storage
            last_prices = {}
            if os.path.exists(prices_file):
                with open(prices_file, "r", encoding="utf-8") as f:
                    last_prices = json.load(f)
            
            old_state = last_prices.get(name, "")
            if current_state != old_state:
                steps.append("🔔 Change detected! Sending email...")
                email_body = f"Йо шефе,\n\nИмаме промяна за {name}:\n{current_state}\n\nЛинк: {url}"
                send_email(f"🚨 Промяна: {name}", email_body)
                
                last_prices[name] = current_state
                with open(prices_file, "w", encoding="utf-8") as f:
                    json.dump(last_prices, f, ensure_ascii=False, indent=4)
                steps.append("💾 Updated last_prices.json with new state.")
            else:
                steps.append("😴 No state change detected. No email sent.")

        # FINAL OUTPUT
        print("\n--- Списък на успешните стъпки ---")
        for step in steps:
            print(step)
        print(f"\n[FINAL] {name}: {current_state}. Мамка му човече, работи!\n")

    except Exception as e:
        err = f"💥 Error: {e}"
        print(err)
        send_email("🔥 DJI Script Crash!", err)

if __name__ == "__main__":
    check_prices()
