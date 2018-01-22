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

def processUrl(url) :
	print 'Processing url ' + url
	# request = mechanize.Request(url)
	# response = mechanize.urlopen(request)

def processForm(form) :

	print 'Processing form :' 
	print form.attrs
	
	

	submitInput = form.find(isSubmitInput)

	if submitInput is None :
		return

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

def isProcessTimesForm(tag):
	return tag.name == 'form' and tag['name'] == 'processTimesForm'

def isSubmitInput(tag):
	return tag.name == 'input' and tag['type'] == 'submit'
	
def main() :

	# Connessione al Database
	db = MySQLdb.connect("localhost","root","greenway", "greenway")
	 
	# Ottenimento del cursore
	cursor = db.cursor()
	 
	# Esecuzione di una query SQL
	cursor.execute("SELECT VERSION()")
	 
	# Lettura di una singola riga dei risultati della query
	data = cursor.fetchone()
	 
	print "Database version : %s " % data
	 

	request = mechanize.Request(initUrl)
	response = mechanize.urlopen(request)
	responseRead = response.read()
	soup = BeautifulSoup(responseRead, "lxml")
	htmlCode = str(soup)
	forms = soup.find_all(isProcessTimesForm)
	
	
	
	
	for form in forms :
		processForm(form)	

	# Disconnessione
	db.close()
		
main()