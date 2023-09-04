import os
from flask_paginate import Pagination, get_page_parameter
from flask import Flask, session, redirect, render_template, request, url_for, g
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_mail import Mail, Message
from colorama import Fore, Style
from termcolor import colored

from dotenv import load_dotenv

load_dotenv()

from helpers import apology, login_required, is_email, check_caracter, get_books_info
from flask import jsonify


app = Flask(__name__)

app.config['SECRET_KEY'] = 'qwertyuiopasdfghjklzxcvbnm'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv("GMAIL")
app.config['MAIL_PASSWORD'] = os.getenv("PASS_WORD")
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.before_request
def before_request():
    g.books_pagination = []

@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", message="Page not found"), 404

@app.route("/home")
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])    
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirm_password")
        email = request.form.get("mail")
        
        if not username or not check_caracter(username):
            return render_template("error.html", message="Invalid username \n The username cannot be longer than 20 characters, and cannot contain any symbols. ")
        if not password or not confirmation:
            return render_template("error.html", message="Password is required")
        if password != confirmation:
            return render_template("error.html", message="Passwords do not match")
        if not email:
            return render_template("error.html", message="Email is required")
        if not is_email(email):
            return render_template("error.html", message="Invalid email")
        if len(password) < 8:
            return render_template("error.html", message="Password must be at least 8 characters long")
        
        user_exist = text("SELECT * FROM users WHERE username = :username")
        if db.execute( user_exist, {"username": username}).rowcount != 0: 
            return render_template("error.html", message="Username already exists")
        
        query = text("INSERT INTO users (username, password, email) VALUES (:username, :password, :email)") 
        db.execute(query, {"username": username, "password": generate_password_hash(password), "email": email})
        db.commit()
        
        msg = Message("Welcome to Disa Books", sender="dknauth@code-fu.net.ni", recipients=[email])
        message = f'Welcome to Disa Books {username}! \n Estamos encantados de darte la bienvenida a nuestra comunidad literaria. En Disa Books, encontrarás un mundo lleno de historias fascinantes, aventuras emocionantes y conocimiento esperando ser descubierto. \nExplora nuestra amplia selección de libros de diferentes géneros y autores. Ya sea que te apasione la ficción, la no ficción, la fantasía, el romance o la ciencia ficción, estamos seguros de que encontrarás algo que te atrape y te transporte a mundos nuevos y emocionantes. \n¡Prepárate para sumergirte en un viaje literario único en Disa Books! Esperamos que esta experiencia enriquezca tu pasión por la lectura y te proporcione momentos inolvidables entre las páginas de los libros. \n¡Disfruta explorando y leyendo en Disa Books! \n\nAtentamente,\nEl equipo de Disa Books'
        msg.body = message
        
        try:
            mail.send(msg)
            print(Fore.GREEN + "Email sent" + Style.RESET_ALL)
        except Exception as e:
            print(e)
            return render_template("error.html", message="Error sending welcome email")
            
        if request.form.get("autologin") is not None:
            query = text("SELECT * FROM users WHERE username = :username")
            user = db.execute(query, {"username": username}).fetchone()
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect("/")
        else:
            return render_template("login.html")
                
    else:
        return render_template("register.html")
    
@app.route("/login", methods=["GET", "POST"])  
def login(): 
      
    #Forget any user_id
    session.clear()
     
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        query = text("SELECT * FROM users WHERE username = :username or email = :username")
        
        if not username:
            return render_template("error.html", message="Username is required")
        if not password:
            return render_template("error.html", message="Password is required")
        
        if db.execute(query, {"username": username}).rowcount == 0:
            return render_template("error.html", message="Username does not exist")
        
        user = db.execute(query, {"username": username}).fetchone()
        
        if  not check_password_hash(user.password, password):
            return render_template("error.html", message="Incorrect password")
        
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect("/")
    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 11  # Número de elementos por página
    
    if request.method == "POST":
        search = str(request.form.get("search"))
        if not search:
            return render_template("error.html", message="Search is required")
        
        if len(search) == 4 and search.isnumeric():
            query = text("SELECT * FROM books WHERE isbn LIKE :search OR year = :year")
            books = db.execute(query, {"search": f"%{search}%", "year": int(search)}).fetchall()
        else:
            query = text("SELECT * FROM books WHERE LOWER(isbn) LIKE LOWER(:search) OR LOWER(title) LIKE LOWER(:search) OR LOWER(author) LIKE LOWER(:search) ")
            books = db.execute(query, {"search": f"%{search}%"}).fetchall()
              
        if len(books) == 0:
            print(Fore.RED + "Books not found" + Style.RESET_ALL)
            return render_template("error.html", message="No results found")
        
        session["search"] = books
        total_books = len(books)
        print(Fore.RED + f"{ len(books)}" + Style.RESET_ALL)
        pagination = Pagination(page=page, per_page=per_page, total=total_books, css_framework="bootstrap")

        # Divide los resultados en páginas
        start = (page - 1) * per_page
        end = start + per_page
        books_to_display = books[start:end]
        
        imageBooks = {}
        for i in range(0,len(books_to_display)):
            responsive = get_books_info(books_to_display[i].isbn)
            print(responsive)
            try:
                imageBooks[books_to_display[i].title] = responsive["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]
            except Exception as e:
                print(e)
                imageBooks[books_to_display[i].title] = "../static/img/books.jpg"
                 
        return render_template("index.html", books=books_to_display, imageBooks=imageBooks, pagination=pagination)
    else:
        total_books = len(session["search"])
        print(Fore.GREEN + f"{total_books}" + Style.RESET_ALL)
        pagination = Pagination(page=page, per_page=per_page, total=total_books, css_framework="bootstrap")

        # Divide los resultados en páginas
        start = (page - 1) * per_page
        end = start + per_page
        books_to_display = session["search"][start:end]
        print(Fore.GREEN + f"{books_to_display}" + Style.RESET_ALL)
        imageBooks = {}
        for i in range(0,len(books_to_display)):
            responsive = get_books_info(books_to_display[i].isbn)
            print(responsive)
            try:
                imageBooks[books_to_display[i].title] = responsive["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]
            except Exception as e:
                print(e)
                imageBooks[books_to_display[i].title] = "../static/img/books.jpg"
                 
        return render_template("index.html", books=books_to_display, imageBooks=imageBooks, pagination=pagination)
    
@app.route("/book/<string:isbn>", methods=["GET", "POST"])
@login_required
def book(isbn):
    if request.method == "POST":
        rating = int(request.form.get("rating"))
        review = request.form.get("review")
        
        if not rating:  
            return render_template("error.html", message="Rating is required")
        if not review:
            return render_template("error.html", message="Review is required")
        
        print(Fore.GREEN + f"{rating}" + Style.RESET_ALL)
        
        query = text("SELECT * FROM reviews WHERE isbn = :isbn AND user_id = :user_id")
        if db.execute(query, {"isbn": isbn, "user_id": session["user_id"]}).rowcount == 0:
            query = text("INSERT INTO reviews (isbn, user_id, rating, review) VALUES (:isbn, :user_id, :rating, :review)")
            db.execute(query, {"isbn": isbn, "user_id": session["user_id"], "rating": rating, "review": review})
            db.commit()
            return redirect(f"/book/{isbn}")
        else:
            return render_template("error.html", message="You already reviewed this book")
    else:
        responsive = get_books_info(isbn)
        print(responsive)
        if responsive is None:
            print(Fore.RED + "Book not found" + Style.RESET_ALL)
            return render_template("error.html", message="Book not found")
        print(Fore.GREEN + "Book found" + Style.RESET_ALL)
        
        try:
            image = responsive["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]
        except Exception as e:
                print(e)
                image = "../static/img/books.jpg"
                
        title = responsive["items"][0]["volumeInfo"]["title"] #lista
        author = responsive["items"][0]["volumeInfo"]["authors"] #lista
        year = responsive["items"][0]["volumeInfo"]["publishedDate"]
        description = responsive["items"][0]["volumeInfo"]["description"]
        page_count = responsive["items"][0]["volumeInfo"]["pageCount"]
        category = responsive["items"][0]["volumeInfo"]["categories"] #lista
        average_rating = responsive["items"][0]["volumeInfo"]["averageRating"]
        ratings_count = responsive["items"][0]["volumeInfo"]["ratingsCount"]
        category_count = len(category)
        authors_count = len(author)

	    #pasarle tambien en una variable authors_count la cantidad de authores xd igual con las categorias xd category_count
        query = text("SELECT review, rating, users.username FROM reviews JOIN users ON users.id = reviews.user_id WHERE isbn = :isbn")
        reviews = db.execute(query, {"isbn": isbn}).fetchall()
        
        if len(reviews) == 0:
            review_count = 0
            average_score = 0
            print(Fore.RED + "No reviews found" + Style.RESET_ALL)
            return render_template("book.html", isbn=isbn, image=image, title=title, author=author, year=year, description=description, review_count=review_count, average_score=average_score, page_count=page_count, category_count=category_count, authors_count=authors_count, category=category, average_rating=average_rating, ratings_count=ratings_count)
        
        book_reviews = []
        for i in range(0, len(reviews)):
            book_reviews.append({
                "name": reviews[i].username,
                "review": reviews[i].review
                })
        print(Fore.GREEN + f"{book_reviews}" + Style.RESET_ALL)
        
        review_count = len(reviews)
        average_score = 0
        for i in range(0,len(reviews)):
            average_score += reviews[i].rating
        average_score = average_score / review_count
        print(Fore.GREEN + "Reviews found" + Style.RESET_ALL)
        return render_template("book.html", isbn=isbn, image=image, title=title, author=author, year=year, description=description, review_count=review_count, average_score=average_score, page_count=page_count, category_count=category_count, authors_count=authors_count, book_reviews=book_reviews, category=category, average_rating=average_rating, ratings_count=ratings_count)
   
   
@app.route("/api/<string:isbn>")
@login_required 
def api(isbn):
    if not isbn:
        return jsonify({"error": "Invalid isbn"}), 422
   
    query_2 = text("SELECT * FROM books WHERE isbn = :isbn")
    books = db.execute(query_2, {"isbn": isbn}).fetchone()
    
    if books is None:
        return jsonify({"error": "Book not found"}), 404
    
    query = text("SELECT COUNT(*) as review_count, AVG(rating) as average_score FROM reviews WHERE isbn = :isbn")
    reviews = db.execute(query, {"isbn": isbn}).fetchone()
    
    return jsonify({
        "title": books.title,
        "author": books.author,
        "year": books.year,
        "isbn": books.isbn,
        "review_count": reviews.review_count,
        "average_score": reviews.average_score
    })
    
@app.route("/reviews/<string:username>")
@login_required
def reviews(username):
    query = text("SELECT review, books.title, users.email, users.username FROM reviews JOIN books ON reviews.isbn = books.isbn JOIN users ON users.id = user_id WHERE user_id = :user_id")
    reviews = db.execute(query, {"user_id": session["user_id"]}).fetchall()
    return render_template("reviews.html", reviews=reviews)
    
if __name__ == '__main__':
    with app.app_context():
        app.run()
    
