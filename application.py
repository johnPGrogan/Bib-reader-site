import os

# from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
#from flask.ext.session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import random

from helpers import *



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
#app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
#app.config["SESSION_FILE_DIR"] = mkdtemp()
#app.config["SESSION_PERMANENT"] = False
#app.config["SESSION_TYPE"] = "filesystem"
#Session(app)

# Configure CS50 Library to use SQLite database
#db = SQL("sqlite:///finance.db")

# Make sure API key is set
#if not os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")


@app.route("/", methods=["GET","POST"])
def index():
    """Take bibliography + options"""
    if request.method == "POST":

        # error checking
        if not request.form.get("bib"):
            flash("No text entered, please enter a BibTex bibliography")
            return redirect("/")

        bib_text = request.form.get("bib")
        use_initials = request.form.get("initials")

        min_freq = request.form.get("minFreq") # get minimum frequencies to displau
        if not min_freq:
            min_freq = "1";
        min_freq = float(min_freq)


        bib_style = request.form.get("bibStyle") # get style

        # check format of text
        err = check_bib_format(bibtex_str=bib_text, bib_style=bib_style)
        if err:
            flash(err)
            return redirect("/")

        # parse + count
        authors, journals = bib_analyser(bibtex_str=bib_text, bib_style=bib_style, use_initials=use_initials)



        # format a table
        return render_template("home.html", authors=authors, journals=journals, minFreq=min_freq, useInitials=use_initials)


    else:
        return render_template("home.html")




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
