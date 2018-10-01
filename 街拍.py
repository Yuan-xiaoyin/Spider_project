import json
import os
import re
from json import JSONDecodeError
from multiprocessing import Pool
import pymongo
from hashlib import md5
from config import *
import requests
from urllib.parse import urlencode
from IPython.core.display import JSON
from bs4 import BeautifulSoup
from requests import RequestException


client=pymongo.MongoClient(MONGO_URL,connect=False)
db=client[MONGO_DB]

# 得到单个Ajax的数据
def get_one_page(offset,keyword):
    params={
        'offset':offset,
        'format':'json',
        'keyword':keyword,
        'autoload':'true',
        'count':'20',
        'cur_tab':'1',
    }
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"}
    url='https://www.toutiao.com/search_content/?'+urlencode(params)
    try:
        response=requests.get(url,headers=headers)
        if response.status_code==200:
            return response.text
        return None
    except RequestException:
        print("页面请求出错")
        return None
# 解析单页的url
def parse_one_page(html):
    try:
        data=json.loads(html)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:
        pass

# 请求每个url的详情页面
def get_page_detil(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"}
    try:
        response=requests.get(url,headers=headers)
        if response.status_code==200:
            return response.text
        return None
    except RequestException:
        print("详情页面请求出错")
        return None

# 得到每张图片的url
def parse_page_detil(html,url):
     soup=BeautifulSoup(html,'lxml')
     title=soup.select('title')[0].get_text()
     print(title)
     # 通过分析ajax分析，用正则表达式解析得到每张图片的url
     image_pattern=re.compile('gallery: JSON.parse\("(.*?)\"\),\n',re.S)
     result=re.findall(image_pattern,html)
     if result:
         for data in result:
             # 先进行转义，因为现在得到的是字符集的格式，我用的\\转换，还可以用正则进行转换，或者用json进行解析
             data=data.replace('\\',"")
             # 将得到的数据转换为json对象
             data=json.loads(data)
             # 通过分析可以知道，每张图片的url是在sub_images这个字典中的，判断得到的数据是否有sub_images这个键
             if data and 'sub_images' in data.keys():
                 sub_images=data.get('sub_images')
                 # 遍历得到每张图片的url
                 images=[item.get('url') for item in sub_images]
                 # 调用下载图片的函数,下载图片
                 for image in images:
                     download_image(image)
                 return {
                     "title":title,
                     "url":url,
                     "images":images,
                 }
# 下载图片
def download_image(url):
    print('正在下载图片',url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            save_image(response.content)
            return response.text
        return None
    except RequestException:
        print("下载图片请求出错",url)
        return None
# 保存图片
def save_image(content):
    file_path='{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)

#将得到的数据保存到mongo数据库
def save_to_Mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到Mongo成功',result)
        return True
    return False


# 主函数
def main(offset):
    html=get_one_page(offset,keyword)
    for url in parse_one_page(html):
        html=get_page_detil(url)
        if html:
            result=parse_page_detil(html,url)
            if result:
                save_to_Mongo(result)


if __name__=="__main__":

    groups=[x*20 for x in range(GROUP_START,END_START)]
    pool=Pool()
    pool.map(main,groups)




