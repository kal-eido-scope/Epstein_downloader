from requests import Session
from requests.adapters import HTTPAdapter, Retry

def get_default_session() -> Session:
    """配置并返回默认的HTTP会话"""
    session = Session()
    retries = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        'Referer': 'https://www.justice.gov/epstein/doj-disclosures',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'cookie': 'justiceGovAgeVerified=true'
    }
    session.headers.update(headers)
    return session

default_session = get_default_session()