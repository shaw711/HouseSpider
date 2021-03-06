#encoding=utf-8
import sys

sys.path.append("..")
from scrapy.spiders import Spider
from lxml import html
import plug
from plug.utils import StringUtil,NumberUtil
from ershoufang.items import HouseItem
import re
import scrapy
import time
import pymongo
from scrapy.utils.project import get_project_settings
class erShouSpider(Spider):
	name = "ershoufang2"
	allowed_domains = ["58.com"]
	
	def __init__(self):
		super(erShouSpider,self).__init__()
		self.settings = get_project_settings()
		self.client = pymongo.MongoClient(
																self.settings['MONGO_IP'],
																self.settings['MONGO_PORT'])
		self.cities_db = self.client[self.settings['CITY_DB']]
		self.cities_Col = self.cities_db[self.settings['CITY_COL']]
		self.fillurl=""
		self.cityhost=""
		self.city=""
	def get_specify_request(self):
		#返回指定的请求
		condition = {"city":self.settings['CITY']}
		if self.settings['PROVIENCE'] and self.settings['PROVIENCE']!="":
			condition = {"city":self.settings['CITY'],"provience":self.settings['PROVIENCE']}
			content = self.cities_Col.find_one(condition)
			self.cityhost = content['cityhost']
			self.fillUrl = "http://%s.58.com/ershoufang/"%self.cityhost
			self.city = content["_id"]
			return [scrapy.Request(self.fillUrl)]
	def get_sequence_request(self):
		#按顺序进行爬取
		requests = []
		if self.cities_Col.count({"status":False}) <= 0:
			print("全部设为false")
			self.cities_Col.update({},{"$set":{"status":False}},True,True,True)
		content = self.cities_Col.find_one({"status":False})
		self.cities_Col.update({"_id":content["_id"]},{"$set":{"status":True}})
		self.client.close()
		self.cityhost = content['cityhost']
		self.fillUrl = "http://%s.58.com/ershoufang/"%self.cityhost
		self.city = content["_id"]
		requests.append(scrapy.Request(self.fillUrl))
		return requests
	def start_requests(self):
		if self.settings['CITY'] and self.settings['CITY'] != '':
			return self.get_specify_request()
		else:
			return self.get_sequence_request()
	def parseUrls(self,html):
		links = html.xpath(".//a/@href")
		urls = []
		for link in links:
			if StringUtil.filtString(self.fillUrl+"pn\d+?/",link):
				
				urls.append(link)
		return urls
	def parseItems(self,html,url):
		houselist = html.xpath(".//ul[@class='house-list-wrap']//div[@class='list-info']")
		items = []
		for houseinfo in houselist:
			detailurl = houseinfo.xpath(".//h2[1]/a/@href")
			title = "".join(houseinfo.xpath(".//h2[1]/a/text()"))
			roomNum = "".join(houseinfo.xpath(".//p[1]/span[1]/text()")[0].split())
			size = "".join(houseinfo.xpath(".//p[1]/span[2]/text()"))
			orient =  "".join(houseinfo.xpath(".//p[1]/span[3]/text()"))
			floor = "".join(houseinfo.xpath(".//p[1]/span[4]/text()"))
			address = "".join(("".join(houseinfo.xpath(".//p[2]/span[1]//a/text()"))).split())
			sumprice = "".join(houseinfo.xpath("./following-sibling::div[1]//p[@class='sum']/b/text()"))
			unitprice = "".join(houseinfo.xpath("./following-sibling::div[@class='price']//p[@class='unit']/text()"))
			items.append(HouseItem(
										_id = "".join(detailurl),
										title = title,
										roomNum = roomNum,
										size = NumberUtil.fromString(size),
										orient = orient,
										floor = floor,
										address = address,
										sumPrice = NumberUtil.fromString(sumprice),
										unitPrice = NumberUtil.fromString(unitprice),
										city=self.city,
										fromUrl = url,
										nowTime = time.time(),
										status = "SUBSPENDING")
									)
		return items
	def printItem(self,item):
		print("房屋出售标题是"+item['title'])
		print("房屋数量是:"+item['roomNum'])
		print("房屋大小是:"+item['size'])
		print("房屋朝向是:"+item['orient'])
		print("房屋楼层是:"+item['floor'])
		print("房屋地址是:"+item['address'])
		print("房屋总价是:"+item['sumPrice'])
		print("房屋均价是:"+item['unitPrice'])
	def parse(self,response):
		if(response.body =='None'):
			return
		doc = html.fromstring(response.body.decode("utf-8"))
		urls = self.parseUrls(doc)
		items = self.parseItems(doc,response.url)
		for url in urls:
			yield scrapy.Request(url,callback=self.parse)
		for item in items:
			yield item

