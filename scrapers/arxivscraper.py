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


class ArxivScraper:
    """
    Scraping agent class for Arxiv.

    Inputs:
        - params: dict, specifies scraping options. Keys are:
            - start: dict, contains starting date for search. Keys are: day, month, year
            - end: dict, contains end date for search. Keys are: day, month, year
            - abstract: bool, specify if you want to obtain abstract
            - archive: string, archive type. Currently only "quant-ph" was tested
            - parallel: bool, whether it parses each paper info in parallel
            - save_by_day: bool, whether it saves papers data day by day. If true, it saves the data in a json format
            - save_dir: string, the directory you save your data to. Only matters when save_by_day is true

    Outputs:
        - results: list, a list of dict for each day within a specified period. Empty when save_by_day is set true


    """
    def __init__(self, params):
        self.url_header = 'https://arxiv.org'
        self.start_date = params['start']
        self.end_date = params['end']
        self.abstract = params['abstract']
        self.archive = params['archive']
        self.parallel = params['parallel']
        self.save_by_day = params['save_by_day']
        self.save_dir = params['save_dir']

        self.date_pattern = '\w{3}, \d+ \w{3} 20\d{2} \d{2}:\d{2}:\d{2}'
        self.weekday_pattern = r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
        self.time_pattern = '\d{2}:\d{2}:\d{2}'

    def start_scraping(self):
        # obtain starting url
        url_start = self._get_url(self.start_date)

        # compute end date for search
        date_end = self._parse_date(self.end_date)

        # get html from the url by requests
        response = requests.get(url_start)
        # prepare parser
        soup = BeautifulSoup(response.text, 'lxml')

        # parse first page
        results, next_page = self.parse_page(soup, date_end)

        # until no more page appears:
        while next_page:
            res, next_page = self.parse_page(next_page, date_end)
            results += res

            # this is not to send requests too much - avoid IP ban
            time.sleep(0.2)

        return results

    def parse_page(self, soup, date_end):
        # parse html (soup) and return papers and next page html
        results = []

        # find all the dates in this page
        headers = soup.find_all('h2')
        if len(headers) == 0:
            return results, None

        for h2 in headers:
            date = h2.find('a').get_attribute_list('name')[0]
            # if the date exceeds end date for search, terminate parsing
            if date > date_end:
                return results, None

            paper_data = h2.find_next_siblings()[0]
            papers = self.get_papers(paper_data)
            res = {
                'date': date,
                'papers': papers
            }
            if self.save_by_day:
                save_path = os.path.join(self.save_dir, date + '_arxiv.json')
                with open(save_path, 'w') as f:
                    json.dump(res, f)
            else:
                results.append(res)

        next_page = self.get_next_page(soup)
        return results, next_page

    def get_papers(self, soup):
        ident_list = soup.find_all('dt')
        meta_list = soup.find_all('dd')

        ident_info = [item.find('span', class_='list-identifier') for item in ident_list]
        indices = [i for i, m in enumerate(ident_info) if (m.text != 'replaced') and (m.text != 'cross_list')]

        paper_list = [{'identifier': ident_info[i],
                       'meta': meta_list[i],
                       'order': i}
                      for i in indices]

        # parallel paper information retrieval for all the papers in a day
        if self. parallel:
            papers = Parallel(n_jobs=-1)([delayed(self.get_paper_info)(paper) for paper in paper_list])
        else:
            papers = list(map(self.get_paper_info, paper_list))

        return papers

    def get_paper_info(self, paper):
        title = paper['meta'].find('div', class_='list-title mathjax').text.split('\nTitle: ')[1].split('\n')[0]
        author_list = np.array(paper['meta'].find('div', class_='list-authors').text.split('\n'))[2:-1]
        authors = []
        for author in author_list:
            authors.append(author.split(',')[0])

        # parse the paper's abstract page
        paper_href = paper['identifier'].find('a', title='Abstract').get_attribute_list('href')[0]
        paper_link = self.url_header + paper_href
        response = requests.get(paper_link)

        # this is not to send requests too much - avoid IP ban
        time.sleep(0.2)

        soup = BeautifulSoup(response.text, 'lxml')

        # get abstract when the abstract option is set true
        abstract = ''
        if self.abstract:
            for s in soup.find('blockquote').text.split('\n'):
                abstract += s

        # comments = soup.find('td', class_='tablecell comments mathjax')
        # if comments:
        #     text = comments.text
        #     pages = re.findall('\d+ pages', text)[0]
        #     num_pages = int(re.findall('\d+', pages)[0])
        # else:
        #     num_pages = -1  # missing value handling

        num_versions = len(soup.find_all('b'))

        # paper submit time and paper size
        latest_submit = soup.find('div', class_='submission-history').text.split('\n')[-2]
        match = re.findall(self.date_pattern, latest_submit)
        if len(match) > 0:
            submit_weekday = re.findall(self.weekday_pattern, match[0])[0]
            submit_time = re.findall(self.time_pattern, match[0])[0]
        else:
            submit_weekday = 'none'
            submit_time = 'none'
        size = re.findall('[0-9]+[a-z]b', latest_submit)[0]

        paper_info = {
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'order': paper['order'],
            # 'num_pages': num_pages,
            'num_versions': num_versions,
            'submit_weekday': submit_weekday,
            'submit_time': submit_time,
            'size': size,
            'paper_link': paper_link
        }
        return paper_info

    def get_next_page(self, soup):
        next_page = soup.find_all('li')[-1]
        link = next_page.find('a').get_attribute_list('href')[0]

        # form next url and send request
        url_next = self.url_header + link
        response = requests.get(url_next)

        # prepare parser for the next page html
        next_page = BeautifulSoup(response.text, 'lxml')
        return next_page

    # helper methods
    def _parse_date(self, date):
        # parse date from a given parameters to generate date string
        if date['day'] < 10:
            day = '0' + str(date['day'])
        else:
            day = str(date['day'])
        if date['month'] < 10:
            month = '0' + str(date['month'])
        else:
            month = str(date['month'])
        year = str(date['year'])
        return 'day_%s_%s_%s' % (year, month, day)

    def _get_url(self, date):
        # url generation given parameters for accessing the first page
        url = 'https://arxiv.org/catchup?'
        url += 'smonth=%d&' % date['month']
        url += 'sday=%d&' % date['day']
        url += 'group=grp_&'
        url += 'archive=%s&' % self.archive
        url += 'num=50&'
        url += 'method=without&'
        url += 'syear=%d' % date['year']
        return url


if __name__ == '__main__':
    # !!! parameters for ArchiveScraper are stored in `arxiv_config.json` under the `configs` directory.
    params = {'start': {'year': 2018, 'month': 3, 'day': 13},
              'end': {'year': 2018, 'month': 3, 'day': 14},
              'archive': 'quant-ph',
              'abstract': True,
              'parallel': False,
              'save_by_day': False,
              'save_dir': ''
              }

    scraper = ArxivScraper(params)
    results = scraper.start_scraping()
    print('# of days: ', len(results))
    print('First date: ', results[0]['date'])
    print('First paper of the first day: ', results[0]['papers'][0])
    print('Last date: ', results[-1]['date'])
    print('First paper of the last day: ', results[-1]['papers'][0])

    # with open('../data/arxiv-2018-04-11-2018-04-11.pkl', 'wb') as f:
    #     pickle.dump(results, f)
