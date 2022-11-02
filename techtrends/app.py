import sqlite3
import logging
import sys
from wsgiref.handlers import format_date_time

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

# Define the Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = "your secret key"

app.config["total_connections"] = 0

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    """get_db_connection - this function used to connect the database"""
    try:
        connection = sqlite3.connect("database.db")
        connection.row_factory = sqlite3.Row
        connection.set_trace_callback(app.logger.info)
        app.config["total_connections"] = app.config["total_connections"] + 1
        return connection
    except sqlite3.Error as error:
        app.logger.error("Error occurred while making SQLite DB connection", error)

# Function to get a post using its ID
def get_post(post_id):
    """get_post - To get a post using its ID"""
    try:
        connection = get_db_connection()
        post = connection.execute(
            "SELECT * FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        connection.close()
        return post
    finally:
        if connection:
            connection.close()
            app.logger.debug("get_post function - SQLite DB connection is closed")

# Define the main route of the web application
@app.route("/")
def index():
    """index - Main route of the application"""
    try:
        connection = get_db_connection()
        posts = connection.execute("SELECT * FROM posts").fetchall()
        connection.close()
        app.logger.debug(
            f"""Articles "{','.join(str(post['title']) for post in posts)}" fetched from database!"""
        )
        return render_template("index.html", posts=posts)
    finally:
        if connection:
            connection.close()
            app.logger.debug("index function - SQLite DB connection is closed")

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route("/<int:post_id>")
def post(post_id):
    """Define how each individual article is rendered.
    If the post ID is not found a 404 page is shown"""
    post = get_post(post_id)
    if post is None:
        app.logger.info(f'Article with id "{post_id}" doesn\'t exist!')
        return render_template("404.html"), 404
    else:
        title = post["title"]
        app.logger.info(f'Article "{title}" retrieved!')
        return render_template("post.html", post=post)

# Define the About Us page
@app.route("/about")
def about():
    """/about - Define the About us page"""
    app.logger.info('The "About Us" page is retrieved')
    return render_template("about.html")

# Define the post creation functionality 
@app.route("/create", methods=("GET", "POST"))
def create():
    """/create - Define the post creation functionality"""
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        if not title:
            app.logger.info("Title is missing!")
            flash("Title is required!")
        else:
            try:
                connection = get_db_connection()
                connection.execute(
                    "INSERT INTO posts (title, content) VALUES (?, ?)", (title, content)
                )
                connection.commit()
                connection.close()
                app.logger.info(f'New Article "{title}" created!')
                return redirect(url_for("index"))
            finally:
                if connection:
                    connection.close()
                    app.logger.debug(
                        "create function - SQLite DB connection is closed"
                    )

    return render_template("create.html")

# Define the health check functionality 
@app.route("/healthz")
def status():
    """/healthz - Define the health check functionality"""
    app.logger.info("Health check call with response: %s", {"result": "OK - healthy"})
    response = app.response_class(
        response=json.dumps({"result": "OK - healthy"}, indent=4),
        status=200,
        mimetype="application/json",
    )
    return response

# Define the metrics check functionality 
@app.route("/metrics")
def metrics():
    """/metrics - Define the metrics check functionality"""
    try:
        connection = get_db_connection()
        totalPosts = connection.execute("SELECT count(id) FROM posts").fetchone()[0]
        connection.close()
        result = {
            "db_connection_count": app.config["total_connections"],
            "post_count": totalPosts,
        }
        app.logger.debug("metrics check call with response : ", result)
        response = app.response_class(
            response=json.dumps(result, indent=4),
            status=200,
            mimetype="application/json",
        )
        return response
    finally:
        if connection:
            connection.close()
            app.logger.debug("metrics function - SQLite DB connection is closes")


def setup_logger():
    """setup_logger - to set the logs"""
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.ERROR)
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [stderr_handler, stdout_handler]
    # format output
    format_output = "%(levelname)s:%(name)s:%(lineno)d:%(asctime)s, %(message)s"
    format_date_time = "%m/%d/%Y, %H:%M:%S"
    logging.basicConfig(
        format=format_output,
        datefmt=format_date_time,
        level=logging.DEBUG,
        handlers=handlers,
    )

# start the app on port 3111
if __name__ == "__main__":
    """Start the app on port 3111"""
    setup_logger()
    app.run(host="0.0.0.0", port="3111")