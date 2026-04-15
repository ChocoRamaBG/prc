import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText

# По твое желание - изходната директория да е там, където е файлът
try:
    output_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    output_dir = os.getcwd()

def check_price():
    url = "https://store.dji.com/bg/product/dji-mini-3-refurbished-unit?from=pages-refurbished&vid=141921"
    # Слагаме хедъри, за да не ни резнат като някой бот гащник
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Търсим точно твоя span
        price_span = soup.find('span', class_='styles__price___xAdOB')

        if price_span:
            current_price = price_span.text.strip()
            target_price = "275 €"

            if current_price != target_price:
                send_email(current_price)
                log_msg = f"Price changed to {current_price}!"
            else:
                log_msg = "Price is still the same. No email sent."
        else:
            log_msg = "Could not find the price span. HTML is a total паприкаш."

    except Exception as e:
        log_msg = f"Error occurred: {e}"

    # Записваме лог файл в output_dir
    with open(os.path.join(output_dir, "price_log.txt"), "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def send_email(new_price):
    sender = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    receiver = sender # Пращаме имейла до теб самия

    if not sender or not password:
        print("No email credentials found. Andibul carrot, check your GitHub secrets.")
        return

    msg = MIMEText(f"Йо шефе, цената на дрона вече не е 275 евро! Новата цена е: {new_price}. Бягай да купуваш, палавник!")
    msg['Subject'] = "DJI Mini 3 Price Alert!"
    msg['From'] = sender
    msg['To'] = receiver

    try:
        # Използваме Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    check_price()
