"""Instagram reel scraper using Selenium."""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import json
import re
from typing import List, Dict, Optional
from datetime import datetime
from backend.config import settings


class InstagramScraper:
    """Scraper for Instagram reels."""

    def __init__(self):
        """Initialize the scraper with Chrome WebDriver."""
        self.driver: Optional[webdriver.Chrome] = None

    def _init_driver(self):
        """Initialize Chrome WebDriver with anti-detection settings."""
        chrome_options = ChromeOptions()

        # Headless mode for server environments
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Realistic user agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Use custom driver path if provided, otherwise auto-install
        if settings.SELENIUM_DRIVER_PATH:
            service = ChromeService(executable_path=settings.SELENIUM_DRIVER_PATH)
        else:
            service = ChromeService(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Hide webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def _close_driver(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add a random delay to mimic human behavior."""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _extract_reel_data_from_element(self, element) -> Optional[Dict]:
        """
        Extract reel data from a DOM element.

        Args:
            element: Selenium WebElement

        Returns:
            Dictionary with reel data or None if extraction fails
        """
        try:
            # Try to extract reel URL
            link_elem = element.find_element(By.TAG_NAME, "a")
            reel_url = link_elem.get_attribute("href")

            if not reel_url or "/reel/" not in reel_url:
                return None

            # Extract reel ID from URL
            reel_id_match = re.search(r'/reel/([^/\?]+)', reel_url)
            if not reel_id_match:
                return None

            instagram_reel_id = reel_id_match.group(1)

            # Try to extract thumbnail
            thumbnail_url = None
            try:
                img_elem = element.find_element(By.TAG_NAME, "img")
                thumbnail_url = img_elem.get_attribute("src")
            except NoSuchElementException:
                pass

            # For now, return basic data
            # Full metadata will be extracted when user clicks on reel (future enhancement)
            return {
                "instagram_reel_id": instagram_reel_id,
                "reel_url": reel_url if reel_url.startswith("http") else f"https://www.instagram.com{reel_url}",
                "thumbnail_url": thumbnail_url,
                "video_url": None,  # Would need to open reel page to get this
                "caption": None,  # Would need to parse from reel page
                "author_username": "unknown",  # Would need to parse from reel page
                "like_count": 0,
                "view_count": 0,
                "instagram_comment_count": 0,
                "post_date": datetime.utcnow()  # Placeholder
            }

        except Exception as e:
            print(f"Error extracting reel data: {e}")
            return None

    def scrape_reels(self, query: str) -> List[Dict]:
        """
        Scrape Instagram reels for a given search query.

        Args:
            query: Search keyword

        Returns:
            List of dictionaries containing reel data

        Raises:
            WebDriverException: If scraping fails
        """
        reels_data = []

        try:
            # Initialize driver
            self._init_driver()

            # Navigate to Instagram explore/tags page for keyword
            search_url = f"https://www.instagram.com/explore/tags/{query.replace(' ', '')}/"
            print(f"Navigating to: {search_url}")
            self.driver.get(search_url)

            # Wait for page to load
            self._random_delay(2, 4)

            # Scroll to load more content
            scroll_count = 3
            for i in range(scroll_count):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._random_delay(1, 2)

            # Try to find reel elements
            # Instagram's structure changes frequently, so we use multiple strategies
            possible_selectors = [
                "article a[href*='/reel/']",
                "div a[href*='/reel/']",
                "a[href*='/reel/']"
            ]

            reel_elements = []
            for selector in possible_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        reel_elements = elements
                        break
                except NoSuchElementException:
                    continue

            # Extract data from found elements
            seen_ids = set()
            for element in reel_elements[:settings.MAX_SEARCH_RESULTS]:
                reel_data = self._extract_reel_data_from_element(element)

                if reel_data and reel_data["instagram_reel_id"] not in seen_ids:
                    seen_ids.add(reel_data["instagram_reel_id"])
                    reels_data.append(reel_data)

            print(f"Scraped {len(reels_data)} reels for query: {query}")

        except TimeoutException:
            print(f"Timeout while scraping Instagram for query: {query}")
            raise WebDriverException("Instagram page took too long to load")

        except Exception as e:
            print(f"Error scraping Instagram: {e}")
            raise WebDriverException(f"Failed to scrape Instagram: {str(e)}")

        finally:
            # Always close the driver
            self._close_driver()

        return reels_data


# Global scraper instance
_scraper = None


def get_scraper() -> InstagramScraper:
    """Get or create the global scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = InstagramScraper()
    return _scraper
