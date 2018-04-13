import time
import pickle
import numpy as np
import requests
from bs4 import BeautifulSoup


# TODO: add an option for obtaining abstract for each paper


def scrape_arxiv(params):
    """
    Main scraping function for Arxiv.

    Inputs:
        - params: dict, specify search period, archive type, and method. Keys are:
            - start: dict, contains starting date for search. Keys are: day, month, year
            - end: dict, contains end date for search. Keys are: day, month, year
            - method: string, either of "with" or "without" to specify if you want to obtain abstract
            - archive: string, archive type. Currently only "quant-ph" was tested

    Outputs:
        - results: list, a list of dict for each day within a specified period
    """

    # obtain starting url
    url_start = get_url(params['start'], params['archive'], params['method'])

    # compute end date for search
    date_end = parse_date(params['end'])

    # get html from the url by requests
    response = requests.get(url_start)
    # prepare parser
    soup = BeautifulSoup(response.text, 'lxml')

    # parse first page
    results, next_page = parse_page(soup, date_end)

    # until no more page appears:
    while next_page:
        res, next_page = parse_page(next_page, date_end)
        results += res

        # this is not to send requests too much - avoid IP ban
        time.sleep(0.1)

    return results


def parse_page(soup, date_end):
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
        papers = get_papers(paper_data)
        results.append({
            'date': date,
            'papers': papers
        })

    next_page = get_next_page(soup)
    return results, next_page


def get_next_page(soup, url_header='https://arxiv.org'):
    # find next page section in the html and get href link
    next_page = soup.find_all('li')[-1]
    link = next_page.find('a').get_attribute_list('href')[0]

    # form next url and send request
    url_next = url_header + link
    response = requests.get(url_next)

    # prepare parser for the next page html
    next_page = BeautifulSoup(response.text, 'lxml')
    return next_page


def get_papers(soup):
    # find all the papers and corresponding meta information
    paper_list = soup.find_all('dd')
    meta_list = soup.find_all('dt')

    papers = []
    for i, (paper, meta) in enumerate(zip(paper_list, meta_list)):
        # if meta data says it is either of "Replaced" or "Cross-List", ignore the paper
        meta_info = meta.find('span', class_='list-identifier')
        if 'replaced' in meta_info.text or 'cross-list' in meta_info.text:
            continue

        # get title and authors
        title = paper.find('div', class_='list-title mathjax').text.split('\nTitle: ')[1].split('\n')[0]
        author_list = np.array(paper.find('div', class_='list-authors').text.split('\n'))[2:-1]
        authors = []
        for author in author_list:
            authors.append(author.split(',')[0])
        paper_info = {
            'title': title,
            'authors': authors,
            'order': i
        }
        papers.append(paper_info)

    return papers


def parse_date(date):
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


def get_url(date, archive, method):
    # url generation given parameters for accessing the first page
    url = 'https://arxiv.org/catchup?'
    url += 'smonth=%d&'  % date['month']
    url += 'sday=%d&'    % date['day']
    url += 'group=grp_&'
    url += 'archive=%s&' % archive
    url += 'num=50&'
    url += 'method=%s&'  % method
    url += 'syear=%d'    % date['year']
    return url


if __name__ == '__main__':
    params = {'start': {'year': 2018, 'month': 3, 'day': 1},
              'end': {'year': 2018, 'month': 4, 'day': 1},
              'archive': 'quant-ph',
              'method': 'without'
              }

    results = scrape_arxiv(params)
    print('# of days: ', len(results))
    print('First date: ', results[0]['date'])
    print('First paper of the first day: ', results[0]['papers'][0])
    print('Last date: ', results[-1]['date'])
    print('First paper of the last day: ', results[-1]['papers'][0])

    with open('../data/arxiv-2018-03-01-2018-04-01.pkl', 'wb') as f:
        pickle.dump(results, f)
