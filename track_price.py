from flask import Flask, request, jsonify
import requests
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from selenium.webdriver.chrome.service import Service
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

# Store initial and current price in-memory for simplicity
price_tracking = {}

def send_email(subject, body, recipient_email):
    sender_email = "youremail@email.com"
    sender_password = "yourpassword"  # Make sure to store this securely, not hard-coded
    smtp_server = "smtp.example.com"
    smtp_port = 587

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def get_amazon_data(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(2)  
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    title = soup.find('span', {'id': 'productTitle'}).text.strip()
    try:
        price = soup.find('span', {'id': 'priceblock_ourprice'}).text.strip()
        price = float(price.replace('$', '').replace(',', ''))  # Convert price to float
    except AttributeError:
        price = "Price not available"
    driver.quit()
    return {'title': title, 'price': price}

def get_ebay_data(url):
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.get(url)
    
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    title_element = soup.find('h1', {'class': 'x-item-title'})
    if title_element:
        title = title_element.text.strip()
    else:
        title = "Title not found"
    
    price_element = soup.find('span', {'id': 'prc-isum'})
    if price_element:
        price = price_element.text.strip()
        try:
            price = float(price.replace('$', '').replace(',', ''))
        except ValueError:
            price = "Invalid price"
    else:
        price = "Price not found"
    
    driver.quit()
    
    return {'title': title, 'price': price}

def check_price_periodically(url, user_email):
    initial_data = get_amazon_data(url)
    initial_price = initial_data['price']
    
    price_tracking['initial_price'] = initial_price
    price_tracking['current_price'] = initial_price
    price_tracking['tracking'] = True  # Tracking flag
    
    while price_tracking['tracking']:
        current_data = get_amazon_data(url)
        current_price = current_data['price']
        
        if current_price != price_tracking['current_price']:
            subject = "Price Change Alert!"
            body = f"The price has changed! Old price: ${price_tracking['current_price']}, New price: ${current_price}"
            send_email(subject, body, user_email)
            
            price_tracking['current_price'] = current_price
            
        time.sleep(300)  

@app.route("/stop_tracking", methods=["POST"])
def stop_tracking():
    price_tracking['tracking'] = False
    return jsonify({"message": "Price tracking stopped."}), 200

@app.route("/scrape", methods=["POST"])
def scrape_platform():
    url = request.json.get('url')
    user_email = request.json.get('email')

    if not url or not user_email:
        return jsonify({"error": "URL and email are required"}), 400

    # Scrape the platform based on the URL
    if "amazon" in url:
        print("Scraping Amazon...")
        current_data = get_amazon_data(url)
    elif "ebay" in url:
        print("Scraping eBay...")
        current_data = get_ebay_data(url)
    else:
        return jsonify({"error": "Unsupported platform"}), 400

    if current_data is None:
        return jsonify({"error": "Could not retrieve product price. Please check the URL."}), 400

    current_price = current_data['price']
    
    tracking_thread = threading.Thread(target=check_price_periodically, args=(url, user_email))
    tracking_thread.start()

    return jsonify({"message": f"Price tracking started. Initial price: ${current_price}", "price": current_price, "status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True)
