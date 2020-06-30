from flask import Flask, render_template, request, g, redirect
import sqlite3
from sqlite3 import Error
import requests
import datetime
app = Flask(__name__)

"""Replace None with your API Token, in string format"""
token = None

"""
Sign Up at IEX API to get a personal API token (free): 
https://iexcloud.io/?gclid=Cj0KCQjw3Nv3BRC8ARIsAPh8hgI9Un2KrPqeWxv3Xop2f-7BusG7zoWeaAy46n4M2cQ0ap-yvTWCukcaAg5OEALw_wcB
"""


def lookup(stockSymbol):
	"""
	input is a stock symbol, output is a dict of that symbol's current stats OR invalid symbol
	"""
	try:
		response = requests.get(f"https://cloud.iexapis.com/stable/stock/{stockSymbol}/quote?token={token}")
		quote = response.json()
		return {'name' : quote['companyName'],
			'symbol' : quote['symbol'],
			'price' : float(quote['latestPrice']),
			}
	except:
		return 'Invalid Symbol'


def validateSymbol(symbol):
	return (lookup(symbol) != "Invalid Symbol")


def create_connection(db_file):
	conn=None
	try:
		conn = sqlite3.connect(db_file)
		print(sqlite3.version)
	except Error as e:
		print(e)
	return conn


def selectDB(sqlStatement):
	"""
	sends a SQL request to the DB, and returns the resulting view as a list of lists
	"""
	conn=create_connection(r"stocks.db")
	cur=conn.cursor()
	cur.execute(sqlStatement)
	rows=cur.fetchall()
	# turn into list of list
	rl=[]
	for row in rows:
		rr=[]
		for item in row:
			rr.append(item)
		rl.append(rr)
	conn.commit()
	conn.close()
	return rl

def insertStock(symbol, name, shares, value):
	conn = create_connection(r"stocks.db")
	c=conn.cursor()
	c.execute("INSERT INTO history (symbol, name, shares, value) VALUES (?, ?, ?, ?)", (symbol, name, str(shares), str(value)))
	conn.commit()
	conn.close()

def insertCash(value):
	conn = create_connection(r"stocks.db")
	c=conn.cursor()
	c.execute("INSERT INTO history (symbol, value) VALUES (?, ?)", ("CASH", str(value)))
	conn.commit()
	conn.close()


@app.template_filter()
def currencyFormat(value):
	try:
		value = float(value)
	except:
		return 0
	return "${:,.2f}".format(value)

@app.template_filter()
def percentFormat(value):
    value = float(value)
    return "{:.2%}".format(value)


def getCash():
	cash = selectDB('SELECT SUM(value) from history WHERE symbol = "CASH"')[0][0] #first item in first row
	if cash == None:
		return 0
	return cash

def getHoldingsValue():
	holdings = selectDB('SELECT symbol, SUM(shares) from history WHERE symbol !="CASH" GROUP BY symbol')
	holdingsValue = 0
	for row in holdings:
		holdingsValue += row[1] * lookup(row[0])['price'] #find current price * shares
	return holdingsValue

def getTotalGains():
	transactionTotal = selectDB('SELECT SUM(value) from history WHERE symbol != "CASH"')[0][0]
	holdingsValue = getHoldingsValue()
	try:
		gains =  (holdingsValue - transactionTotal)/transactionTotal
	except:
		gains = 0
	return gains

def getBuyValue(symbol):
	buyValue = selectDB("SELECT SUM(value) from history WHERE symbol =  '"+ symbol.upper() + "'")[0][0]
	return buyValue

def getSummaryTable():
	"""Returns a list of a summary table (which is a list of lists), by calling select on db and appending with current price, value, and gains"""
	table = selectDB('SELECT symbol, name, SUM(shares) from history WHERE symbol != "CASH" GROUP BY symbol HAVING SUM(shares) != 0 ORDER BY timestamp desc')
	for row in table:
		values = lookup(row[0])
		row.append(values['price'])
		row.append(row[3]*row[2])
		buyValue = getBuyValue(row[0])
		gains = (row[4] - buyValue) / buyValue
		row.append(gains)
	return table


@app.route('/')
def home():
	return render_template('home.html', table = getSummaryTable(), cash = getCash(), holdingsValue = getHoldingsValue(), gains = getTotalGains())


@app.route('/quote', methods = ['GET', 'POST'])
def quote():
	if request.method == 'GET':
		return render_template('quote.html', title = "Quote", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())
	else:
		symbol = request.form.get('symbol')
		if not validateSymbol(symbol):
			return render_template('quote.html', title = "Quote", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue(), error = "Invalid Stock Symbol")
		else:
			price = lookup(symbol)['price']
			return render_template('quoted.html', title = "Quote", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue(), symbol = symbol, price = price)

@app.route('/buy', methods = ['GET', 'POST'])
def buy():
	if request.method == 'GET':
			return render_template('buy.html', title = "Buy", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())
	else:
		symbol = request.form.get('symbol').upper()
		if validateSymbol(symbol) == False:
			return render_template('buy.html', title = "Buy", error = "Invalid Stock Symbol", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())
		else:
			shares = int(request.form.get('shares'))
			price = lookup(symbol)['price']
			name = lookup(symbol)['name']
			if price*shares > getCash():
				return render_template('buy.html', title = "Buy", error = "Not enough cash", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())
			else:
				insertStock(symbol, name, shares, shares*price)
				insertCash(-shares*price)
				return redirect('/')


@app.route('/sell', methods = ['GET', 'POST'])
def sell():
	table = getSummaryTable()
	if request.method == 'GET':
		return render_template('sell.html', title = "Sell", table = table, gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())
	elif request.method == 'POST':
		for row in table:
			sharesToSell = int(request.form.get(row[0]))
			if sharesToSell > 0:
				value = sharesToSell*lookup(row[0])["price"]
				insertCash(value)
				insertStock(row[0], row[1], -sharesToSell, -value)
		return redirect("/")


@app.route('/history')
def history():
	table = selectDB('SELECT timestamp, symbol, name, shares, value FROM history ORDER BY timestamp DESC')
	return render_template('history.html', title = "History", table = table, gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())

@app.route('/cash', methods = ['GET', 'POST'])
def cash():
	if request.method == 'GET':
		return render_template('cash.html', title = "Cash", gains = getTotalGains(), cash = getCash(), holdingsValue = getHoldingsValue())
	else:
		transferAmount = float(request.form.get("transferAmount"))
		transferDirection = request.form.get("transferDirection")
		if transferAmount == 0:
			return redirect('/')
		else:
			if transferDirection == "fromBank":
				insertCash(transferAmount)
			else:
				insertCash(-transferAmount)
			return redirect('/')



if token != None:
	# app.run(debug=True)
	if __name__ == '__main__':
		app.run()
else:
	print("Please Sign Up and Request API Token from IEX API")