import requests
from concurrent.futures import ThreadPoolExecutor
import threading
from urllib.parse import urljoin
url = "http://127.0.0.1:8000/concurrency/buy/"

def buy_item(id):
    response = requests.post(url + str(id))
    print(response.status_code,response.text)

# x = threading.Thread(target=buy_item, args=1)
# x.start()
# x.join()

with ThreadPoolExecutor(max_workers=100) as executor:
    for i in range(100):
        executor.submit(buy_item,1)