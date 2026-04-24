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

    # Внимание, гащник! Тук сменяме на HTML, за да е красиво!
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
    """Превръща тия криви стрингове в чисти числа за смятане, льольо!"""
    if not price_str or "Error" in price_str or "N/A" in price_str:
        return 0.0
    cleaned = re.sub(r'[^\d.,]', '', str(price_str))
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except:
        return 0.0

def get_price_data(url, site_key):
    # Хедърчовци, за да не ни хванат че сме бот!
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

        if site_key == "dji_global_refurbished":
            forced_cookies = {"currency": "EUR", "country": "bg", "region": "BG"}
            response = requests.get(url, headers=headers, cookies=forced_cookies, timeout=15)
            response.raise_for_status()
            
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

        elif site_key == "emag_bg":
            html_text = ""
            try:
                # Батко чатко мами системата
                emag_headers = headers.copy()
                emag_headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                response = requests.get(url, headers=emag_headers, timeout=20)
                response.raise_for_status()
                html_text = response.text
            except requests.exceptions.RequestException as req_e:
                if hasattr(req_e, 'response') and req_e.response is not None:
                    html_text = req_e.response.text
                else:
                    raise req_e

            # Проверка дали са ни нацелили с CAPTCHA
            if "captcha" in html_text.lower() or "challenge-platform" in html_text.lower():
                price = "N/A"
                status = "Блокиран от CAPTCHA (Cloudflare)"
            else:
                soup = BeautifulSoup(html_text, 'html.parser')
                
                # По-широк селектор, за да не гърми
                price_elem = soup.select_one('p.product-new-price')
                if price_elem:
                    price = price_elem.get_text(separator='', strip=True)
                else:
                    price_match = re.search(r'EM\.productDiscountedPrice\s*=\s*([\d.]+)', html_text)
                    price = price_match.group(1) + " €" if price_match else "N/A"
                
                if '"code":"in_stock"' in html_text or '"availability":{"id":3' in html_text:
                    status = "В наличност"
                elif '"code":"out_of_stock"' in html_text:
                    status = "Няма наличност"
                else:
                    status_elem = soup.select_one(".label-in_stock, .label-out_of_stock, .label-limited_stock")
                    status = status_elem.get_text(strip=True) if status_elem else "Unknown"

        else:
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

            elif site_key == "drones_bg":
                ins_elem = soup.select_one('p.price ins span.woocommerce-Price-amount bdi')
                if ins_elem:
                    price = ins_elem.get_text(separator=' ', strip=True)
                else:
                    price_elem = soup.select_one('p.price span.woocommerce-Price-amount bdi')
                    price = price_elem.get_text(separator=' ', strip=True) if price_elem else "N/A"

                status_elem = soup.select_one('.stock')
                status = status_elem.get_text(strip=True) if status_elem else "В наличност"

        return {"price": price, "status": status}
    except Exception as e:
        print(f"❌ Грешка при скрапване на {site_key}: {e}")
        return {"price": "Error", "status": str(e)}

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
        },
        "Drones.bg": {
            "url": "https://drones.bg/magazin/dronove-dji/vsichki-dji-dronove/dron-dji-mini-3/",
            "key": "drones_bg"
        }
    }

    prices_file = os.path.join(output_dir, "last_prices.json")
    
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
        source_price_val = clean_price(current_results["DJI GLOBAL (SOURCE)"]["price"])
        comp_prices = []
        for name, res in current_results.items():
            if name != "DJI GLOBAL (SOURCE)":
                val = clean_price(res["price"])
                if val > 0: comp_prices.append(val)
        
        min_comp_price = min(comp_prices) if comp_prices else 0.0
        potential_profit = min_comp_price - source_price_val if min_comp_price > 0 else 0.0
        roi_pct = (potential_profit / source_price_val * 100) if source_price_val > 0 else 0.0
        profit_margin_pct = (potential_profit / min_comp_price * 100) if min_comp_price > 0 else 0.0
        min_sell_price_15_roi = source_price_val * 1.15

        source_name = "DJI GLOBAL (SOURCE)"
        source_res = current_results[source_name]

        # --- HTML БРУТАЛЕН ДИЗАЙН С DIV-ОВЕ ЗА МОБИЛНИ ---
        email_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #333; padding: 20px;">
            <div style="max-width: 700px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                
                <div style="background-color: #ff4757; padding: 20px; text-align: center; color: white;">
                    <h2 style="margin: 0; font-size: 24px;">Йо шефе как си днес!</h2>
                    <p style="margin: 5px 0 0 0; font-size: 16px;">Ето ти пълния ценови паприкаш за:<br/><strong>🔥 {product_full_name} 🔥</strong></p>
                </div>

                <div style="padding: 25px;">
                    <div style="background-color: #fff0f1; border-left: 5px solid #ff4757; padding: 15px; border-radius: 4px; margin-bottom: 25px;">
                        <h3 style="margin-top: 0; color: #ff4757; font-size: 18px;">🚨 ЦЕНА ЗА КУПУВАНЕ (ОТ МАЙКАТА)</h3>
                        <p style="margin: 5px 0; font-size: 18px;"><strong>Цена:</strong> <span style="font-size: 22px; color: #2ed573; font-weight: bold;">{source_res['price']}</span></p>
                        <p style="margin: 5px 0;"><strong>Статус:</strong> {source_res['status']}</p>
                        <a href="{shops[source_name]['url']}" style="display: inline-block; margin-top: 10px; background-color: #ff4757; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-weight: bold;">🔗 Купи от тук</a>
                    </div>

                    <div style="background-color: #f1f2f6; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #dfe4ea;">
                        <h3 style="margin-top: 0; color: #2f3542; font-size: 18px; border-bottom: 2px solid #ced6e0; padding-bottom: 10px;">🚀 БИЗНЕС АНАЛИЗ (МЕТРИКИ ЗА ПРОФИТЧОВЦИ)</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #dfe4ea;">💸 Най-ниска цена при конкурентчовци:</td>
                                <td style="text-align: right; font-weight: bold;">{min_comp_price:.2f} €</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #dfe4ea;">💰 Потенциална брутна печалба:</td>
                                <td style="text-align: right; font-weight: bold; color: #2ed573;">{potential_profit:.2f} €</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #dfe4ea;">📈 Възвръщаемост (ROI):</td>
                                <td style="text-align: right; font-weight: bold; color: {'#2ed573' if roi_pct >= 15 else '#ff4757'};">{roi_pct:.1f}%</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #dfe4ea;">📉 Марж на печалбата:</td>
                                <td style="text-align: right; font-weight: bold;">{profit_margin_pct:.1f}%</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold;">🎯 Цена за минимум 15% ROI:</td>
                                <td style="text-align: right; font-weight: bold; color: #1e90ff;">{min_sell_price_15_roi:.2f} €</td>
                            </tr>
                        </table>
                    </div>

                    <h3 style="color: #2f3542; font-size: 18px; margin-bottom: 15px;">📊 ДЕТАЙЛИ ЗА КОНКУРЕНТЧОВЦИ</h3>
                    <div style="display: block;">
        """
        
        # Добавяме редовете за конкурентите динамично (вече с div-ове вместо счупени table-и)
        for i, (name, res) in enumerate(current_results.items()):
            if name == source_name: continue
            bg_color = "#ffffff" if i % 2 == 0 else "#f1f2f6"
            email_body += f"""
                        <div style="background-color: {bg_color}; border: 1px solid #dfe4ea; border-radius: 8px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <div style="font-weight: bold; font-size: 16px; color: #2f3542; border-bottom: 1px solid #ced6e0; padding-bottom: 8px; margin-bottom: 10px;">🏪 Магазин: {name}</div>
                            <div style="margin-bottom: 6px;"><strong>Цена:</strong> <span style="color: #ff4757; font-weight: bold; font-size: 16px;">{res['price']}</span></div>
                            <div style="margin-bottom: 10px;"><strong>Статус:</strong> {res['status']}</div>
                            <div><a href="{shops[name]['url']}" style="display: inline-block; background-color: #1e90ff; color: white; padding: 8px 12px; text-decoration: none; border-radius: 5px; font-size: 14px; font-weight: bold;">🔗 Към офертата</a></div>
                        </div>
            """
            
        email_body += """
                    </div>

                    <div style="margin-top: 30px; text-align: center; background-color: #ffa502; padding: 15px; border-radius: 8px; color: white; font-weight: bold; font-size: 16px;">
                        Бягай да действаш, преди някой друг палавник да ги изкупи, andibul carrot! 🥕
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        send_email(f"🚨 {product_full_name}: Пълен Бизнес Анализ", email_body)
        
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(current_results, f, ensure_ascii=False, indent=4)
        report_steps.append("💾 Saved results to last_prices.json")
    else:
        print("Нищо ново под слънцето, гащник. Пазарът е застинал.")

    print("\n--- Успешни стъпки ---")
    for step in report_steps:
        print(step)
    print(f"\nМамка му човече, работи! Вече знаеш колко еврочовци ще лапнеш.\n")

if __name__ == "__main__":
    check_prices()
