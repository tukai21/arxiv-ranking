import time
import pickle
import numpy as np
import requests
from bs4 import BeautifulSoup


# TODO: add an option for obtaining abstract for each paper


def scrape_arxiv(params):
    url_start = get_url(params['start'], params['archive'], params['method'])
    date_end = parse_date(params['end'])

    response = requests.get(url_start)
    soup = BeautifulSoup(response.text, 'lxml')

    results, next_page = parse_page(soup, date_end)
    while next_page:
        res, next_page = parse_page(next_page, date_end)
        results += res

        time.sleep(0.1)

    return results


def parse_date(date):
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
    url = 'https://arxiv.org/catchup?'
    url += 'smonth=%d&'  % date['month']
    url += 'sday=%d&'    % date['day']
    url += 'group=grp_&'
    url += 'archive=%s&' % archive
    url += 'num=50&'
    url += 'method=%s&'  % method
    url += 'syear=%d'    % date['year']
    return url


def parse_page(soup, date_end):
    results = []

    headers = soup.find_all('h2')
    if len(headers) == 0:
        return results, None

    for h2 in headers:
        date = h2.find('a').get_attribute_list('name')[0]
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
    next_page = soup.find_all('li')[-1]
    link = next_page.find('a').get_attribute_list('href')[0]
    url_next = url_header + link
    response = requests.get(url_next)
    next_page = BeautifulSoup(response.text, 'lxml')
    return next_page


def get_papers(soup):
    paper_list = soup.find_all('dd')
    meta_list = soup.find_all('dt')

    papers = []
    for i, (paper, meta) in enumerate(zip(paper_list, meta_list)):
        meta_info = meta.find('span', class_='list-identifier')
        if 'replaced' in meta_info.text or 'cross-list' in meta_info.text:
            continue

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
