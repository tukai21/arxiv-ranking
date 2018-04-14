import re
import os
import sys
import json
import time
import pickle
import numpy as np
from joblib import Parallel, delayed
import requests
from bs4 import BeautifulSoup


sys.setrecursionlimit(100000)


class ScirateScraper:
    """
    Scraping agent class for Scirate.

    Inputs:
        - params: dict, specifies scraping options. Keys are:
            - start: dict, contains starting date for search. Keys are: day, month, year
            - end: dict, contains end date for search. Keys are: day, month, year
            - archive: string, archive type. Currently only "quant-ph" was tested
            - save_by_day: bool, whether it saves papers data day by day. If true, it saves the data in a json format
            - save_dir: string, the directory you save your data to. Only matters when save_by_day is true

    Outputs:
        - results: list, a list of dict for each day within a specified period. Empty when save_by_day is set true


    """
    def __init__(self, params):
        self.start_date = params['start']
        self.end_date = params['end']
        self.archive = params['archive']
        self.save_by_day = params['save_by_day']
        self.save_dir = params['save_dir']

    def start_scraping(self):
        """
        Main scraping function for Scirate.

        Inputs:
            - params: dict, specify search period, archive type, and method. Keys are:
                - start: dict, contains starting date for search. Keys are: day, month, year
                - end: dict, contains end date for search. Keys are: day, month, year
                - method: string, either of "with" or "without" to specify if you want to obtain abstract
                - archive: string, archive type. Currently only "quant-ph" was tested

        Outputs:
            - results: list, a list of dict for each day within a specified period
        """

        url_start = self._get_url(self.start_date)
        url_end = self._get_url(self.end_date)
        date_end = self._parse_date(url_end)
        response = requests.get(url_start)
        soup = BeautifulSoup(response.text, 'lxml')
        date = self._parse_date(url_start)
        results = []

        while date <= date_end:
            papers = self.get_papers_scirate(soup)
            time.sleep(0.1)
            if len(papers) == 0:
                soup, date = self.get_next_page(soup)
                continue
            else:
                res = {
                    'date': date,
                    'papers': papers
                }
                if self.save_by_day:
                    save_path = os.path.join(self.save_dir, date + '_scirate.json')
                    with open(save_path, 'w') as f:
                        json.dump(res, f)
                else:
                    results.append(res)
                soup, date = self.get_next_page(soup)

        return results

    def get_papers_scirate(self, soup):
        papers = []
        paper_list = soup.find_all('li', class_='paper tex2jax')

        for i, paper in enumerate(paper_list):
            title = paper.find('div', class_='title').text
            author_list = paper.find('div', class_='authors').text.split(', ')
            authors = []
            for author in author_list:
                authors.append(author.strip())

            scite_count = int(paper.find('button', class_='btn btn-default count').text)

            paper_info = {
                'title': title,
                'authors': authors,
                'rank': i,
                'scite_count': scite_count
            }
            papers.append(paper_info)

        return papers

    def get_next_page(self, soup):
        nextday = soup.find('td', class_='btn-default half top right').find('a')
        href = nextday.get_attribute_list('href')[0]
        header = 'https://scirate.com'
        url_next = header + href
        response = requests.get(url_next)
        next_page = BeautifulSoup(response.text, 'lxml')
        next_date = self._parse_date(url_next)
        return next_page, next_date

    # helper methods
    def _parse_date(self, url):
        text = url.split('date=')[-1].split('&')[0]
        year, month, day = text.split('-')
        date = 'day_%s_%s_%s' % (year, month, day)
        return date

    def _get_url(self, date):
        if date['day'] < 10:
            day = '0' + str(date['day'])
        else:
            day = str(date['day'])
        if date['month'] < 10:
            month = '0' + str(date['month'])
        else:
            month = str(date['month'])
        year = str(date['year'])

        href = '?date=%s-%s-%s&range=1' % (year, month, day)
        url_base = 'https://scirate.com/arxiv/%s' % self.archive
        url = url_base + href
        return url


if __name__ == '__main__':
    # !!! parameters for ArchiveScraper are stored in `arxiv_config.json` under the `configs` directory.
    params = {'start': {'year': 2018, 'month': 4, 'day': 11},
              'end': {'year': 2018, 'month': 4, 'day': 12},
              'archive': 'quant-ph',
              'save_by_day': False,
              'save_dir': ''
              }

    scraper = ScirateScraper(params)
    results = scraper.start_scraping()
    print('# of days: ', len(results))
    print('First date: ', results[0]['date'])
    print('First paper of the first day: ', results[0]['papers'][0])
    print('Last date: ', results[-1]['date'])
    print('First paper of the last day: ', results[-1]['papers'][0])

    with open('../data/scirate-2018-04-11-2018-04-11.pkl', 'wb') as f:
        pickle.dump(results, f)
