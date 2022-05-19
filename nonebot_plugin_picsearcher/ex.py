# -*- coding: utf-8 -*-
from typing import List, Tuple
import io
import random

from PIL import Image
from lxml.html import fromstring
import aiohttp
import nonebot
from aiohttp.client_exceptions import InvalidURL
from nonebot.adapters.onebot.v11 import MessageSegment

from .formdata import FormData

driver = nonebot.get_driver()
cookie: str = getattr(driver.config, "ex_cookie", None)
proxy: str = getattr(driver.config, "proxy", None)
target: str = "https://upld.e-hentai.org/image_lookup.php"

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundaryB0NrMSYMfjY5r0l1',
    'Host': 'e-hentai.org',
    'Origin': 'https://e-hentai.org',
    'Referer': 'https://e-hentai.org/?filesearch=1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'}

if cookie:
    headers['Cookie'] = cookie

def parse_html(html: str):
    """
    解析exhentai返回的数据
    :param html:
    :return:
    """
    selector = fromstring(html)
    hrefs = selector.xpath('//td[@class="gl3c glname"]/a/@href')
    names = selector.xpath('//td[@class="gl3c glname"]/a/div[1]/text()')
    pics = selector.xpath('//tr/td[@class="gl2c"]/div[@class="glthumb"]/div[1]/img/@src')  # 缩略图
    yield from zip(names, hrefs, pics)


async def get_pic_from_url(url: str, target, headers):
    """
    从接受到的picurl获取图片信息
    :param url:
    :return:
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = io.BytesIO(await resp.read())
            # Content_Length = resp.content_length
        data = FormData(boundary="----WebKitFormBoundaryB0NrMSYMfjY5r0l1")
        data.add_field(name="sfile", value=content, content_type="image/jpeg",
                       filename="0.jpg")
        data.add_field(name="f_sfile", value="search")
        data.add_field(name="fs_similar", value="on")
        async with session.post(target, data=data, headers=headers, proxy=proxy) as res:
            html = await res.text()
            print(html)
        return list(parse_html(html))


async def get_content_from_url(url: str):
    """
    从url 获得b64 encode
    :param url:
    :return:
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                img = io.BytesIO(await resp.read())
                im = Image.open(img)
                r, g, b = im.getpixel((0, 0))
                im.putpixel((0, 0), (random.randint(r, r + 3) % 255,
                                     random.randint(g, g + 3) % 255,
                                     random.randint(b, b + 3) % 255))
                im.save(img, 'PNG')
                return img
    except aiohttp.client_exceptions.InvalidURL:
        return url


async def get_des(url: str):
    """
    迭代要发送的信息
    :param url:
    :return:
    """
    image_data: List[Tuple] = await get_pic_from_url(url, target, headers)
    if not image_data:
        if cookie:
            headers_ex = headers.copy()
            headers_ex['Cookie'] = cookie
            headers_ex['Host'] = 'exhentai.org'
            headers_ex['Origin'] = 'https://exhentai.org'
            headers_ex['Referer'] = 'https://exhentai.org/?filesearch=1'
            image_data: List[Tuple] = \
                await get_pic_from_url(url, 'https://exhentai.org/upload/image_lookup.php', headers_ex)
            if not image_data:
                msg: str = "找不到高相似度的"
                yield msg
                return
        else:
            msg: str = "找不到高相似度的"
            yield msg
            return
    for name, href, pic_url in image_data:
        content = await get_content_from_url(pic_url)
        yield MessageSegment.image(file=content) + f"\n本子名称：{name}\n" + f"链接{href}\n"
