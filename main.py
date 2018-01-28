import sys
import re
import mechanize
import logging
from bs4 import BeautifulSoup
from time import sleep
import urlparse
import datetime
import traceback


import MySQLdb

dbHost = "localhost"
dbUser = "root"
dbPassaword = "10sp3r14m0ch3m3l4c4v0!"
dbName = "MySQL"

db = MySQLdb.connect(dbHost, dbUser, dbPassaword, dbName)

mechanizeLog = logging.getLogger('mechanize')
mechanizeLog.addHandler(logging.StreamHandler(sys.stdout))
mechanizeLog.setLevel(logging.INFO)

# browser = mechanize.Browser()

initUrl = 'https://egov.uscis.gov/cris/processTimesDisplayInit.do'

rootUrl = 'https://egov.uscis.gov'

updateTimeEntries = False

x = 0

# how=1 means, return it as a dictionary, where the keys are the column names, or table.column if there are two columns with the same name (say, from a join). how=2 means the same as how=1 except that the keys are always table.column; this is for compatibility with the old Mysqldb module.
fetchRowHow = 0

class RowInfo :
	MaxEntries = 3
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

def isLastUpdated(tag) :	
	return tag.name == 'p' and 'id' in tag.attrs and tag.attrs['id'] == 'posted' 
	
def cleanUpString(s) :
	s = re.sub('[,\t\r\n]+', '', s)
	s = s.lstrip()
	s = s.rstrip()
	
	return s

def cleanUpLastUpdated(s) :
	s = cleanUpString(s)
	index = s.find(':')
	s = s[index + 1 : ]
	s = s.lstrip()
	s = s.rstrip()
	return s
	
	
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
	
	if len(info.entries) < RowInfo.MaxEntries :
		info.entries.insert(len(info.entries) - 1, 'N/A')
	
	return info
	
def processTables(htmlSoup, locationId) :

	global updateTimeEntries

	getCategoryIdQuery = """SELECT CategoryId FROM Categories WHERE Form = \'{0}\' AND Description1 = \'{1}\' AND Description2 = \'{2}\' LIMIT 1;"""

	insertCategoryEntryQuery = """INSERT INTO Categories (Form, Description1, Description2) VALUES (\'{0}\', \'{1}\', \'{2}\');"""

	getTimeEntryQuery = """SELECT EntryId FROM TimeEntries WHERE CategoryId = {0} AND LocationId = {1} AND ProcessingDate = \'{2}\' AND LastUpdateDate = \'{3}\' AND PageLastUpdateDate = \'{4}\' LIMIT 1;"""

	
	insertTimeEntryQuery = """INSERT INTO TimeEntries (CategoryId, LocationId, ProcessingDate, LastUpdateDate, PageLastUpdateDate) VALUES ({0}, {1}, \'{2}\', \'{3}\', \'{4}\');"""

	
	postedTags = htmlSoup.find_all(isLastUpdated)
	if postedTags is None or not len(postedTags) == 1 :
		return False
	
	pageLastUpdatedStr = cleanUpLastUpdated(postedTags[0].get_text())
	
	# find table with class='dataTable'
	# print htmlSoup
	tables = htmlSoup.find_all(isProcessTimeTable)

	if len(tables) <= 0 :
		print 'No tables!'
		return False
	
	for table in tables :
		caption = table.caption.get_text()
		lastUpdatedStr = cleanUpLastUpdated(caption)

		# print 'Caption: ' + caption	


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
				
				# datetimeObject = datetime.strptime(dateStr, '%B %d %Y')
				# info.date = datetimeObject

				if info is None :
					return False
				
				
				
				firstIndex = 0
				lastIndex = len(info.entries) - 1
				
				# print 'DB ID : ' + locationId + ' / ' + info.header + ' / ' + str(info.entries[firstIndex : lastIndex])
				# print 'DB date : ' + info.entries[lastIndex]
				# print 'DB last update date : ' + lastUpdatedStr
				# print 'DB page last update date : ' + pageLastUpdatedStr


				try :	
					# get categoryId
					q = getCategoryIdQuery.format(info.header, info.entries[0], info.entries[1])
					db.query(q)
					f = db.store_result()
					r = f.fetch_row(1, fetchRowHow)

					categoryId = None
					if len(r) > 0 :
						categoryId = r[0][0]
					
					if categoryId is None :

						q = insertCategoryEntryQuery.format(info.header, info.entries[0], info.entries[1])
						db.query(q)

						q = getCategoryIdQuery.format(info.header, info.entries[0], info.entries[1])
						db.query(q)
						f = db.store_result()
						r = f.fetch_row(1, fetchRowHow)

						if len(r) <= 0 :
							print 'Warning : Unable to find category for query ' + q
							continue
							
						categoryId = r[0][0]
				
					if updateTimeEntries :
					
						q = getTimeEntryQuery.format(categoryId, locationId, datetime.datetime.strptime(info.entries[2], '%B %d %Y').strftime('%Y-%m-%d'), datetime.datetime.strptime(lastUpdatedStr, '%B %d %Y').strftime('%Y-%m-%d'), datetime.datetime.strptime(pageLastUpdatedStr, '%B %d %Y').strftime('%Y-%m-%d'))
						db.query(q)
						f = db.store_result()
						r = f.fetch_row(1, fetchRowHow)

						if len(r) > 0 :
							print 'Warning : Found existing entry for query ' + q
							continue
					
						q = insertTimeEntryQuery.format(categoryId, locationId, datetime.datetime.strptime(info.entries[2], '%B %d %Y').strftime('%Y-%m-%d'), datetime.datetime.strptime(lastUpdatedStr, '%B %d %Y').strftime('%Y-%m-%d'), datetime.datetime.strptime(pageLastUpdatedStr, '%B %d %Y').strftime('%Y-%m-%d'))
						db.query(q)
	
				except MySQLdb.MySQLError:
					print("Unexpected error:", sys.exc_info())
					continue
					
	return True
		

def processUrl(url, locationId) :
	print 'Processing url ' + url
	request = mechanize.Request(url)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	
	return processTables(htmlSoup, locationId)

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
		locationId = option['value']
		url += selectionName + '=' + locationId + '&'
		url += submitInput['name'] + '=' + submitInput['value'].replace(' ', '+')	
		if not processUrl(url, locationId) :
			return False
		
	return True

def isProcessTimesForm(tag):
	return tag.name == 'form' and tag['name'] == 'processTimesForm'

def isSubmitInput(tag):
	return tag.name == 'input' and tag['type'] == 'submit'
	
def createTables() :
	
	# SQL DATE - format YYYY-MM-DD
	# SQL DATETIME - format: YYYY-MM-DD HH:MI:SS
	
	# createLocationsTableQuery = """CREATE TABLE Locations (LocationId int NOT NULL PRIMARY KEY, LocationName varchar(255));"""
	# try :
		# db.query(createLocationsTableQuery)
	# except MySQLdb.MySQLError:
		# print("Unexpected error:", sys.exc_info())
		# raise
		
	createCategoriesTableQuery = """CREATE TABLE Categories (CategoryId int NOT NULL AUTO_INCREMENT, Form varchar(255), Description1 varchar(255), Description2 varchar(255), PRIMARY KEY (CategoryId));"""
	print createCategoriesTableQuery
	try :
		db.query(createCategoriesTableQuery)
	except MySQLdb.MySQLError:
		print("Unexpected error:", sys.exc_info())
		raise
	
		
		
	createTimeEntriesTableQuery = """CREATE TABLE TimeEntries (EntryId int NOT NULL AUTO_INCREMENT, CategoryId int NOT NULL, LocationId int NOT NULL, ProcessingDate DATE NOT NULL, LastUpdateDate DATE NOT NULL, PageLastUpdateDate DATE NOT NULL, PRIMARY KEY (EntryId));"""
	print createTimeEntriesTableQuery
	try :
		db.query(createTimeEntriesTableQuery)
	except MySQLdb.MySQLError:
		print("Unexpected error:", sys.exc_info())
		raise

	
		

def fillLocationsTable(forms) :
		
	insertLocationQuery = """INSERT INTO Locations VALUES ({0}, \'{1}\');"""	
	

	for form in forms :
		submitInput = form.find(isSubmitInput)

		if submitInput is None :
			return False

		selectForm = form.find('select')
		
		selectionName = ''
		options = []
		if not selectForm is None :
			selectionName = selectForm['name']
			options = selectForm.find_all('option')
			
		for option in options :
			locationId = option['value'];
			locationName = option.get_text()
			
			# print locationId
			# print locationName
			
			try :
				print insertLocationQuery.format(locationId, locationName)
				db.query(insertLocationQuery.format(locationId, locationName))
			except MySQLdb.MySQLError:
				print("Unexpected error:", sys.exc_info())
				continue

def initDB(creation) :

	global updateTimeEntries

	request = mechanize.Request(initUrl)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	forms = htmlSoup.find_all(isProcessTimesForm)

	if creation :
		createTables()
	else :
		fillLocationsTable(forms)
		updateTimeEntries = False
		processForms()

def processForms() :

	request = mechanize.Request(initUrl)
	response = mechanize.urlopen(request)
	htmlSoup = makeSoup(response)
	forms = htmlSoup.find_all(isProcessTimesForm)
	
	for form in forms :
		if not processForm(form) :
			return
			
def main() :
	global updateTimeEntries

	cursor = db.cursor()
	cursor.execute("SELECT VERSION()")
	data = cursor.fetchone()
	print "Database version : %s " % data

	# creation = True
	# initDB(creation)
	
	updateTimeEntries = True
	processForms()
	
	db.commit()
	db.close()
		
main()