import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

import sqlite3

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    #現在の現金残高
    cash_dict = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    now_cash = cash_dict[0]["cash"]
    stocks = db.execute(
        "SELECT Symbol, SUM(Shares) as Shares, Total, Name FROM buy WHERE User_ID = ? GROUP BY Symbol HAVING (SUM(shares)) > 0;",
        session["user_id"],
    )
    print(stocks)
    #全保有株式の現在の合計金額
    total_stocks_cash = 0
    #現金残高を含めた全財産
    total_cash = 0
    for stock in stocks:
        print(stock)
        # print(stock["Shares"])
        # print("ここまできた")
        # 保有銘柄
        name = stock["Name"]
        #保有している各銘柄のsymbol
        symbol = stock["Symbol"]
        # print(symbol)
        #各株式数
        shares = stock["Shares"]
        #各株式の現在価格
        quote = lookup(symbol)
        now_price = quote.get("price")
        # print(now_price)
        #各株式の合計
        each_total = shares * now_price
        tatal_stocks_cash = each_total + total_stocks_cash
    total_cash = total_stocks_cash + now_cash
    # print("ここまできた")
    return render_template("index.html", stocks = stocks, total_cash = total_cash, now_cash = now_cash)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    #POST経由で判定
    # symbol = "abc"
    # quote = lookup(symbol)
    # symbol_symbol = quote.get("symbol")
    # price = quote.get("price")
    # print("buyの実験")
    # print(symbol_symbol)
    # print (quote)
    # print(symbol)
    # print(price)
    user_id = session["user_id"]
    if request.method == "POST":
        #print("1ここまできた")
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quote = lookup(symbol)
        symbol_symbol = quote.get("symbol")
        name = quote.get("name")
        price = quote['price']
        cash_dict = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
        cash = cash_dict[0]["cash"]
        #symbolが空白の時
        if symbol == "":
            return apology("Stock symbol not valid, please try again")
        #symbolが存在しない場合
        if quote == None:
            return apology("Stock symbol not valid, please try again")
        #sharesが整数のとき
        shares = int(shares)
        if shares < 1:
            return apology("shares must be over zero")

        #ユーザが現在の価格で株式数を購入できない場合
        # print(symbol_symbol)
        # print(name)
        # print(quote)
        # print(cash)
        # print(price*2)
        # print(shares)
        # print(type(shares))
        # float(cash)
        if cash < price * shares:
            return apology("you have not enough money")
        else:
            #購入できた
            shares_price = price * shares
            db.execute(
                "UPDATE users SET cash = cash - ? WHERE id = ?",
                shares_price,
                session["user_id"],
            )
            db.execute(
                "INSERT INTO buy (User_ID, Symbol, Name, Shares, Price, Total) VALUES (?, ?, ?, ?, ?, ?)",
                session["user_id"],
                symbol_symbol,
                name,
                shares,
                price,
                shares_price,
            )
            flash("Purchased correctly")
            return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    histories = db.execute(
        "SELECT Symbol, Price, Shares, timestamp FROM buy WHERE User_ID = ?;",
        session["user_id"],
    )
    for history in histories:
        print(history)
        symbol = history["Symbol"]
        price = history["Price"]
        shares = history["Shares"]
        timestamp = history["timestamp"]

    return render_template("history.html", histories = histories)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # print("ここまできた")
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if not symbol:
            return apology("please enter a symbol")
        elif quote == None:
            return apology("Symbol does not exist")
        else:
            brand = quote.get("name")
            price = quote.get("price")
            return render_template("quoted.html", symbol = brand, price = price)
    if request.method == "GET":
        return render_template("quote.html")




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return apology("Missing username")
        elif not request.form.get("password") :
            return apology("Missing password")
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords don't match")
        hash = generate_password_hash(request.form.get("password"))
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",username, hash)
            return redirect("/")
        except :
            return apology("You cannot use this username")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # 売りたいsymbol取得
        symbol = request.form.get("symbol")
        # sharesをint型で取得
        shares = request.form.get("shares")
        shares = int(shares)
        # 入力されているか
        if symbol == "":
            return apology("Stock symbol not valid, please try again")
        # 正の整数かどうか
        if shares < 1:
            return apology("shares must be over zero")
        # 持ってる株を調べる
        stocks = db.execute(
            "SELECT SUM(shares) as shares FROM buy WHERE User_ID = ? AND Symbol = ?;",
            session["user_id"],
            symbol,
        )[0]
        # 指定した株数が持っている株数より大きかったら
        if shares > stocks["shares"]:
            return apology("You don't have this number of shares")
        price = lookup(symbol)["price"]
        name = lookup(symbol)["name"]
        shares_value = price * shares
        # 売ったら株式数は減る
        sold_shares = -1 * shares
        try:
            # 売った履歴
            db.execute(
                "INSERT INTO buy (User_ID, Symbol, Name, Shares, Price, Total) VALUES (?, ?, ?, ?, ?, ?)",
                session["user_id"],
                symbol,
                name,
                sold_shares,
                price,
                shares_value
            )
            # 売った分だけ残金増える
            db.execute(
                "UPDATE users SET cash = cash + ? WHERE id = ?",
                shares_value,
                session["user_id"],
            )
        except:
            return apology("It wasn't handled correctly")
        flash("Sold!")
        return redirect("/")
    else:
        stocks = db.execute(
            "SELECT symbol FROM buy WHERE User_ID = ? GROUP BY Symbol",
            session["user_id"],
        )
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
