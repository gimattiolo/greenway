import sys
import re
import mechanize
import logging
from bs4 import BeautifulSoup
from time import sleep
import urlparse
from datetime import datetime

import MySQLdb

mechanizeLog = logging.getLogger('mechanize')
mechanizeLog.addHandler(logging.StreamHandler(sys.stdout))
mechanizeLog.setLevel(logging.INFO)

# browser = mechanize.Browser()

initUrl = 'https://egov.uscis.gov/cris/processTimesDisplayInit.do'

rootUrl = 'https://egov.uscis.gov'

class RowInfo :
	def __init__(self):
		self.header = u''
		self.entries = []
		
def makeSoup(response) :
	responseRead = response.read()
	soup = BeautifulSoup(responseRead, "lxml")
	return soup

def isTableColumn(tag) :
	return tag.name == 'td'	

def isTable(tag) :
	return tag.name == 'table'

def hasCaption(tag) :
	# check it is a direct child
	return len([x for x in tag.contents if x.name == 'caption']) > 0 

def isProcessTimeTable(tag):
	return isTable(tag) and hasCaption(tag)

def isProcessTimeTableBody(tag):
	return tag.name == 'tbody' 
	
def isProcessTimeTableRow(tag):
	return tag.name == 'tr'

def cleanUpString(s) :
	s1 = re.sub('[,\t\r\n]+', '', s)
	s1 = s1.lstrip()

	s1 = s1.rstrip()
	
	return s1
	
def processRow(row) :
	info = RowInfo()

	info.header = cleanUpString(row.th.string)

	columns = row.find_all(isTableColumn)
	
	if len(columns) <= 0 :
		print 'No columns!'
		return None
	
	for column in columns :
		# print column
		info.entries.append(cleanUpString(column.string))

	return info
	
def processTables(htmlSoup) :
	
	htmlSoup
	# find table with class='dataTable'
	# print htmlSoup
	tables = htmlSoup.find_all(isProcessTimeTable)

	if len(tables) <= 0 :
		print 'No tables!'
		return False
	
	for table in tables :
		caption = table.caption.get_text()
		print 'Caption: ' + caption	
		bodies = table.find_all(isProcessTimeTableBody)

		if len(bodies) <= 0 :
			print 'No bodies!'
			return False

		for body in bodies :
			rows = body.find_all(isProcessTimeTableRow)

			if len(rows) <= 0 :
				print 'No rows!'
				return False

			for row in rows :
				# print row

				info = processRow(row)
				
				# dateStr = cleanUpString(row.td.find_next_sibling('td').string)
				# datetimeObject = datetime.strptime(dateStr, '%B %d %Y')
				# info.date = datetimeObject

				if info is None :
					return False
				
				print info.header
				print info.entries
	
	return True
		

def processUrl(url) :
	print 'Processing url ' + url
	request = mechanize.Request(url)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	
	return processTables(htmlSoup)

def processForm(form) :

	# print 'Processing form :' 
	# print form.attrs
	
	

	submitInput = form.find(isSubmitInput)

	if submitInput is None :
		return False

	selectForm = form.find('select')

	
	selectionName = ''
	options = []
	if not selectForm is None :
		selectionName = selectForm['name']
		options = selectForm.find_all('option')

	baseUrl = rootUrl 
	baseUrl += form['action'] + '?'
	for option in options :
		url = baseUrl  
		# print option
		url += selectionName + '=' + option['value'] + '&'
		url += submitInput['name'] + '=' + submitInput['value'].replace(' ', '+')	
		if not processUrl(url) :
			return False
		
	return True

def isProcessTimesForm(tag):
	return tag.name == 'form' and tag['name'] == 'processTimesForm'

def isSubmitInput(tag):
	return tag.name == 'input' and tag['type'] == 'submit'
	
def main() :

	# db = MySQLdb.connect("localhost","root","greenway", "greenway")
	 
	# cursor = db.cursor()
	 
	# cursor.execute("SELECT VERSION()")
	 
	# data = cursor.fetchone()
	 
	# print "Database version : %s " % data
	 

	request = mechanize.Request(initUrl)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	forms = htmlSoup.find_all(isProcessTimesForm)
	

	
	
	for form in forms :
		if not processForm(form) :
			return

	# db.close()
		
main()