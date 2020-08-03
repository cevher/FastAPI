from pydantic import BaseModel
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
import models
from sqlalchemy.orm import Session
from database import  SessionLocal, engine
from models import Stock
import yfinance as yf

app = FastAPI()

templates = Jinja2Templates(directory="templates")
models.Base.metadata.create_all(bind=engine)

class StockRequest(BaseModel):
    symbol:str

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

@app.get("/")
def home(request: Request, forward_pw=None, dividend_yield=None, ma50=None, ma200=None, db:Session =Depends(get_db)):

    stocks = db.query(Stock)

    if forward_pw:
        stocks = stocks.filter(Stock.forward_pw<forward_pw)
    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield>dividend_yield)
    if ma50:
        stocks = stocks.filter(Stock.price>ma50)
    if ma200:
        stocks = stocks.filter(Stock.price>ma200)
    return templates.TemplateResponse("home.html", {
        "request": request, 
        "stocks": stocks,
        "dividend_yield": dividend_yield,
        "forward_pw": forward_pw,
        "ma50": ma50,
        "ma200": ma200,
        
    })


def fetch_stock_data(id:int):
    db = SessionLocal() #create a db session
    stock = db.query(Stock).filter(Stock.id==id).first()
    
    yahoo_data = yf.Ticker(stock.symbol)

    stock.ma200 = yahoo_data.info['twoHundredDayAverage']
    stock.ma50 = yahoo_data.info['fiftyDayAverage']
    stock.price = yahoo_data.info['previousClose']
    stock.forward_pw = yahoo_data.info['forwardPE']
    stock.forward_eps = yahoo_data.info['forwardEps']
    
    if yahoo_data.info['dividendYield'] is not None:
        stock.dividend_yield = yahoo_data.info['dividendYield'] * 100
    
    db.add(stock)
    db.commit()

@app.post("/stock")
async def create_stock(stock_request: StockRequest,background_task:BackgroundTasks,db: Session=Depends(get_db)):
    
    stock=Stock()
    stock.symbol=stock_request.symbol
    db.add(stock)
    db.commit()  ###Stock ID created once the sotkc is entered into the dataabase

    background_task.add_task(fetch_stock_data, stock.id)

    return {
        "code": "success",
        "message": "Stock created"
    }