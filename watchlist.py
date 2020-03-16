import requests
import yfinance
import re
from sys import argv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint
from send_email import send_email
from collections import namedtuple
import logbook
from datetime import datetime, timedelta

Company = namedtuple('Company', 'ticker price buyprice')
app_log = logbook.Logger('App')

def init_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('WATCHLIST').sheet1
    return sheet

def get_tickers(sheet):
    tickers = sheet.col_values(1)[2:]
    return tickers

def get_buyprices(sheet):
    buyprices = sheet.col_values(2)[2:]
    return buyprices

def get_prices(list_tickers):
    prices = []
    if len(list_tickers) > 1:
        data = yfinance.download(tickers=list_tickers, period='1d')
        for name in list_tickers:
            ticker_price = data['Adj Close'][name][0]
            prices.append(round(ticker_price, 2))
    else:
        ticker_data = yfinance.Ticker(list_tickers[0])
        price = ticker_data.history(period='1d')['Close'][0]
        prices.append(price)
    return prices

def construct_companies(tickers, prices, buyprices):
    companies = []
    companies_length = len(tickers)
    for _ in range(companies_length):
        companies.append(Company(tickers[_], prices[_], float(buyprices[_])))
    return companies


# prices_and_buyprices
def email_buyprice(companies):
    week = timedelta(days=7)
    for company in companies:
        # Vamos a suponer que hacemos todos los cálculos y mandamos un correo.
        last_company = None
        with open('watchlist.log', 'r') as f:
            for line in f.readlines():
                if company.ticker in line:
                    last_company = line
        if last_company:
            pat = re.compile('\d+-\d+-\d+')
            date_str = pat.findall(last_company)
            date = datetime.strptime(date_str[0], '%Y-%m-%d').date()
            # print(date)
        if not last_company or date <= datetime.date(datetime.today()) - week:
            if company.price <= company.buyprice:
                body = f'Hola Quique,\nLa compañía {company.ticker} está por debajo de su precio de compra, de forma que deberías echarle un ojo.\nUn saludo,\n Quique.'
                subject = f'Company {company.ticker} is on sale!'
                app_log.trace(f'Email was sent on company "{company.ticker}"')
                send_email(body, subject)   

def main():
    sheet = init_spreadsheet()
    tickers = get_tickers(sheet)
    prices = get_prices(tickers)
    buyprices = get_buyprices(sheet)
    companies = construct_companies(tickers, prices, buyprices)
    email_buyprice(companies)
