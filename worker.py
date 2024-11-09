# worker.py
from session_manager import LinkedInSessionManager
from queue_manager import QueueManager
from database_manager import DatabaseManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from bs4 import BeautifulSoup
import time

class ProfileWorker:
    def __init__(self):
        self.session_manager = LinkedInSessionManager()
        self.queue_manager = QueueManager()
        self.db_manager = DatabaseManager()  
        self.driver = self.session_manager.init_driver()

    def process_profile(self, profile_url):
        """Scrape LinkedIn posts from a profile URL and enqueue discovered profiles."""
        self.driver.get(profile_url)
        time.sleep(4)

        self.driver.execute_script("window.scrollBy(0, 1000);")  
        time.sleep(2) 

        try:
            show_all_posts_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[6]/div[3]/div/div/div[2]/div/div/main/section[4]/footer/a/span"))
        )

            self.driver.execute_script("arguments[0].click();", show_all_posts_button)
            print("Clicked on 'Show all posts' button.")
            time.sleep(4)  


        except Exception as e:
            print("Could not find or click 'Show all posts' button:", e)


        # Scroll down to ensure all posts are loaded
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for new posts to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            # Once the page is fully loaded, get the HTML source
            page_source = self.driver.page_source

            # Use BeautifulSoup to parse the HTML
            soup = BeautifulSoup(page_source, "html.parser")

            # Find all posts within the main posts container
            posts_container = soup.select_one("#profile-content > div > div.scaffold-layout.scaffold-layout--breakpoint-none.scaffold-layout--sidebar-main-aside.scaffold-layout--single-column.scaffold-layout--reflow > div > div > main > div > section > div.pv0.ph5 > div > div > div.scaffold-finite-scroll__content > ul")
            
            # If posts are present, loop through each post
            if posts_container:
                posts = posts_container.find_all("li")  # Each `li` represents a post

                for post in posts:
                    # Initialize post data
                    post_data = {
                        "profile_url": profile_url,
                        "content": None,
                        "date": None,
                        "media_type": None,
                        "likes": 0,
                        "comments": 0
                    }

                    # Extract content
                    content = post.select_one("span.break-words")
                    if content:
                        post_data["content"] = content.get_text(strip=True)

                    # Extract date
                    date = post.select_one("span[aria-hidden='true']")
                    if date:
                        post_data["date"] = date.get_text(strip=True)

                    # Extract likes
                    likes = post.select_one("button > span[aria-label*='like']")
                    if likes:
                        post_data["likes"] = int(likes.get_text(strip=True).replace(",", ""))

                    # Extract comments
                    comments = post.select_one("button > span[aria-label*='comment']")
                    if comments:
                        post_data["comments"] = int(comments.get_text(strip=True).replace(",", ""))

                    # Check for media (image or video)
                    media = post.select_one("img") or post.select_one("video")
                    post_data["media_type"] = "image" if media and media.name == "img" else "video" if media else None

                    # Insert post data into the database or handle it as needed
                    self.db_manager.insert_post(post_data)
                    print("Inserted post data into the database:", post_data)

                    # Find and enqueue profile URLs (mentioned users or reposted content)
                    profile_urls = self.find_profile_urls_in_post(post)
                    for profile_url in profile_urls:
                        if not self.queue_manager.is_processed(profile_url):
                            self.queue_manager.enqueue_url(profile_url)
                            print(f"Enqueued profile URL: {profile_url}")

    def find_profile_urls_in_post(self, post_container):
        """Find and return LinkedIn profile URLs from a given post container."""
        profile_urls = []

        try:
            # Locate all anchor tags within the post that could contain profile links
            profile_links = post_container.find_elements(By.XPATH, ".//a[contains(@href, 'linkedin.com/in/')]")

            for link in profile_links:
                profile_url = link.get_attribute("href")
                if profile_url and profile_url not in profile_urls:
                    profile_urls.append(profile_url)
        except Exception as e:
            print("Error finding profile URLs in post:", e)

        return profile_urls



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