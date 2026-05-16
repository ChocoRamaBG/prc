import sys
import subprocess

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

import requests
import smtplib
import os
import json
import re
import time
import cloudscraper
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

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

    msg = MIMEText(body_text, 'html', 'utf-8')
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

def clean_price(price_str):
    if not price_str or "Error" in str(price_str) or "N/A" in str(price_str):
        return 0.0
    
    price_str = str(price_str).lower()
    is_bgn = "лв" in price_str or "bgn" in price_str
    
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
        
    try:
        val = float(cleaned)
        if is_bgn:
            val = round(val / 1.95583, 2)
        return val
    except:
        return 0.0

def get_price_data(url, site_key):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    try:
        price = "Unknown"
        status = "Unknown"

        if site_key == "dji_global_refurbished":
            forced_cookies = {"currency": "EUR", "country": "bg", "region": "BG"}
            response = requests.get(url, headers=headers, cookies=forced_cookies, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # РАЗБИРААЙ! Търсим визуалната цена в Add to Cart лентата
            price_box = soup.select_one('section[data-test-locator="sectionAddToCartBar"] span[class*="price"]')
            if price_box:
                price = price_box.get_text(strip=True)
                status = "В наличност (Визуално потвърдено)"
            else:
                # Ако няма такава лента, значи вероятно няма наличност или дизайна е сменен тотално
                price = "N/A"
                status = "Няма наличност (Лентата за купуване липсва)"

        elif site_key == "emag_bg":
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
            response = scraper.get(url, timeout=20)
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Търсим в мета таговете или в JavaScript обекта на eMAG
            meta_p = soup.find('meta', property='product:price:amount') or soup.find('meta', attrs={'itemprop': 'price'})
            if meta_p:
                price = meta_p.get('content') + " лв."
            else:
                match = re.search(r'EM\.productDiscountedPrice\s*=\s*([\d.]+)', html)
                price = match.group(1) + " лв." if match else "N/A"
            
            status = "В наличност" if "in_stock" in html or "id\":3" in html else "Няма наличност"

        elif site_key == "store_dji_bg":
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            price_elem = soup.find(id="our_price_display")
            status_elem = soup.find(id="availability_value")
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            status = status_elem.get_text(strip=True) if status_elem else "N/A"

        elif site_key == "aerocam_bg":
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            price_elem = soup.select_one(".live-price")
            if price_elem:
                txt = price_elem.get_text(separator=' ', strip=True)
                # Опитваме се да извадим само евро сумата
                match = re.search(r'([\d.,]+)\s*€', txt)
                price = match.group(1) + " €" if match else txt
            status_p = soup.find(lambda tag: tag.name == "p" and "Наличност:" in tag.get_text())
            status = status_p.get_text(strip=True).replace("Наличност:", "").strip() if status_p else "N/A"

        elif site_key == "copter_bg":
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            price_elem = soup.select_one(".current-price-value")
            status_elem = soup.select_one(".js-product-availability")
            price = price_elem.get_text(strip=True) if price_elem else "N/A"
            status = status_elem.get_text(strip=True) if status_elem else "N/A"

        elif site_key == "drones_bg":
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            price_elem = soup.select_one('p.price span.woocommerce-Price-amount bdi')
            price = price_elem.get_text(separator=' ', strip=True) if price_elem else "N/A"
            status_elem = soup.select_one('.stock')
            status = status_elem.get_text(strip=True) if status_elem else "В наличност"

        return {"price": price, "status": status}
    except Exception as e:
        return {"price": "Error", "status": str(e)}

def check_prices():
    product_full_name = "DJI Mini 3 (DJI RC-N1) (Refurbished Unit)"
    shops = {
        "DJI GLOBAL (SOURCE)": {"url": "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?vid=141921&set_region=BG", "key": "dji_global_refurbished"},
        "DJI Store Sofia (Local)": {"url": "https://store.dji.bg/bg/dron-dji-mini-3.html", "key": "store_dji_bg"},
        "AeroCam.bg": {"url": "https://aerocam.bg/DJI-dronove/dji-mini-drones/dronove-Dji-mini-3/dron-dji-mini-3", "key": "aerocam_bg"},
        "Copter.bg": {"url": "https://www.copter.bg/bg/dron-dji-mini-3.html", "key": "copter_bg"},
        "eMAG.bg": {"url": "https://www.emag.bg/dron-dji-mini-3-4k-hdr-cp-ma-00000584-01/pd/D2DBDQMBM/", "key": "emag_bg"},
        "Drones.bg": {"url": "https://drones.bg/magazin/dronove-dji/vsichki-dji-dronove/dron-dji-mini-3/", "key": "drones_bg"}
    }

    prices_file = os.path.join(output_dir, "last_prices.json")
    last_data = {}
    if os.path.exists(prices_file):
        try:
            with open(prices_file, "r", encoding="utf-8") as f: last_data = json.load(f)
        except: pass

    current_results = {}
    any_change = False
    print(f"🚀 Анализ за: {product_full_name}...")

    for name, info in shops.items():
        print(f"🔎 Проверка на {name}...")
        data = get_price_data(info["url"], info["key"])
        current_results[name] = data
        if data["price"] != last_data.get(name, {}).get("price", ""): any_change = True

    if any_change:
        source_price_val = clean_price(current_results["DJI GLOBAL (SOURCE)"]["price"])
        comp_prices = [clean_price(res["price"]) for n, res in current_results.items() if n != "DJI GLOBAL (SOURCE)" and clean_price(res["price"]) > 0]
        
        min_comp = min(comp_prices) if comp_prices else 0.0
        profit = min_comp - source_price_val if min_comp > 0 else 0.0
        roi = (profit / source_price_val * 100) if source_price_val > 0 else 0.0

        email_body = f"""
        <html><body style="font-family: sans-serif; background: #f4f7f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <div style="background: #ff4757; padding: 15px; text-align: center; color: white;">
                    <h2>Актуален ценови доклад</h2>
                    <p>{product_full_name}</p>
                </div>
                <div style="padding: 20px;">
                    <p style="font-size: 20px;">💰 Цена от DJI GLOBAL: <strong>{current_results['DJI GLOBAL (SOURCE)']['price']}</strong></p>
                    <p>📊 Потенциална печалба спрямо БГ пазара: <span style="color: #2ed573; font-weight: bold;">{profit:.2f} €</span> (ROI: {roi:.1f}%)</p>
                    <hr/>
                    <h4>Детайли по магазини:</h4>
                    {"".join([f"<p><b>{n}</b>: {r['price']} ({r['status']})</p>" for n, r in current_results.items()])}
                </div>
            </div>
        </body></html>"""

        send_email(f"🚨 Цена за DJI Mini 3: {current_results['DJI GLOBAL (SOURCE)']['price']}", email_body)
        with open(prices_file, "w", encoding="utf-8") as f: json.dump(current_results, f, ensure_ascii=False, indent=4)
        print("✅ Промените са отчетени и имейлът е пратен!")
    else:
        print("😴 Няма промяна в цените.")

if __name__ == "__main__":
    check_prices()
