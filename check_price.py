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

def clean_price(price_str):
    """Превръща тия криви стрингове в чисти числа за смятане, льольо!"""
    if not price_str or "Error" in price_str or "N/A" in price_str:
        return 0.0
    # Махаме всичко, което не е цифра, точка или запетая
    cleaned = re.sub(r'[^\d.,]', '', str(price_str))
    # Оправяме запетайките, че става паприкаш
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except:
        return 0.0

def get_price_data(url, site_key):
    # What the fuck, слагаме истински хедърчовци, за да не ни хванат че сме бот!
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1"
    }
    
    try:
        price = "Unknown"
        status = "Unknown"
        delivery = "N/A" # <-- Батко чатко ти го добави тук, боклуче!

        if site_key == "dji_global_refurbished":
            forced_cookies = {"currency": "EUR", "country": "bg", "region": "BG"}
            response = requests.get(url, headers=headers, cookies=forced_cookies, timeout=15)
            response.raise_for_status()
            
            # Извличаме цена и статус от JSON паприкаша
            match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', response.text, re.DOTALL)
            if match:
                state_json = json.loads(match.group(1))
                target_vid = "141921" 
                variants = state_json.get('products', {}).get('variants', [])
                for v in variants:
                    if str(v.get('id')) == target_vid:
                        price = v.get('priceLabel') or f"{v.get('priceCents', 0) / 100} €"
                        st_text = v.get('status', {}).get('text', 'Unknown Status')
                        is_in_stock = v.get('in_stock', False) or v.get('status', {}).get('is_in_stock', False)
                        if st_text in ["Buy Now", "Add to Cart"]:
                            is_in_stock = True
                        status = f"{st_text} ({'В наличност' if is_in_stock else 'Няма наличност'})"
                        break
            else:
                price, status = "JSON Error", "Structure Changed"

            # --- ДОБАВЕНО ОТ БАТКО ЧАТКО ЗА ДАТАТА НА ДОСТАВКА ---
            try:
                soup_dji = BeautifulSoup(response.text, 'html.parser')
                # Търсим оня гнусен span, дето ми го прати
                del_elem = soup_dji.select_one('span[class*="fast-shipping-text"]')
                if del_elem:
                    delivery = del_elem.get_text(strip=True)
                else:
                    # Ако ония палавници от DJI сменят класовете, търсим с регекс
                    del_match = re.search(r'(Free express shipping arrival date:[^<]+)', response.text)
                    if del_match:
                        delivery = del_match.group(1).strip()
            except Exception as e:
                delivery = f"Грешка при скрапване на датата: {e}"

        elif site_key == "emag_bg":
            # Специално за eMAG, защото са палавници и слагат анти-бот защити
            html_text = ""
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                html_text = response.text
            except requests.exceptions.RequestException as req_e:
                print(f"❌ eMAG хвана бота, льольо! {req_e}")
                if hasattr(req_e, 'response') and req_e.response is not None:
                    html_text = req_e.response.text
                else:
                    raise req_e
            
            if html_text:
                try:
                    files = {'file': ('emag_screenshot.html', html_text.encode('utf-8'))}
                    paste_res = requests.post("https://file.io", files=files, timeout=10)
                    res_json = paste_res.json()
                    if paste_res.ok and res_json.get("success"):
                        print(f"📸 Ето ти линкче към паприкаша (1 сваляне само, гащник!): {res_json.get('link')}")
                    else:
                        print(f"❌ file.io умря. Ето ти малко HTML директно тук:\n\n{html_text[:1500]}\n...[TRUNCATED]...")
                except Exception as upload_e:
                    print(f"❌ What the hell, и облакът не работи: {upload_e}")

            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Пробваме първо през JS
            price_match = re.search(r'EM\.productDiscountedPrice\s*=\s*([\d.]+);', html_text)
            if price_match:
                price = price_match.group(1) + " лв."
            else:
                price_elem = soup.select_one('p.product-new-price[data-test="main-price"]')
                price = price_elem.get_text(separator='', strip=True) if price_elem else "N/A"
            
            if '"code":"in_stock"' in html_text or '"availability":{"id":3' in html_text:
                status = "В наличност"
            elif '"code":"out_of_stock"' in html_text:
                status = "Няма наличност"
            else:
                status_elem = soup.select_one(".label-in_stock, .label-out_of_stock, .label-limited_stock")
                status = status_elem.get_text(strip=True) if status_elem else "Unknown"

        else:
            # За останалите сайтчовци
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            if site_key == "store_dji_bg":
                price_elem = soup.find(id="our_price_display")
                status_elem = soup.find(id="availability_value")
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                status = status_elem.get_text(strip=True) if status_elem else "N/A"

            elif site_key == "aerocam_bg":
                price_elem = soup.select_one(".live-price-new")
                status_match = re.search(r'Наличност:</b>\s*([^<]+)', response.text)
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                status = status_match.group(1).strip() if status_match else "N/A"

            elif site_key == "copter_bg":
                price_elem = soup.select_one(".current-price-value")
                status_elem = soup.select_one(".js-product-availability")
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                status = status_elem.get_text(strip=True) if status_elem else "N/A"

        return {"price": price, "status": status, "delivery": delivery}
    except Exception as e:
        print(f"❌ Грешка при скрапване на {site_key}: {e}")
        return {"price": "Error", "status": str(e), "delivery": "Error"}

def check_prices():
    product_full_name = "DJI Mini 3 (DJI RC-N1) (Refurbished Unit)"
    
    shops = {
        "DJI GLOBAL (SOURCE)": {
            "url": "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=site-nav&vid=141921&set_region=BG",
            "key": "dji_global_refurbished"
        },
        "DJI Store Sofia (Local)": {
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
        },
        "eMAG.bg": {
            "url": "https://www.emag.bg/dron-dji-mini-3-4k-hdr-cp-ma-00000584-01/pd/D2DBDQMBM/",
            "key": "emag_bg"
        }
    }

    prices_file = os.path.join(output_dir, "multi_prices.json")
    last_data = {}
    if os.path.exists(prices_file):
        try:
            with open(prices_file, "r", encoding="utf-8") as f:
                last_data = json.load(f)
        except: pass

    current_results = {}
    any_change = False
    report_steps = []
    
    print(f"🚀 Стартиране на анализа за: {product_full_name}...")
    report_steps.append("🚀 Session started.")

    for name, info in shops.items():
        print(f"🔎 Проверка на {name}...")
        data = get_price_data(info["url"], info["key"])
        current_results[name] = data
        
        old_price = last_data.get(name, {}).get("price", "None")
        if data["price"] != old_price:
            any_change = True
            report_steps.append(f"✅ Промяна в {name}: {old_price} -> {data['price']}")
        else:
            report_steps.append(f"😴 Без промяна в {name} ({data['price']})")

    if any_change:
        # --- ИЗЧИСЛЯВАНЕ НА БИЗНЕС МЕТРИКИ (ЗА ПАЛАВНИЦИ) ---
        source_price_val = clean_price(current_results["DJI GLOBAL (SOURCE)"]["price"])
        comp_prices = []
        for name, res in current_results.items():
            if name != "DJI GLOBAL (SOURCE)":
                val = clean_price(res["price"])
                if val > 0: comp_prices.append(val)
        
        min_comp_price = min(comp_prices) if comp_prices else 0.0
        potential_profit = min_comp_price - source_price_val if min_comp_price > 0 else 0.0
        margin_pct = (potential_profit / source_price_val * 100) if source_price_val > 0 else 0.0

        # Build Email Body
        email_body = f"Йо шефе, ето ти пълния ценови паприкаш за:\n🔥 {product_full_name} 🔥\n\n"
        
        source_name = "DJI GLOBAL (SOURCE)"
        source_res = current_results[source_name]
        email_body += f"🚨 ЦЕНА ЗА КУПУВАНЕ (ОТ МАЙКАТА): {source_res['price']}\n"
        email_body += f"📦 Статус: {source_res['status']}\n"
        email_body += f"🚚 ДОСТАВКА: {source_res.get('delivery', 'Няма инфо')}\n"
        email_body += f"🔗 Линк: {shops[source_name]['url']}\n"
        email_body += "=" * 40 + "\n\n"
        
        email_body += "🚀 БИЗНЕС АНАЛИЗ (МЕТРИКИ ЗА ПРОФИТЧОВЦИ):\n"
        email_body += f"💸 Най-ниска цена при конкурентчовци: {min_comp_price:.2f} €\n"
        email_body += f"💰 Потенциална брутна печалба: {potential_profit:.2f} €\n"
        email_body += f"📈 Възвръщаемост (ROI): {margin_pct:.1f}%\n"
        email_body += "------------------------------\n\n"

        email_body += "📊 ДЕТАЙЛИ ЗА КОНКУРЕНТЧОВЦИ:\n"
        for name, res in current_results.items():
            if name == source_name: continue
            email_body += f"🏪 {name}\n"
            email_body += f"💰 Цена: {res['price']}\n"
            email_body += f"📦 Статус: {res['status']}\n"
            email_body += f"🔗 Линк: {shops[name]['url']}\n"
            email_body += "-" * 30 + "\n"
        
        email_body += "\nБягай да действаш, преди някой друг палавник да ги изкупи, andibul carrot!"
        
        send_email(f"🚨 {product_full_name}: Пълен Бизнес Анализ", email_body)
        
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(current_results, f, ensure_ascii=False, indent=4)
        report_steps.append("💾 Saved results to multi_prices.json")
    else:
        print("Нищо ново под слънцето, гащник. Пазарът е застинал.")

    print("\n--- Успешни стъпки ---")
    for step in report_steps:
        print(step)
    print(f"\nМамка му човече, работи! Вече знаеш колко еврочовци ще лапнеш.\n")

if __name__ == "__main__":
    check_prices()
