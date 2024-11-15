
from session_manager import LinkedInSessionManager
from queue_manager import QueueManager
from database_manager import DatabaseManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
from datetime import datetime, timedelta
import re

class ProfileWorker:
    def __init__(self):
        self.session_manager = LinkedInSessionManager()
        self.queue_manager = QueueManager()
        self.db_manager = DatabaseManager()  
        self.driver = self.session_manager.init_driver()

    def find_and_click_show_all_posts(self):
        """Load page, use BeautifulSoup to locate 'Show all posts' button dynamically, and click it with Selenium."""
        
        time.sleep(3)  

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        show_all_button = None
        try:
            show_all_button = soup.find("span", string=lambda t: t and "Show all posts" in t)
            
            if show_all_button:
                button_class = show_all_button.parent.get("class")
                if button_class:
                    button_class_selector = "." + ".".join(button_class)
                    print(f"Found 'Show all posts' button with class selector: {button_class_selector}")
                else:
                    print("Button found but class name not retrieved.")
            else:
                print("'Show all posts' button not found in HTML.")
                return 

        except Exception as e:
            print("Error locating 'Show all posts' button:", e)
            return 

        try:
            show_all_posts_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_class_selector))
            )
            self.driver.execute_script("arguments[0].click();", show_all_posts_button)
            print("Clicked on 'Show all posts' button.")
            time.sleep(3)

        except Exception as e:
            print("Failed to click 'Show all posts' button with Selenium:", e)

    def parse_relative_date(self,relative_date_str):
        """Convert a relative date like '1mo' or '2wk' to an absolute date."""
        current_date = datetime.now()

        # Match against patterns for weeks, months, years, days
        match = re.match(r"(\d+)([a-z]+)", relative_date_str)
        if match:
            value, unit = int(match.group(1)), match.group(2)
            
            if unit == "mo":  # Months
                return current_date - timedelta(days=value * 30)
            elif unit == "wk":  # Weeks
                return current_date - timedelta(weeks=value)
            elif unit == "yr":  # Years
                return current_date - timedelta(days=value * 365)
            elif unit == "d":  # Days
                return current_date - timedelta(days=value)
        return current_date
        

    def process_profile(self, profile_url):
        if self.queue_manager.is_processed(profile_url):
            print(f"Profile {profile_url} already processed. Skipping.")
            return
        
        
        """Scrape LinkedIn posts from a profile URL and enqueue discovered profiles."""
        self.driver.get(profile_url)
        time.sleep(4)

        self.driver.execute_script("window.scrollBy(0, 1000);")  
        time.sleep(2) 

        try:
            self.find_and_click_show_all_posts()
            time.sleep(3) 
        except Exception as e:
            print("Could not find or click 'Show all posts' button:", e)

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached the bottom of the page; all posts should be loaded.")
                break
            last_height = new_height

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        posts = soup.find_all("li", class_="profile-creator-shared-feed-update__container")

        if posts:
            self.queue_manager.mark_processed(profile_url)
            print(f"Marked profile {profile_url} as processed.")

            print(f"Found {len(posts)} posts.")
            for post in posts:
                post_data = {
                    "profile_url": profile_url,
                    "content": None,
                    "date": None,
                    "media_type": None,
                    "likes": 0,
                    "comments": 0
                }
                
                
                content_element = post.select_one("span.break-words.tvm-parent-container > span[dir='ltr']")
                if content_element:
                    post_data["content"] = content_element.get_text("\n", strip=True) 
                
                date_element = post.select_one("span.update-components-actor__sub-description span[aria-hidden='true']")
                if date_element:
                    relative_date_str = date_element.get_text(strip=True).split(" •")[0]
                    post_data["date"] = self.parse_relative_date(relative_date_str).date()
                
                likes_element = post.select_one(".social-details-social-counts__social-proof-fallback-number")
                if likes_element:
                    post_data["likes"] = int(likes_element.get_text(strip=True).replace(",", ""))
                
                
                # Extract comments count
                comments_element = post.select_one("button[aria-label*='comments']")
                if comments_element:
                    post_data["comments"] = int(re.search(r"\d+", comments_element.get_text()).group())
                
                media_types=[]
                if post.select(".update-components-image__container img"):
                    media_types.append("image")
                    
                if post.select("video"):
                    media_types.append("video")               

                post_data["media_type"] = ", ".join(media_types) if media_types else None

                self.db_manager.insert_post(post_data)
                print("Inserted post data into the database:", post_data)


                post_html= str(post)
                profile_urls = self.find_profile_urls_in_post(post_html)
                
                for profile_url in profile_urls:
                    if not self.queue_manager.is_processed(profile_url):
                        self.queue_manager.enqueue_url(profile_url)
                        print(f"Enqueued profile URL: {profile_url}")

        else:
            print("No posts found in the parsed HTML.")
        

    def find_profile_urls_in_post(self, post_html):
        """Extract and clean LinkedIn profile URLs from a given post's HTML content."""
        profile_urls = set()

        soup = BeautifulSoup(post_html, "html.parser")

        profile_links = soup.find_all("a", href=True)

        for link in profile_links:
            profile_url = link["href"]
            
            if "linkedin.com/in/" in profile_url:
                parsed_url = urlparse(profile_url)
                cleaned_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                
                identifier = cleaned_url.split("/")[-2] if cleaned_url.endswith('/') else cleaned_url.split("/")[-1]
                
                if identifier not in profile_urls:
                    profile_urls.add(identifier)

        unique_urls = [f"https://www.linkedin.com/in/{identifier}/" for identifier in profile_urls]

        return unique_urls

    def run(self):
        """Main worker loop to continuously process URLs from the queue."""

        self.session_manager.login()
        while True:
            url = self.queue_manager.dequeue_url()
            if url:
                print(f"Processing URL: {url}")
                self.process_profile(url)
            else:
                print("Queue is empty. Waiting for new URLs...")
                time.sleep(4)  

if __name__ == "__main__":
    
    worker = ProfileWorker()
    worker.run()