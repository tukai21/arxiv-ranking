import json
from scrapers.arxivscraper import ArxivScraper
from scrapers.sciratescraper import ScirateScraper


if __name__ == '__main__':
    with open('./configs/arxiv_config.json', 'r') as f:
        params_arxiv = json.load(f)
    with open('./configs/scirate_config.json', 'r') as f:
        params_scirate = json.load(f)

    scraper_arxiv = ArxivScraper(params_arxiv)
    scraper_scirate = ScirateScraper(params_scirate)
    scraper_arxiv.start_scraping()
    print('Arxiv Scraping Complete.')
    scraper_scirate.start_scraping()
    print('Scirate Scraping Complete.')
