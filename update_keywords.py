import json
from datetime import datetime, timedelta

import requests

keywords = []


current_date = datetime.now().strftime('%Y%m%d')
for i in range(30):
    date = datetime.now() - timedelta(days=i)
    formatted_date = date.strftime('%Y%m%d')
    url = f'https://trends.google.com/trends/api/dailytrends?geo=US&hl=en&ed={formatted_date}&ns=15'

    headers = {
        'Content-Type': 'application/json'
    }
    res = requests.get(url,headers=headers)

    content = res.content

    json_data =  json.loads(content[5:])

    topics = json_data['default']['trendingSearchesDays'][0]['trendingSearches']

    for topic in topics:
        title = topic['title']['query']
        if title not in keywords:
            keywords.append(title)

with open('keywords.txt', 'w') as f:
    f.write('\n'.join(keywords))
