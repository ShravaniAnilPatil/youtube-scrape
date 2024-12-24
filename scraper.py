import os
import time
import random
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from googleapiclient.discovery import build

API_KEY = ''  
youtube = build('youtube', 'v3', developerKey=API_KEY)
def search_videos(genre, max_results=500):
    """Search for videos on YouTube using Selenium and return video links, excluding Shorts."""
    driver = uc.Chrome()
    driver.get("https://www.youtube.com")

    search_box = driver.find_element(By.NAME, "search_query")
    search_box.send_keys(genre)
    search_box.send_keys(Keys.RETURN)
    time.sleep(3) 

    video_links = set()
    while len(video_links) < max_results:
        videos = driver.find_elements(By.XPATH, '//a[@id="video-title"]')
        for video in videos:
            link = video.get_attribute("href")
          
            if link and '/watch?v=' in link:
                video_links.add(link)
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(random.uniform(1.5, 3.0))  

    driver.quit()
    return list(video_links)[:max_results]


def fetch_api_data(video_id):
    """Fetch additional video details using the YouTube API."""
    try:
        response = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        ).execute()

        if "items" in response and len(response["items"]) > 0:
            item = response["items"][0]
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            return {
                "Category": snippet.get("categoryId"),
                "Topic Details": snippet.get("tags"),
                "Views": statistics.get("viewCount"),
                "Comment Count": statistics.get("commentCount"),
                "Published Date": snippet.get("publishedAt"),
            }
    except Exception as e:
        print(f"API error for video ID {video_id}: {e}")

    return {
        "Category": None,
        "Topic Details": None,
        "Views": None,
        "Comment Count": None,
        "Published Date": None,
    }

def extract_video_details(video_url):
    """Scrape video details using Selenium."""
    driver = uc.Chrome()
    driver.get(video_url)

    try:
        title = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//yt-formatted-string[@class="style-scope ytd-watch-metadata"]'))
        ).text

        try:
            description_element = driver.find_element(
                By.XPATH,
                '//div[@id="description"]//span[@class="yt-core-attributed-string--link-inherit-color"]'
            )
            description = description_element.text
        except NoSuchElementException:
            description = None

        channel = driver.find_element(By.XPATH, '//a[@class="yt-simple-endpoint style-scope yt-formatted-string"]').text
        try:
            duration = driver.find_element(By.CLASS_NAME, 'ytp-time-duration').text
        except NoSuchElementException:
            duration = None
        try:
            keywords = driver.find_element(By.XPATH, '//meta[@name="keywords"]').get_attribute("content")
        except NoSuchElementException:
            keywords = None

        try:
            captions_text = driver.find_element(By.XPATH, '//ytd-engagement-panel-title-header-renderer').text
            captions_available = "true" if "captions" in captions_text.lower() else "false"
        except NoSuchElementException:
            captions_available = "false"
        try:
            location = driver.find_element(By.XPATH, '//span[@class="style-scope ytd-metadata-row-renderer"]').text
        except NoSuchElementException:
            location = None

    except TimeoutException:
        print(f"Timeout loading details for {video_url}")
        title = description = channel = duration = keywords = captions_available = location = None

    driver.quit()

    return {
        "Video URL": video_url,
        "Title": title,
        "Description": description,
        "Channel Title": channel,
        "Duration": duration,
        "Keywords": keywords,
        "Captions Available": captions_available,
        "Location": location,
    }
def scrape_youtube_videos(genre, max_results=50, output_file="output.csv"):
    """Scrape YouTube videos using API and Selenium, and save details to a CSV file in parallel."""
    video_links = search_videos(genre, max_results)
    column_order = [
        "Video URL",
        "Title",
        "Description",
        "Channel Title",
        "Keywords",
        "Category",
        "Topic Details",
        "Published Date",
        "Duration",
        "Views",
        "Comment Count",
        "Captions Available",
        "Location",
    ]
    if not os.path.exists(output_file):
        pd.DataFrame(columns=column_order).to_csv(output_file, index=False)

    for index, video_url in enumerate(video_links):
        print(f"Processing {index + 1}/{len(video_links)}: {video_url}")

        video_id = video_url.split("v=")[-1].split("&")[0]
        api_data = fetch_api_data(video_id)
        selenium_data = extract_video_details(video_url)
        combined_data = {**selenium_data, **api_data}

       
        pd.DataFrame([combined_data])[column_order].to_csv(output_file, mode='a', header=False, index=False)
        time.sleep(random.uniform(2.0, 5.0)) 
    print(f"Data scraping completed. Results saved to {output_file}")

if __name__ == "__main__":
    genre = input("Enter the genre: ")
    max_results = int(input("Enter the number of videos to scrape: "))
    scrape_youtube_videos(genre, max_results)
