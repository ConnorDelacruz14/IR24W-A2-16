from threading import Thread

from inspect import getsource
from utils.download import download
from utils import get_logger
from urllib.parse import urlparse
import scraper
import time


class Worker(Thread):
    def __init__(self, worker_id, config, frontier):
        self.logger = get_logger(f"Worker-{worker_id}", "Worker")
        self.config = config
        self.frontier = frontier
        # basic check for requests in scraper
        assert {getsource(scraper).find(req) for req in {"from requests import", "import requests"}} == {-1}, "Do not use requests in scraper.py"
        assert {getsource(scraper).find(req) for req in {"from urllib.request import", "import urllib.request"}} == {-1}, "Do not use urllib.request in scraper.py"
        super().__init__(daemon=True)
        
    def run(self):
        while True:
            tbd_url = self.frontier.get_tbd_url()
            if not tbd_url:
                self.logger.info("Frontier is empty. Stopping Crawler.")
                break

            # Implementing multithreading wait
            # Recheck in the frontier if the current website has been crawled recently, if it has not met the time delay, proceed the delay
            # and then scrape
            current_netloc = urlparse(tbd_url).netloc
            last_crawl_time = self.frontier.get_last_crawl_time(current_netloc)
            time_since_last_crawl = time.time() - last_crawl_time

            if time_since_last_crawl < self.config.time_delay:
                time.sleep(self.config.time_delay - time_since_last_crawl)

            resp = download(tbd_url, self.config, self.logger)
            self.logger.info(
                f"Downloaded {tbd_url}, status <{resp.status}>, "
                f"using cache {self.config.cache_server}.")
            scraped_urls = scraper.scraper(tbd_url, resp)
            for scraped_url in scraped_urls:
                self.frontier.add_url(scraped_url)
            self.frontier.mark_url_complete(tbd_url)

            self.frontier.set_last_crawl_time(current_netloc, time.time())
            time.sleep(self.config.time_delay)
