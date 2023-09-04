import os
import urllib.parse
from flask import redirect, render_template, request, session
from functools import wraps
from colorama import Fore, Style
from termcolor import colored
import requests
import re


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def is_email(mail):
    patron = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
     
    if re.match(patron, mail):
        return True
    else:
        return False

def check_caracter(username):
    if len(username) > 20:
        return False
    else:
        not_symbol = [',', '/', '!', '+', '-', "'", '@', ']', '&', ':', '\\']
        for char in not_symbol:
            if char in username:
                return False
    return True

def get_books_info(isbn):
    url = "https://www.googleapis.com/books/v1/volumes?q=isbn:" + isbn.strip()
    responsive = requests.get(url).json()
    if "totalItems" not in responsive:
        print(Fore.RED + "not info found" + Style.RESET_ALL)
        return None
    if responsive["totalItems"] == 0:
        print(Fore.RED + "not info found" + Style.RESET_ALL)
        return None
    print(Fore.GREEN + "Book info found" + Style.RESET_ALL)
    return responsive
