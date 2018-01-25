import sys
import re
import mechanize
import logging
from bs4 import BeautifulSoup
from time import sleep
import urlparse

import MySQLdb

mechanizeLog = logging.getLogger('mechanize')
mechanizeLog.addHandler(logging.StreamHandler(sys.stdout))
mechanizeLog.setLevel(logging.INFO)

# browser = mechanize.Browser()

initUrl = 'https://egov.uscis.gov/cris/processTimesDisplayInit.do'

rootUrl = 'https://egov.uscis.gov'

class RowInfo :
	application = u''
	description = u''
	date = u''
	

def makeSoup(response) :
	responseRead = response.read()
	soup = BeautifulSoup(responseRead, "lxml")
	return soup

	
def isProcessTimeTable(tag):
	return tag.name == 'table' and 'class' in tag.attrs and tag['class'] == ['dataTable']

def isProcessTimeTableBody(tag):
	return tag.name == 'tbody' 
	
def isProcessTimeTableRow(tag):
	return tag.name == 'tr'

def removeSpecialChar(s) :
	re.sub('[\t\r\n]+', '', s)
	
def processRow(row):

	info = RowInfo()
	info.application = row.th.string
	# removeSpecialChar(info.application)
	info.description = row.td.string
	# removeSpecialChar(info.description)
	info.date = row.td.find_next_sibling('td').string
	# removeSpecialChar(info.date)

	temp = [str(info.application)]
	print temp[0]
	print removeSpecialChar(temp[0])
	return info

	
def processTables(htmlSoup) :
	
	# find table with class='dataTable'
	tables = htmlSoup.find_all(isProcessTimeTable)
	for table in tables :
		caption = table.caption.get_text()
		print caption	
		bodies = table.find_all(isProcessTimeTableBody)
		for body in bodies :
			rows = body.find_all(isProcessTimeTableRow)
			for row in rows :
				info = processRow(row)
		

def processUrl(url) :
	print 'Processing url ' + url
	request = mechanize.Request(url)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	
	processTables(htmlSoup)

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
		processUrl(url)
		return True
		
	return True

def isProcessTimesForm(tag):
	return tag.name == 'form' and tag['name'] == 'processTimesForm'

def isSubmitInput(tag):
	return tag.name == 'input' and tag['type'] == 'submit'
	
def main() :

	# Connessione al Database
	# db = MySQLdb.connect("localhost","root","greenway", "greenway")
	 
	# Ottenimento del cursore
	# cursor = db.cursor()
	 
	# Esecuzione di una query SQL
	# cursor.execute("SELECT VERSION()")
	 
	# Lettura di una singola riga dei risultati della query
	# data = cursor.fetchone()
	 
	# print "Database version : %s " % data
	 

	request = mechanize.Request(initUrl)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	forms = htmlSoup.find_all(isProcessTimesForm)
	
	
	
	
	for form in forms :
		ans = processForm(form)
		if ans : 	
			break
	# Disconnessione
	# db.close()
		
main()