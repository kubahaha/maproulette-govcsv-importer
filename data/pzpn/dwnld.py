import os

from scrapy import Selector
import requests


def warmaz():
    list_in = open('./warmaz.txt')
    for line in list_in:
        name, url = line.split(';')
        resp = requests.get(url)
        sel = Selector(text=resp.text)

        print(url)
        # print(resp.text)
        # with open('page.html', 'w') as page:
            # page.write(resp.text)
        name = sel.css('.textwidget').extract()[1]
        addr = sel.css('.textwidget').extract()[1]
        stad_name = sel.css('.textwidget').extract()[0]
        capacity = sel.css('.textwidget').extract()[0]
        start_date = sel.css('. ').extract()[1]
        email = sel.css('.textwidget').extract()[1]
        print(sel.css('.textwidget').extract()[0])


warmaz()
