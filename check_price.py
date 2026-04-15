import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

def check_price():
    url = "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=pages-refurbished&vid=141921"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    # Тук ще си пазим ценичката, гащник
    price_file = os.path.join(output_dir, "last_price.txt")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        price_span = soup.find('span', class_='styles__price___xAdOB')

        if price_span:
            current_price = price_span.text.strip()
            
            # Четем старата цена, ако я има
            last_price = ""
            if os.path.exists(price_file):
                with open(price_file, "r", encoding="utf-8") as f:
                    last_price = f.read().strip()

            # Ако цената е различна от последната записана
            if current_price != last_price:
                send_email(current_price, last_price)
                
                # Презаписваме файлчето с новата цена
                with open(price_file, "w", encoding="utf-8") as f:
                    f.write(current_price)
                    
                print(f"Price updated from {last_price} to {current_price}. Мамка му човече, работи!")
            else:
                print(f"Price is still {current_price}. No spam for you, боклуче.")
        else:
            print("Could not find the price span. Пълен паприкаш.")

    except Exception as e:
        print(f"Error occurred: {e}")

def send_email(new_price, old_price):
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver = sender 

    if not sender or not password:
        print("No email credentials found. Андибул морков!")
        return

    old_text = old_price if old_price else "неизвестна"
    msg = MIMEText(f"Йо шефе, цената се смени от {old_text} на {new_price}! Бягай да купуваш, andibul carrot!")
    msg['Subject'] = "🚨 DJI Mini 3 Price Changed!"
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    check_price()
