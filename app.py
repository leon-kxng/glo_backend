from flask import Flask, jsonify, request, g, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ------------------ MySQL Database Configuration ------------------ #
# Replace 'your_mysql_user', 'your_mysql_password', and the database names below with your actual MySQL credentials.
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:cee@localhost/people_db"
app.config["SQLALCHEMY_BINDS"] = {
    "users": "mysql+pymysql://root:cee@localhost/users_db",
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ------------------ File Upload Configuration ------------------ #
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'images')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

db = SQLAlchemy(app)

# ------------------ Database Models ------------------ #
class Person(db.Model):
    __tablename__ = "people"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    stage = db.Column(db.String(50), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    notes = db.relationship("Note", backref="person", lazy=True)

class Note(db.Model):
    __tablename__ = "notes"
    
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("people.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)

class User(db.Model):
    __tablename__ = "users"
    __bind_key__ = "users"  # Bind this model to the 'users' database
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ------------------ API Routes (Unchanged) ------------------ #
@app.route("/api/people", methods=["POST"])
def add_person():
    data = request.get_json()
    name = data["name"]
    age = data["age"]
    stage = data["stage"]
    notes = data.get("notes", [])
    date_added = data["date_added"]  # Expecting date in "YYYY-MM-DD" format
    
    date_added = datetime.strptime(date_added, "%Y-%m-%d").date()
    new_person = Person(name=name, age=age, stage=stage, date_added=date_added)
    db.session.add(new_person)
    db.session.commit()  # Commit first to get the new person's ID
    
    for note_text in notes:
        new_note = Note(person_id=new_person.id, text=note_text)
        db.session.add(new_note)
    db.session.commit()
    
    return jsonify({"message": "Person and notes added successfully!", "id": new_person.id}), 201

@app.route("/api/people", methods=["GET"])
def get_people():
    people = Person.query.all()
    people_data = [
        {
            "id": p.id,
            "name": p.name,
            "age": p.age,
            "stage": p.stage,
            "date_added": p.date_added,
            "profile_picture": f"/uploads/{os.path.basename(p.profile_picture)}" if p.profile_picture else None,
            "notes": [note.text for note in p.notes]
        }
        for p in people
    ]
    return jsonify(people_data)

@app.route("/api/notes", methods=["POST"])
def add_note():
    data = request.get_json()
    person_id = data["person_id"]
    text = data["text"]
    person = Person.query.get(person_id)
    if not person:
        return jsonify({"message": "Person not found"}), 404
    new_note = Note(person_id=person_id, text=text)
    db.session.add(new_note)
    db.session.commit()
    return jsonify({"message": "Note added successfully!", "id": new_note.id}), 201

@app.route("/api/notes", methods=["GET"])
def get_notes():
    notes = Note.query.all()
    return jsonify([{"id": n.id, "person_id": n.person_id, "text": n.text} for n in notes])

@app.route("/api/people/<int:person_id>/notes", methods=["GET"])
def get_person_notes(person_id):
    notes = Note.query.filter_by(person_id=person_id).all()
    return jsonify([{"id": n.id, "person_id": n.person_id, "text": n.text} for n in notes])

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Invalid request data"}), 400
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"message": "Username already exists"}), 400
    new_user = User(username=data["username"])
    new_user.set_password(data["password"])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Invalid credentials"}), 401
    user = User.query.filter_by(username=data["username"]).first()
    if user and user.check_password(data["password"]):
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route("/api/people/<int:person_id>/upload_picture", methods=["POST"])
def upload_profile_picture(person_id):
    person = Person.query.get(person_id)
    if not person:
        return jsonify({"message": "Person not found"}), 404
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    if file and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        person.profile_picture = filepath
        db.session.commit()
        return jsonify({"message": "Profile picture uploaded successfully!"}), 200
    return jsonify({"message": "Invalid file format"}), 400

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), filename)

# ------------------ Database Initialization ------------------ #
with app.app_context():
    db.create_all()  # This creates tables in both the people_db and users_db

if __name__ == "__main__":
    app.run(debug=True)
