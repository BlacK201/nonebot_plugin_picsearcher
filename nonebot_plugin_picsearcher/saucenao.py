# -*- coding: utf-8 -*-
import io
import random
from typing import List, Tuple
from PIL import Image

import aiohttp
from lxml.html import fromstring
from nonebot.adapters.onebot.v11 import MessageSegment

from .formdata import FormData
from .proxy import proxy

header = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryPpuR3EZ1Ap2pXv8W",
    'Connection': 'keep-alive',
    'Host': 'saucenao.com', 'Origin': 'https://saucenao.com', 'Referer': 'https://saucenao.com/index.php',
    'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'}

def parse_html(html: str):
    """
    解析nao返回的html
    :param html:
    :return:
    """
    selector = fromstring(html)
    for tag in selector.xpath('//div[@class="result"]/table'):
        pic_url = tag.xpath('./tr/td/div/a/img/@src')
        pic_url = pic_url[0] if pic_url else None
        xsd: List[str] = tag.xpath(
            './tr/td[@class="resulttablecontent"]/div[@class="resultmatchinfo"]/div[@class="resultsimilarityinfo"]/text()')
        xsd = xsd[0] if xsd else "没有写"
        title: List[str] = tag.xpath(
            './tr/td[@class="resulttablecontent"]/div[@class="resultcontent"]/div[@class="resulttitle"]/strong/text()')
        title = title[0] if title else "没有写"
        # pixiv id
        pixiv_id: List[str] = tag.xpath(
            './tr/td[@class="resulttablecontent"]/div[@class="resultcontent"]/div[@class="resultcontentcolumn"]/a[1]/@href')
        pixiv_id = pixiv_id[0] if pixiv_id else "没有说"
        member: List[str] = tag.xpath(
            './tr/td[@class="resulttablecontent"]/div[@class="resultcontent"]/div[@class="resultcontentcolumn"]/a[2]/@href')
        member = member[0] if member else "没有说"
        yield pic_url, xsd, title, pixiv_id, member


async def get_pic_from_url(url: str):
    """
    从url搜图
    :param url:
    :return:
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = io.BytesIO(await resp.read())
        data = FormData(boundary="----WebKitFormBoundaryPpuR3EZ1Ap2pXv8W")
        data.add_field(name="file", value=content, content_type="image/jpeg",
                       filename="blob")
        async with session.post("https://saucenao.com/search.php", data=data, headers=header, proxy=proxy) as res:
            html = await res.text()
            image_data = list(parse_html(html))
    return image_data


async def get_des(url: str):
    image_data: List[Tuple] = await get_pic_from_url(url)
    if not image_data:
        msg: str = "找不到高相似度的"
        yield msg
        return
    for pic in image_data:
        async with aiohttp.ClientSession() as session:
            async with session.get(pic[0], headers=headers) as resp:
                print(pic[0])
                img = io.BytesIO(await resp.read())
                im = Image.open(img)
                origin_mode = im.mode
                if not im.mode == "RGB":
                    im = im.convert("RGB")
                r, g, b = im.getpixel((0, 0))
                im.putpixel((0, 0), (random.randint(r, r + 3) % 255,
                                     random.randint(g, g + 3) % 255,
                                     random.randint(b, b + 3) % 255))
                if not im.mode == origin_mode:
                    im = im.convert(origin_mode)
                im.save(img, 'PNG')
        yield MessageSegment.image(file=img) + f"\n相似度:{pic[1]}\n标题:{pic[2]}\npixivid:{pic[3]}\nmember:{pic[4]}\n"
