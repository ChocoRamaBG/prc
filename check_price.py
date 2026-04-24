import requests
import smtplib
import os
import json
import re
import time
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

# Пътят към папката, за да не се губят файловете като твоите мозъчни клетки
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
    # Премахваме валути и празни пространства
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    # Оправяме хилядите и десетичните запетаи
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except:
        return 0.0

def get_price_data(url, site_key, target_vid=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7"
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
                variants = state_json.get('products', {}).get('variants', [])
                for v in variants:
                    if str(v.get('id')) == str(target_vid):
                        price = v.get('priceLabel') or f"{v.get('priceCents', 0) / 100} €"
                        st_text = v.get('status', {}).get('text', 'Unknown Status')
                        is_in_stock = v.get('in_stock', False) or v.get('status', {}).get('is_in_stock', False)
                        if st_text in ["Buy Now", "Add to Cart"]:
                            is_in_stock = True
                        status = f"{st_text} ({'В наличност' if is_in_stock else 'Няма наличност'})"
                        break
            else:
                price, status = "JSON Error", "Structure Changed"

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

            elif site_key == "emag_bg":
                # eMAG се правят на интересни, ама мета таговете не лъжат
                price_meta = soup.find("meta", property="product:price:amount")
                price = f"{price_meta['content']} €" if price_meta else "N/A"
                
                avail_meta = soup.find("meta", property="product:availability")
                if avail_meta and "instock" in avail_meta.get('content', '').lower():
                    status = "В наличност"
                elif "В наличност" in response.text:
                    status = "В наличност"
                else:
                    status = "Няма наличност"

        return {"price": price, "status": status}
    except Exception as e:
        return {"price": "Error", "status": str(e)}

def check_prices():
    # ТУКА СА ТВОИТЕ ДРОНЧОВЦИ, ПАЛАВНИК!
    tracking_list = [
        {
            "name": "DJI Mini 3 (DJI RC-N1) (Refurbished Unit)",
            "global_url": "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=site-nav&vid=141921&set_region=BG",
            "global_vid": "141921",
            "local_shops": {
                "DJI Store Sofia": "https://store.dji.bg/bg/dron-dji-mini-3.html",
                "AeroCam.bg": "https://aerocam.bg/DJI-dronove/dji-mini-drones/dronove-Dji-mini-3/dron-dji-mini-3",
                "Copter.bg": "https://www.copter.bg/bg/dron-dji-mini-3.html",
                "eMAG.bg": "https://www.emag.bg/dron-dji-mini-3-4k-hdr-cp-ma-00000584-01/pd/D2DBDQMBM/"
            }
        },
        {
            "name": "DJI Mini 3 Fly More Combo (DJI RC-N1) (Refurbished Unit)",
            "global_url": "https://store.dji.com/bg/product/dji-mini-3-combo-refurbished-unit?from=site-nav&vid=141981&set_region=BG",
            "global_vid": "141981",
            "local_shops": {
                "DJI Store Sofia": "https://store.dji.bg/bg/dron-dji-mini-3-fly-more-combo.html",
                "AeroCam.bg": "https://aerocam.bg/dji-mini-3-fly-more-combo",
                "Copter.bg": "https://www.copter.bg/bg/dron-dji-mini-3-fly-more-combo-dji-rc-n1.html",
                "eMAG.bg": "https://www.emag.bg/dron-dji-mini-3-fly-more-combo-dji-rc-n1-cp-ma-00000585-01/pd/D8DBDQMBM/"
            }
        }
    ]

    prices_file = os.path.join(output_dir, "multi_product_analysis.json")
    last_data = {}
    if os.path.exists(prices_file):
        try:
            with open(prices_file, "r", encoding="utf-8") as f:
                last_data = json.load(f)
        except: pass

    all_reports = []
    any_major_change = False
    
    print(f"🚀 Стартиране на брутален пазарен анализ...")

    for item in tracking_list:
        p_name = item["name"]
        print(f"--- 🔎 Анализирам: {p_name} ---")
        
        # 1. Глобална цена (Изворът)
        source_data = get_price_data(item["global_url"], "dji_global_refurbished", item["global_vid"])
        source_val = clean_price(source_data["price"])
        
        # 2. Локални цени (Конкурентчовци)
        local_results = {}
        comp_prices = []
        for s_name, s_url in item["local_shops"].items():
            key = "emag_bg" if "emag.bg" in s_url else "store_dji_bg" if "store.dji.bg" in s_url else "aerocam_bg" if "aerocam.bg" in s_url else "copter_bg"
            data = get_price_data(s_url, key)
            local_results[s_name] = data
            val = clean_price(data["price"])
            if val > 0: comp_prices.append(val)
        
        # 3. Метрики за профитчовци
        min_comp = min(comp_prices) if comp_prices else 0.0
        avg_comp = sum(comp_prices) / len(comp_prices) if comp_prices else 0.0
        profit = min_comp - source_val if min_comp > 0 else 0.0
        roi = (profit / source_val * 100) if source_val > 0 else 0.0
        
        # Проверка за промяна
        old_source_price = last_data.get(p_name, {}).get("source_price", 0.0)
        if source_val != old_source_price and source_val > 0:
            any_major_change = True

        product_report = {
            "name": p_name,
            "source": source_data,
            "local": local_results,
            "metrics": {
                "min_comp": min_comp, 
                "avg_comp": avg_comp,
                "profit": profit, 
                "roi": roi,
                "gap": avg_comp - min_comp
            },
            "url": item["global_url"]
        }
        all_reports.append(product_report)

    if any_major_change:
        email_body = "Йо шефе, пазарът е твой! Ето пълния паприкаш от метрики:\n\n"
        
        for rep in all_reports:
            email_body += f"📦 ПРОДУКТ: {rep['name']}\n"
            email_body += f"💰 ЦЕНА ЗА КУПУВАНЕ (SOURCE): {rep['source']['price']}\n"
            email_body += f"🚦 СТАТУС: {rep['source']['status']}\n"
            email_body += f"💵 ПРЕДПОЛАГАЕМ ПРОФИТ: {rep['metrics']['profit']:.2f} €\n"
            email_body += f"📈 ROI (Възвръщаемост): {rep['metrics']['roi']:.1f}%\n"
            email_body += f"⚖️ Пазарна средна в БГ: {rep['metrics']['avg_comp']:.2f} €\n"
            email_body += f"📉 Най-ниска цена в БГ: {rep['metrics']['min_comp']:.2f} €\n"
            email_body += f"🔗 Линк за покупка: {rep['url']}\n"
            email_body += "\n--- Детайли по магазини ---\n"
            for s_name, s_data in rep['local'].items():
                email_body += f"   - {s_name}: {s_data['price']} ({s_data['status']})\n"
            email_body += "=" * 45 + "\n\n"
        
        email_body += "Бягай да действаш, преди конкурентчовците да се събудят, andibul carrot!"
        send_email("🚨 DJI Market Intelligence: Нова далавера дебне!", email_body)
        
        # Запазваме историята
        new_history = {r["name"]: {"source_price": clean_price(r["source"]["price"])} for r in all_reports}
        with open(prices_file, "w", encoding="utf-8") as f:
            json.dump(new_history, f, ensure_ascii=False, indent=4)
    else:
        print("Малини, къпини... нищо не се е променило в източника.")

if __name__ == "__main__":
    check_prices()
