# session_manager.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import os
import time

class LinkedInSessionManager:
    def __init__(self):
        load_dotenv()  # Load environment variables for credentials
        self.driver = None

    def init_driver(self):
        """Initialize the Selenium WebDriver with Chrome options."""
        options = Options()
        
        # Anti-detection settings
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("start-maximized")
        
        # Initialize WebDriver
        self.driver = webdriver.Chrome(options=options)
        
        # Hide WebDriver property
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return self.driver

    def login(self):
        """Log into LinkedIn using credentials from environment variables."""
        self.driver.get("https://www.linkedin.com/login?fromSignIn=true")
        
        # Input login details
        username = self.driver.find_element(By.ID, "username")
        username.send_keys(os.getenv('USERNAME'))
        time.sleep(2)
        
        password = self.driver.find_element(By.ID, "password")
        password.send_keys(os.getenv('PASSWORD'))
        time.sleep(2)
        
        # Submit login
        sign_in_button = self.driver.find_element(By.XPATH, '//*[@type="submit"]')
        sign_in_button.click()
        time.sleep(5)  # Allow time for login
        
        # Verify login
        if "feed" in self.driver.current_url:
            print("Login successful!")
        else:
            print("Login failed. Check credentials or captcha requirements.")
            self.driver.quit()

    def close_session(self):
        """Close the browser session."""
        self.driver.quit()
