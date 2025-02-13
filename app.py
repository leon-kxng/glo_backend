from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://uakiu3zpkm6au6ym:cZYWfPXkc51506FLF0Ky@barz3foafqslz9vob4dq-mysql.services.clever-cloud.com:3306/barz3foafqslz9vob4dq"
)
app.config["SQLALCHEMY_BINDS"] = {
    "users": os.getenv(
        "USERS_DATABASE_URL",
        "mysql+pymysql://uakiu3zpkm6au6ym:cZYWfPXkc51506FLF0Ky@barz3foafqslz9vob4dq-mysql.services.clever-cloud.com:3306/users_db"
    )
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)

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
    __bind_key__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route("/api/people", methods=["POST"])
def add_person():
    data = request.get_json()
    name = data["name"]
    age = data["age"]
    stage = data["stage"]
    notes = data.get("notes", [])
    date_added = datetime.strptime(data["date_added"], "%Y-%m-%d").date()
    
    new_person = Person(name=name, age=age, stage=stage, date_added=date_added)
    db.session.add(new_person)
    db.session.commit()
    
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

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
