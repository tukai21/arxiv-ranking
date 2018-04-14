import os
import time
import json
import pickle
import warnings
import requests
from bs4 import BeautifulSoup


msg = 'This module is deprecated. Users are recommended to use "sciratescraper.py" instead.'
warnings.warn(msg, warnings, DeprecationWarning, stacklevel=2)


def scrape_scirate(params):
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

    url_start = get_url(params['start'], params['archive'])
    url_end = get_url(params['end'], params['archive'])
    date_end = parse_date(url_end)
    response = requests.get(url_start)
    soup = BeautifulSoup(response.text, 'lxml')
    date = parse_date(url_start)
    results = []

    while date <= date_end:
        papers = get_papers_scirate(soup)
        time.sleep(0.1)
        if len(papers) == 0:
            soup, date = get_next_page(soup)
            continue
        else:
            res = {
                'date': date,
                'papers': papers
            }
            if params['save_by_day']:
                save_path = os.path.join(params['save_by_day'], date + '_scirate.json')
                with open(save_path, 'w') as f:
                    json.dump(res, f)
            else:
                results.append(res)
            soup, date = get_next_page(soup)

    return results


def get_url(date, archive):
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
    url_base = 'https://scirate.com/arxiv/%s' % archive
    url = url_base + href
    return url


def parse_date(url):
    text = url.split('date=')[-1].split('&')[0]
    year, month, day = text.split('-')
    date = 'day_%s_%s_%s' % (year, month, day)
    return date


def get_papers_scirate(soup):
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


def get_next_page(soup):
    nextday = soup.find('td', class_='btn-default half top right').find('a')
    href = nextday.get_attribute_list('href')[0]
    header = 'https://scirate.com'
    url_next = header + href
    response = requests.get(url_next)
    next_page = BeautifulSoup(response.text, 'lxml')
    next_date = parse_date(url_next)
    return next_page, next_date


if __name__ == '__main__':
    params = {'start': {'year': 2018, 'month': 4, 'day': 11},
              'end': {'year': 2018, 'month': 4, 'day': 12},
              'archive': 'quant-ph',
              'method': 'without',
              'save_by_day': False,
              'save_dir': ''
              }

    results = scrape_scirate(params)
    print('# of days: ', len(results))
    print('First date: ', results[0]['date'])
    print('First paper of the first day: ', results[0]['papers'][0])
    print('Last date: ', results[-1]['date'])
    print('First paper of the last day: ', results[-1]['papers'][0])

    with open('../data/scirate-2018-04-11-2018-04-12.pkl', 'wb') as f:
        pickle.dump(results, f)
